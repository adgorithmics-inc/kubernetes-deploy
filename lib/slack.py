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
        self.thread_ts = 0

    def send_status_update(self, message: str):
        log.debug('Sending to Slack #{}: {}'.format(SLACK_CHANNEL, message))
        returned = self.slacker.api_call(
            'chat.postMessage',
            thread_ts=self.thread_ts,
            channel=SLACK_CHANNEL,
            username='Status Update',
            icon_emoji=self.icon,
            text=message
        )
        log.debug('Returned from Slack: {}'.format(returned))

    def send_completion_reaction(self, success: bool):
        log.debug('Sending to Slack #{}: {}'.format(SLACK_CHANNEL))
        returned = self.slacker.api_call(
            'reactions.add',
            timestamp=self.thread_ts,
            channel=SLACK_CHANNEL,
            name="party_yeet" if success else ":ultra_fire:"
        )
        log.debug('Returned from Slack: {}'.format(returned))

    def send_intial_thread_message(self) -> None:
        """
        Sends initial message to Slack
        :return:
        """
        try:
            log.debug('Sending to Slack #{}'.format(SLACK_CHANNEL))
            returned = self.slacker.api_call(
                'chat.postMessage',
                channel=SLACK_CHANNEL,
                username=self.username,
                icon_emoji=self.icon,
                attachments=[{
                    'fallback': 'Image={} Migrations={}'.format(self.image, self.migration_text),
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
                }]
            )
            log.debug('Returned from Slack: {}'.format(returned))
            self.thread_ts = returned.get('ts')
        except Exception as error:
            log.error(error)
