import config
import argparse
import logging
from lib.slack import SlackApi


logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s][%(levelname)s] %(message)s')


class Deployorama:
    """
    Perform kubernetes deployment and all that jazz.
    """

    def __init__(self, image: str, migration_level):
        self.image = image
        self.migration = migration_level
        self.slacker = SlackApi()
        self.requires_scale_down = migration_level == 2
        self.requires_migration = migration_level > 0
        self.requires_scale_up = False
        self.requires_rollback_deployments = False

    def deploy(self):

        try:
            self.slacker.send_initial_message()
            if (self.requires_scale_down is True):
                self.scale_down_deployments()
            if (self.requires_migration is True):
                self.run_migration()

            self.set_images()

            if (self.requires_scale_up is True):
                self.scale_up_deployments()

        except Exception as e:
            error_message = str(e)
            logging.error(error_message)
            error_handling_message = self.handle_failure()

        self.slacker.send_completion_message(
            error_message=error_message,
            error_handling_message=error_handling_message,
            requires_scale_up=self.requires_scale_up,
            requires_rollback_deployments=self.requires_rollback_deployments,
            requires_rollback_migration=self.requires_rollback_migration
        )

    def handle_failure(self):
        error_handler_message = "Successfully Reverted Deployment Modifications"
        try:
            if (self.requires_rollback_migration is True):
                self.rollback_migration()
            if (self.requires_rollback_deployments is True):
                self.rollback_deployments()
            if (self.requires_scale_up is True):
                self.scale_up_deployments()
        except Exception as e:
            error_handler_message = 'Error Handling Failed: Error={}'.format(str(e))
            logging.error(error_handler_message)

        return error_handler_message

    def rollback_migration(self):
        try:
            self.slacker.send_thread_reply('Rolling Back Migration')
            print('do stuff')
        except Exception as e:
            error_message = 'Rolling Back Migration Failed: Error={}'.format(str(e))
            logging.error(error_message)
            raise e

        self.requires_rollback_migration = False

    def rollback_deployments(self):
        try:
            self.slacker.send_thread_reply('Rolling Back Deployments')
            print('do stuff')
        except Exception as e:
            error_message = 'Rolling Back Deployments Failed: Error={}'.format(str(e))
            logging.error(error_message)
            raise e

        self.requires_rollback_deployments = False

    def scale_down_deployments(self):
        try:
            self.slacker.send_thread_reply('scaling down')
            print('do stuff')
        except Exception as e:
            error_message = 'Scale Down Failed: Error={}'.format(str(e))
            logging.error(error_message)
            raise e

        self.requires_scale_up = True

    def scale_up_deployments(self):
        try:
            self.slacker.send_thread_reply('scaling up')
            print('do stuff')
        except Exception as e:
            error_message = 'Scale Up Failed: Error={}'.format(str(e))
            logging.error(error_message)
            raise e

        self.requires_scale_up = False

    def backup_database(self):
        try:
            self.slacker.send_thread_reply('backing up database')
            print('do stuff')
        except Exception as e:
            error_message = 'Backup Creation Failed: Error={}'.format(str(e))
            logging.error(error_message)
            raise e

    def run_migration(self):
        self.backup_database()

        try:
            self.slacker.send_thread_reply('migrating')
            print('do stuff')
        except Exception as e:
            error_message = 'Migration Failed: Error={}'.format(str(e))
            logging.error(error_message)
            raise e

        self.requires_rollback_migration = True

    def set_images(self):
        try:
            self.slacker.send_thread_reply('set images')
            print('do stuff')
        except Exception as e:
            error_message = 'Set Images Failed: Error={}'.format(str(e))
            logging.error(error_message)
            raise e

        self.requires_rollback_deployments = True


if __name__ == '__main__':
    parser = argparse.ArgumentParser("deploy")
    parser.add_argument("-i", "--image", help="New monolith image to be rolled out.", type=str, required=True)
    parser.add_argument("-m", "--migration", help="Migration level: 0=None, 1=Hot, 2=Cold", type=int, required=True)
    args = parser.parse_args()
    config.IMAGE = args.image
    config.MIGRATION_LEVEL = args.migration
    deployer = Deployorama(args.image, args.migration)
    deployer.deploy()
