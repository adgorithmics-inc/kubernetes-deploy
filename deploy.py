import config
import argparse
import logging
import subprocess

from datetime import datetime
from lib.slackApi import SlackApi
from lib.kubeApi import KubeApi

logging.basicConfig(
    level=logging.DEBUG, format="[%(asctime)s][%(levelname)s] %(message)s"
)

# listed in scale down order
SCALABLE_TIERS = ["frontend", "worker", "scheduler"]
NON_SCALABLE_TIERS = ["apiserver"]


class Deployorama:
    """
    Perform kubernetes deployment and all that jazz.
    """

    def __init__(self):
        self.image = config.IMAGE
        self.migration = config.MIGRATION_LEVEL
        self.slacker = SlackApi()
        self.kuber = KubeApi(namespace=config.NAMESPACE)
        self.deployments = {
            tier: self.kuber.get_deployments(
                label_selector="deploymentGroup={}, tier={}".format(
                    config.DEPLOYMENT_GROUP, tier
                )
            )
            for tier in SCALABLE_TIERS + NON_SCALABLE_TIERS
        }
        self.has_down_time = self.migration == 2
        self.has_migration = self.migration > 0
        self.migration_completed = False

    def all_deployments(self):
        return [deploy for sublist in self.deployments.values() for deploy in sublist]

    def deploy(self):
        """
        The master deployment method to process deployment from start to finish.
        """

        if config.DISABLED:
            self.slacker.send_message(text="Automated deployment is currently disabled")
            return

        error_message = None
        error_handling_message = None

        try:
            self.slacker.send_initial_message()

            if self.has_down_time:
                self.scale_down_deployments()

            if self.has_migration:
                self.backup_database()
                self.run_migration()

            self.set_images()

            if self.has_down_time:
                self.scale_up_deployments()

        except Exception as e:
            error_message = str(e)
            logging.error(error_message)
            error_handling_message = self.handle_deploy_failure()

        self.slacker.send_completion_message(
            error_message=error_message,
            error_handling_message=error_handling_message,
            deployments=self.all_deployments(),
            requires_migration_rollback=self.has_down_time and self.migration_completed,
        )

    def handle_deploy_failure(self):
        """
        Handle deployment failure by reverting all modificaitnos.
        """
        step = "Recovering From Deployment Error"
        self.slacker.send_thread_reply(step)

        if self.has_down_time is True and self.migration_completed:
            return "Skipped Automated Recovery: Requires Manual Intervention"

        try:
            self.rollback_images()
            self.scale_up_deployments()
            error_handler_message = "Successfully Rolled Back Deployment"

        except Exception as e:
            error_handler_message = str(e)
            logging.error(error_handler_message)

        return error_handler_message

    def raise_step_error(self, error: Exception, step: str):
        """
        Handle notification for deployment step errors and raise exception with new message.
        """
        error_message = "{}\nFailed: Error={}".format(step, str(error))
        logging.error(error_message)
        self.slacker.send_thread_reply(error_message)
        raise Exception(error_message)

    def scale_down_deployments(self):
        """
        Scale down deployments.
        """
        try:
            for tier in SCALABLE_TIERS:
                for deployment in self.deployments[tier]:
                    step = "Scaling Down Deployment:\ndeployment={}".format(
                        deployment["name"]
                    )
                    self.slacker.send_thread_reply(step)
                    deployment["scaled_down"] = True
                    self.kuber.set_deployment_replicas(deployment["instance"], 0)
                step = "Verifying {} Deployments Scaled Down Successfully".format(tier)
                self.slacker.send_thread_reply(step)
                for deployment in self.deployments[tier]:
                    self.kuber.verify_deployment_update(deployment["name"])
        except Exception as e:
            self.raise_step_error(step=step, error=e)

    def scale_up_deployments(self):
        """
        Scale up all deployments (in reverse order) to original replica counts.
        """
        try:
            for tier in SCALABLE_TIERS[::-1]:
                for deployment in self.deployments[tier]:
                    if deployment.get("scaled_down", False) is True:
                        step = "Scaling Up Deployment:\ndeployment={}\nreplicas={}".format(
                            deployment["name"], deployment["replicas"]
                        )
                        self.slacker.send_thread_reply(step)
                        self.kuber.set_deployment_replicas(
                            deployment["instance"], deployment["replicas"]
                        )
                        deployment["scaled_down"] = False
                step = "Verifying {} Deployments Scaled Up Successfully".format(tier)
                self.slacker.send_thread_reply(step)
                for deployment in self.deployments[tier]:
                    self.kuber.verify_deployment_update(deployment["name"])
        except Exception as e:
            self.raise_step_error(step=step, error=e)

    def backup_database(self):
        """
        Store a cloud sql backup on google storage
        """
        backup_file = "{}-{}.sql".format(
            config.DATABASE_NAME, datetime.today().strftime("%Y-%m-%d--%H%M")
        )
        backup_uri = "{}/{}".format(config.DATABASE_BACKUP_BUCKET, backup_file)
        step = "Backing Up Database:\nbackup={}".format(backup_uri)
        try:
            self.slacker.send_thread_reply(step)
            backup_command = [
                "gcloud",
                "sql",
                "export",
                "sql",
                config.DATABASE_INSTANCE_NAME,
                backup_uri,
                "--database={}".format(config.DATABASE_NAME),
                "--verbosity=debug",
            ]
            subprocess.run(backup_command, check=True)
        except Exception as e:
            self.raise_step_error(step=step, error=e)

    def run_migration(self):
        """
        Perform database migration via k8 app-migrator job.
        """
        step = "Migrating Database"
        try:
            self.slacker.send_thread_reply(step)
            self.kuber.run_migration(self.image)
            self.migration_completed = True
        except Exception as e:
            self.raise_step_error(step=step, error=e)

    def set_images(self):
        """
        Update images for all deployments.
        """
        try:
            for deployment in self.all_deployments():
                step = "Setting Deployment Image:\ndeployment={}\nold_image={}\nnew_image={}".format(
                    deployment["name"], deployment["image"], self.image
                )
                if deployment["image"] == self.image:
                    self.slacker.send_thread_reply(
                        "Deployment Doesn't Require Image Update: deployment={} image={}".format(
                            deployment["name"], self.image
                        )
                    )
                    continue
                self.slacker.send_thread_reply(step)
                self.kuber.set_deployment_image(deployment["instance"], self.image)
                deployment["updated_image"] = True
            step = "Verifying Deployment Updates Completed Successfully"
            self.slacker.send_thread_reply(step)
            for deployment in self.all_deployments():
                self.kuber.verify_deployment_update(deployment["name"])
        except Exception as e:
            self.raise_step_error(step=step, error=e)

    def rollback_images(self):
        """
        Rollback all deployment images to their original state prior to deployment.
        """
        for deployment in self.all_deployments():
            if deployment.get("updated_image", False) is False:
                continue
            step = "Rolling Back Deployment Image:\ndeployment={}\nattempted_image={}\nrollback_image={}".format(
                deployment["name"], self.image, deployment["image"]
            )
            try:
                self.slacker.send_thread_reply(step)
                self.kuber.set_deployment_image(
                    deployment["instance"], deployment["image"], verify_update=True
                )
                deployment["updated_image"] = False
            except Exception as e:
                self.raise_step_error(step=step, error=e)


if __name__ == "__main__":
    parser = argparse.ArgumentParser("deploy")
    parser.add_argument(
        "-i",
        "--image",
        help="New monolith image to be rolled out.",
        type=str,
        required=True,
    )
    parser.add_argument(
        "-m",
        "--migration",
        help="Migration level: 0=None, 1=Hot, 2=Cold",
        type=int,
        required=True,
    )
    args = parser.parse_args()
    config.IMAGE = args.image.strip()
    config.MIGRATION_LEVEL = args.migration
    deployer = Deployorama()
    deployer.deploy()
