import config
import argparse
import logging
from lib.slack import SlackApi


logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s][%(levelname)s] %(message)s')


class Deployorama:
    """
    Perform kubernetes deployment and all that jazz.
    """

    def __init__(self, image, migration_level):
        self.image = image
        self.migration = migration_level
        self.slacker = SlackApi()

    def deploy(self):
        self.slacker.send_intial_thread_message()
        # start doing work


if __name__ == '__main__':
    parser = argparse.ArgumentParser("deploy")
    parser.add_argument("-i", "--image", help="New monolith image to be rolled out.", type=str, required=True)
    parser.add_argument("-m", "--migration", help="Migration level: 0=None, 1=Hot, 2=Cold", type=int, required=True)
    args = parser.parse_args()
    config.IMAGE = args.image
    config.MIGRATION_LEVEL = args.migration_level
    deployer = Deployorama(args.image, args.migration_level)
    deployer.deploy()
