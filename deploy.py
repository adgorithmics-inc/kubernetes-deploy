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

    def deploy(self):
        self.slacker.send_intial_thread_message()
        self.slacker.send_status_update('testing status update')
        self.slacker.send_status_update('testing status update again')

        try:
            if (self.requires_scale_down is True):
                self.scale_down_deployments()
            if (self.requires_migration is True):
                self.run_migration()

            self.set_images()

            if (self.requires_scale_down is True):
                self.scale_up_deployments()
        except Exception as e:
            error_message = 'Rollout encountered an error: Error={}'.format(e.message)
            logging.error(error_message)
            self.slacker('@here {}'.format(error_message))

    def scale_down_deployments(self):
        self.slacker.send_status_update('scaling down')

    def scale_up_deploytments(self):
        self.slacker.send_status_update('scaling up')

    def run_migration(self):
        self.slacker.send_status_update('migrating')

    def set_images(self):
        self.slacker.send_status_update('set images')


if __name__ == '__main__':
    parser = argparse.ArgumentParser("deploy")
    parser.add_argument("-i", "--image", help="New monolith image to be rolled out.", type=str, required=True)
    parser.add_argument("-m", "--migration", help="Migration level: 0=None, 1=Hot, 2=Cold", type=int, required=True)
    args = parser.parse_args()
    config.IMAGE = args.image
    config.MIGRATION_LEVEL = args.migration
    deployer = Deployorama(args.image, args.migration)
    deployer.deploy()
