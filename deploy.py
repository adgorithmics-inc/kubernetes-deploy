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

    def __init__(self, image: str, migration_level):
        self.image = image
        self.migration = migration_level
        self.slacker = SlackApi()
        self.kuber = KubeApi(namespace=config.NAMESPACE)
        self.deployments = {
            'frontend': self.kuber.get_deployments(label_selector='deploymentGroup={}, tier=frontend'.format(config.DEPLOYMENT_GROUP)),
            'backend': self.kuber.get_deployments(label_selector='deploymentGroup={}, tier!=frontend'.format(config.DEPLOYMENT_GROUP))
        }
        self.requires_scale_down = migration_level == 2
        self.requires_migration = migration_level > 0
        self.requires_scale_up_frontend = False
        self.requires_scale_up_backend = False
        self.requires_rollback_images = False
        self.requires_rollback_migration = False

    def deploy(self):
        """
        The master deployment method to process deployment from start to finish.
        """
        error_message = None
        error_handling_message = None

        try:
            self.slacker.send_initial_message()

            if (self.requires_scale_down is True):
                self.scale_down_frontend_deployments()
                self.scale_down_backend_deployments()

            if (self.requires_migration is True):
                self.backup_database()
                self.run_migration()

            self.set_images()

            if (self.requires_scale_up is True):
                self.scale_up_backend_deployments()
                self.scale_up_frontend_deployments()

        except Exception as e:
            error_message = str(e)
            logging.error(error_message)
            error_handling_message = self.handle_deploy_failure()

        self.slacker.send_completion_message(
            error_message=error_message,
            error_handling_message=error_handling_message,
            requires_scale_up_frontend=self.requires_scale_up_frontend,
            requires_scale_up_backend=self.requires_scale_up_backend,
            requires_rollback_images=self.requires_rollback_images,
            requires_rollback_migration=self.requires_rollback_migration
        )

    def handle_deploy_failure(self):
        """
        Handle deployment failure by reverting all modificaitnos.
        """
        error_handler_message = "Successfully Rolled Back Deployment"
        step = 'Recovering From Deployment Error'
        self.slacker.send_thread_reply(step)
        try:
            if (self.requires_rollback_migration is True):
                self.rollback_migration()
            if (self.requires_rollback_images is True):
                self.rollback_images()
            if (self.requires_scale_up_backend is True):
                self.scale_up_backend_deployments()
            if (self.requires_scale_up_frontend is True):
                self.scale_up_frontend_deployments()
        except Exception as e:
            error_handler_message = str(e)
            logging.error(error_handler_message)

        return error_handler_message

    def handle_step_error(self, error: Exception, step: str):
        """
        Handle an error from a deployment step by logging and notifying slack.
        """
        error_message = '{} Failed: Error={}'.format(step, str(error))
        logging.error(error_message)
        self.slacker.send_thread_reply(error_message)
        raise Exception(error_message)

    def scale_down_frontend_deployments(self):
        """
        Scale down only frontend deployments.
        """
        step = 'Scaling Down Frontend Deployments'
        try:
            self.slacker.send_thread_reply(step)
            self.kuber.scale_down_deployments(self.deployments['frontend'].keys())
        except Exception as e:
            self.handle_step_error(step=step, error=e)

        self.requires_scale_up_frontend = True

    def scale_down_backend_deployments(self):
        """
        Scale down only backend deployments.
        """
        step = 'Scaling Down Backend Deployments'
        try:
            self.slacker.send_thread_reply(step)
            self.kuber.scale_down_deployments(self.deployments['backend'].keys())
        except Exception as e:
            self.handle_step_error(step=step, error=e)

        self.requires_scale_up_backend = True

    def scale_up_frontend_deployments(self):
        """
        Scale up only frontend deployments.
        """
        step = 'Scaling Up Frontend Deployments'
        try:
            self.slacker.send_thread_reply(step)
            self.kuber.scale_up_deployments(self.deployments['frontend'].keys())
        except Exception as e:
            self.handle_step_error(step=step, error=e)

        self.requires_scale_up_frontend = False

    def scale_up_backend_deployments(self):
        """
        Scale up only backend deployments.
        """
        step = 'Scaling Up Backend Deployments'
        try:
            self.slacker.send_thread_reply(step)
            self.kuber.scale_up_deployments(self.deployments['backend'].keys())
        except Exception as e:
            self.handle_step_error(step=step, error=e)

        self.requires_scale_up_backend = False

    def backup_database(self):
        """
        Store a local backup of the database.
        """
        step = 'Backing Up Database'
        try:
            self.slacker.send_thread_reply(step)
            print('backup DB')
        except Exception as e:
            self.handle_step_error(step=step, error=e)

    def run_migration(self):
        """
        Perform database migration via k8 app-migrator job.
        """
        step = 'Migrating Database'
        try:
            self.slacker.send_thread_reply(step)
            print('run migration')
        except Exception as e:
            self.handle_step_error(step=step, error=e)

        self.requires_rollback_migration = True

    def rollback_migration(self):
        """
        Restore database via locally saved backup.
        """
        step = 'Rolling Back Migration'
        try:
            self.slacker.send_thread_reply(step)
            print('rollback DB')
        except Exception as e:
            self.handle_step_error(step=step, error=e)

        self.requires_rollback_migration = False

    def set_images(self):
        """
        Update images for all deployments.
        """
        step = 'Setting Deployment Images'
        try:
            self.slacker.send_thread_reply(step)
            all_deployments = self.deployments['backend'].keys() + self.deployments['frontend'].keys()
            deployments_update = [(name, self.image) for name in all_deployments]
            self.kuber.set_deployment_images(deployments_update)
        except Exception as e:
            self.handle_step_error(step=step, error=e)
            error_message = 'Set Images Failed: Error={}'.format(str(e))
            logging.error(error_message)
            raise e

        self.requires_rollback_images = True

    def rollback_images(self):
        """
        Rollback all deployment images to their original state prior to deployment.
        """
        step = 'Rolling Back Deployment Images'
        try:
            self.slacker.send_thread_reply(step)
            all_deployments = self.deployments['backend'].items() + self.deployments['frontend'].items()
            deployments_update = [(name, value['image']) for (name, value) in all_deployments]
            self.kuber.set_deployment_images(deployments_update)
        except Exception as e:
            self.handle_step_error(step=step, error=e)

        self.requires_rollback_images = False


if __name__ == '__main__':
    parser = argparse.ArgumentParser("deploy")
    parser.add_argument("-i", "--image", help="New monolith image to be rolled out.", type=str, required=True)
    parser.add_argument("-m", "--migration", help="Migration level: 0=None, 1=Hot, 2=Cold", type=int, required=True)
    args = parser.parse_args()
    config.IMAGE = args.image
    config.MIGRATION_LEVEL = args.migration
    deployer = Deployorama(args.image, args.migration)
    deployer.deploy()
