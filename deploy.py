import argparse
import logging
from lib import slack


logging.basicConfig(level=logging.INFO, format='[%(asctime)s][%(levelname)s] %(message)s')


class Deployorama:
    """
    Perform kubernetes deployment and all that jazz.
    """

    def __init__(self, image, migration_level):
        self.image = image
        self.migration = migration_level

    def deploy(self):
        slack.send_message('Testing :troll_parrot:\nImage: {}\nMigration: {}'.format(self.image, self.migration))


if __name__ == '__main__':
    parser = argparse.ArgumentParser("deploy")
    parser.add_argument("-i", "--image", help="New monolith image to be rolled out.", type=str, required=True)
    parser.add_argument("-m", "--migration", help="Migration level: 0=None, 1=Hot, 2=Cold", type=int, required=True)
    args = parser.parse_args()
    deployer = Deployorama(args.image, args.migration)
    deployer.deploy()
