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

    def __init__(self, image: str, migration_level: int):
        self.image = image
        self.migration = migration_level
        self.slacker = SlackApi()
        self.kuber = KubeApi(namespace=config.NAMESPACE)
        self.deployments = {
            tier: self.kuber.get_deployments(
                label_selector=f"deploymentGroup={config.DEPLOYMENT_GROUP}, tier={tier}"
            )
            for tier in SCALABLE_TIERS + NON_SCALABLE_TIERS
        }
        self.has_down_time = migration_level == 2
        self.has_migration = migration_level > 0
        self.migration_completed = False

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
            deployments=self.deployments.values(),
            requires_migration_rollback=self.has_down_time and self.migration_completed,
        )

    def handle_deploy_failure(self):
        """
        Handle deployment failure by reverting all modificaitnos.
        """
        step = "Recovering From Deployment Error"
        self.slacker.send_thread_reply(step)

        if self.has_down_time is True and self.migration_completed:
            return "Skipped Automated Recover: Requires Manual Intervention"

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
        error_message = f"{step} Failed: Error={str(error)}"
        logging.error(error_message)
        self.slacker.send_thread_reply(error_message)
        raise Exception(error_message)

    def scale_down_deployments(self):
        """
        Scale down deployments.
        """
        for tier in SCALABLE_TIERS:
            step = (
                f"Scaling Down Deployment:\ndeployment={self.deployments[tier]['name']}"
            )
            try:
                self.slacker.send_thread_reply(step)
                self.deployments[tier]["scaled_down"] = True
                self.kuber.set_deployment_replicas(self.deployments[tier]["name"], 0)
            except Exception as e:
                self.raise_step_error(step=step, error=e)

    def scale_up_deployments(self):
        """
        Scale up all deployments (in reverse order) to original replica counts.
        """
        for tier in SCALABLE_TIERS[::-1]:
            if self.deployments[tier].get("scaled_down", False) is True:
                step = f"Scaling Up Deployment:\ndeployment={self.deployments[tier]['name']}\nreplicas={self.deployments[tier]['replicas']}"
                try:
                    self.slacker.send_thread_reply(step)
                    self.kuber.set_deployment_replicas(
                        self.deployments[tier]["name"],
                        self.deployments[tier]["replicas"],
                    )
                    self.deployments[tier]["scaled_down"] = False
                except Exception as e:
                    self.raise_step_error(step=step, error=e)

    def backup_database(self):
        """
        Store a cloud sql backup on google storage
        """
        backup_file = (
            f"{config.DATABASE_NAME}-{datetime.today().strftime('%Y-%m-%d--%H%M')}.sql"
        )
        backup_uri = f"{config.DATABASE_BACKUP_BUCKET}/{backup_file}"
        step = f"Backing Up Database:\nbackup={backup_uri}"
        try:
            self.slacker.send_thread_reply(step)
            backup_command = [
                "gcloud",
                "sql",
                "export",
                "sql",
                config.DATABASE_INSTANCE_NAME,
                backup_uri,
                f"--database={config.DATABASE_NAME}",
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
            for deployment in [
                deploy for sublist in self.deployments.values() for deploy in sublist
            ]:
                step = f"Setting Deployment Image:\ndeployment={deployment['name']}\nold_image={deployment['image']}\nnew_image={self.image}"
                if deployment["image"] == self.image:
                    self.slacker.send_thread_reply(
                        f"Deployment Doesn't Require Image Update: deployment={deployment['name']} image={self.image}"
                    )
                    continue
                self.slacker.send_thread_reply(step)
                deployment["updated_image"] = True
                self.kuber.set_deployment_image(deployment["name"], self.image)
            for deployment in self.deployments:
                self.kuber.verify_deployment_update(deployment)
        except Exception as e:
            self.raise_step_error(step=step, error=e)

    def rollback_images(self):
        """
        Rollback all deployment images to their original state prior to deployment.
        """
        for deployment in [
            deploy for sublist in self.deployments.values() for deploy in sublist
        ]:
            if deployment.get("updated_image", False) is False:
                continue
            step = f"Rolling Back Deployment Image:\ndeployment={deployment['name']}\nattempted_image={self.image}\nrollback_image={deployment['image']}"
            try:
                self.slacker.send_thread_reply(step)
                self.kuber.set_deployment_image(
                    deployment["name"], deployment["image"], verify_update=True
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
    config.IMAGE = args.image
    config.MIGRATION_LEVEL = args.migration
    deployer = Deployorama(args.image, args.migration)
    deployer.deploy()
