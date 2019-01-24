import config
import argparse
import logging

from lib.slackApi import SlackApi
from lib.kubeApi import KubeApi


logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s][%(levelname)s] %(message)s')


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
            'frontend': self.kuber.get_deployments(label_selector='deploymentGroup={}, tier=frontend'.format(config.DEPLOYMENT_GROUP)),
            'backend': self.kuber.get_deployments(label_selector='deploymentGroup={}, tier=backend'.format(config.DEPLOYMENT_GROUP)),
            'service': self.kuber.get_deployments(label_selector='deploymentGroup={}, tier=service'.format(config.DEPLOYMENT_GROUP))
        }
        self.has_down_time = migration_level == 2
        self.has_migration = migration_level > 0
        self.migration_completed = False

    def deploy(self):
        """
        The master deployment method to process deployment from start to finish.
        """
        error_message = None
        error_handling_message = None

        try:
            self.slacker.send_initial_message()

            if (self.has_down_time):
                self.scale_down_deployments()

            if (self.has_migration):
                self.backup_database()
                self.run_migration()

            self.set_images()

            if (self.has_down_time):
                self.scale_up_deployments()

        except Exception as e:
            error_message = str(e)
            logging.error(error_message)
            error_handling_message = self.handle_deploy_failure()

        self.slacker.send_completion_message(
            error_message=error_message,
            error_handling_message=error_handling_message,
            deployments=self.deployments['service'] + self.deployments['backend'] + self.deployments['frontend'],
            requires_migration_rollback=self.has_down_time and self.migration_completed
        )

    def handle_deploy_failure(self):
        """
        Handle deployment failure by reverting all modificaitnos.
        """
        step = 'Recovering From Deployment Error'
        self.slacker.send_thread_reply(step)

        if (self.has_down_time is True and self.migration_completed):
            return 'Skipped Automated Recover: Requires Manual Intervention'

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
        error_message = '{} Failed: Error={}'.format(step, str(error))
        logging.error(error_message)
        self.slacker.send_thread_reply(error_message)
        raise Exception(error_message)

    def scale_down_deployments(self):
        """
        Scale down deployments from frontend to backend.
        """
        for deployment in self.deployments['frontend'] + self.deployments['backend']:
            step = 'Scaling Down Deployment: {}'.format(deployment['name'])
            try:
                self.slacker.send_thread_reply(step)
                deployment['scaled_down'] = True
                self.kuber.set_deployment_replicas(deployment['name'], 0)
            except Exception as e:
                self.raise_step_error(step=step, error=e)

    def scale_up_deployments(self):
        """
        Scale up all deployments to original replica counts from backend to frontend.
        """
        for deployment in self.deployments['backend'] + self.deployments['frontend']:
            if (deployment.get('scaled_down', False) is True):
                step = 'Scaling Up Deployment: deployment={} replicas={}'.format(deployment['name'], deployment['replicas'])
                try:
                    self.slacker.send_thread_reply(step)
                    self.kuber.set_deployment_replicas(deployment['name'], deployment['replicas'])
                    deployment['scaled_down'] = False
                except Exception as e:
                    self.raise_step_error(step=step, error=e)

    def backup_database(self):
        """
        Store a local backup of the database.
        """
        step = 'Backing Up Database'
        try:
            self.slacker.send_thread_reply(step)
            print('backup DB')
        except Exception as e:
            self.raise_step_error(step=step, error=e)

    def run_migration(self):
        """
        Perform database migration via k8 app-migrator job.
        """
        step = 'Migrating Database'
        try:
            self.slacker.send_thread_reply(step)
            print('run migration')
            self.migration_completed = True
        except Exception as e:
            self.raise_step_error(step=step, error=e)

    def set_images(self):
        """
        Update images for all deployments.
        """
        for deployment in self.deployments['service'] + self.deployments['backend'] + self.deployments['frontend']:
            step = 'Setting Deployment Image: deployment={} old_image={} new_image={}'.format(deployment['name'], deployment['image'], self.image)
            try:
                self.slacker.send_thread_reply(step)
                deployment['updated_image'] = True
                self.kuber.set_deployment_image(deployment['name'], self.image)
            except Exception as e:
                self.raise_step_error(step=step, error=e)

    def rollback_images(self):
        """
        Rollback all deployment images to their original state prior to deployment.
        """
        for deployment in self.deployments['service'] + self.deployments['backend'] + self.deployments['frontend']:
            if (deployment.get('updated_image', False) is False):
                continue
            step = 'Rolling Back Deployment Image: deployment={} attempted_image={} rollback_image={}'.format(
                deployment['name'],
                self.image,
                deployment['image']
            )
            try:
                self.slacker.send_thread_reply(step)
                self.kuber.set_deployment_image(deployment['name'], deployment['image'])
                deployment['updated_image'] = False
            except Exception as e:
                self.raise_step_error(step=step, error=e)


if __name__ == '__main__':
    parser = argparse.ArgumentParser("deploy")
    parser.add_argument("-i", "--image", help="New monolith image to be rolled out.", type=str, required=True)
    parser.add_argument("-m", "--migration", help="Migration level: 0=None, 1=Hot, 2=Cold", type=int, required=True)
    args = parser.parse_args()
    config.IMAGE = args.image
    config.MIGRATION_LEVEL = args.migration
    deployer = Deployorama(args.image, args.migration)
    deployer.deploy()
