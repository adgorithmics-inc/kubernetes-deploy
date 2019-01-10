import os
import logging
from slackclient import SlackClient

log = logging.getLogger(__name__)
slacker = SlackClient(token=os.getenv('SLACK_TOKEN'))
SLACK_CHANNEL = 'adgo_deployments'
PROD_RELEASE = os.getenv('GCLOUD_CLUSTER_NAME') == 'prod-cluster'
ICON_EMOJI = ':release:' if PROD_RELEASE else ':canned_food:'
USERNAME_PREFIX = 'Production' if PROD_RELEASE else 'Development'


def send_message(message: str) -> None:
    """
    Sends a message to Slack
    :param message:
    :return:
    """

    try:
        logging.debug('Sending to Slack #{}: {}'.format(SLACK_CHANNEL, message))
        returned = slacker.api_call(
            'chat.postMessage',
            channel=SLACK_CHANNEL,
            text=message,
            username='{} Deployer'.format(USERNAME_PREFIX),
            icon_emoji=ICON_EMOJI
        )
        logging.debug('Returned from Slack: {}'.format(returned))

    except Exception as error:
        logging.error(error)
