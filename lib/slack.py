import time
import config
import logging
from slackclient import SlackClient

log = logging.getLogger(__name__)

SLACK_CHANNEL = 'adgo_deployments'

MIGRATION_LEVEL_MAP = [
    {
        'text': 'None',
        'color': 'good'
    },
    {
        'text': ':hotsprings: Hot',
        'color': 'warning'
    },
    {
        'text': ':snowflake: Cold',
        'color': 'danger'
    },
]


class SlackApi:
    """
    Wrapper for slack to send deployment status updates
    """

    def __init__(self):
        is_production = config.CLUSTER_NAME == 'prod-cluster'
        self.slacker = SlackClient(token=config.SLACK_TOKEN)
        self.image = config.IMAGE
        self.icon = ':release:' if is_production else ':canned_food:'
        self.username = ('Production' if is_production else 'Development') + ' Deployer'
        self.color = MIGRATION_LEVEL_MAP[config.MIGRATION_LEVEL]['color']
        self.migration_text = MIGRATION_LEVEL_MAP[config.MIGRATION_LEVEL]['text']

    def send_intial_thread_message(self) -> None:
        """
        Sends a message to Slack
        :param message:
        :return:
        """
        self.thread_ts = time.time()
        initiation_message = 'Initiating {}'.format(self.username)
        try:
            log.debug('Sending to Slack #{}: {}'.format(SLACK_CHANNEL, initiation_message))
            returned = self.slacker.api_call(
                'chat.postMessage',
                ts=self.thread_ts,
                channel=SLACK_CHANNEL,
                username=self.username,
                icon_emoji=self.icon,
                text=initiation_message,
                attachments={
                    'fallback': initiation_message,
                    'color': self.color,
                    'attachment_type': 'default',
                    'fields': [
                        {
                            'title': 'Image',
                            'value': self.image,
                            'short': False
                        },
                        {
                            'title': 'Migrations',
                            'value': self.migration_text,
                            'short': False
                        }
                    ]
                }
            )
            log.debug('Returned from Slack: {}'.format(returned))

        except Exception as error:
            log.error(error)
