import config
import logging
from slackclient import SlackClient

log = logging.getLogger(__name__)

SLACK_CHANNEL = 'adgo_deployments'
BASE_LOG_URL = 'https://console.cloud.google.com/logs/viewer?project=sonic-wavelet-124006&filters=label:container.googleapis.com%2Fpod_name:'

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
        self.cluster_text = 'Production' if is_production else 'Development'
        self.image = config.IMAGE
        self.icon = ':release:' if is_production else ':canned_food:'
        self.username = '{} Deployer'.format(self.cluster_text)
        self.color = MIGRATION_LEVEL_MAP[config.MIGRATION_LEVEL]['color']
        self.migration_text = MIGRATION_LEVEL_MAP[config.MIGRATION_LEVEL]['text']
        self.thread_ts = 0

    def send_thread_reply(self, message: str, attachments: dict = {}, reply_broadcast: bool = False):
        log.debug('Sending thread reply to Slack #{}: thread={} message={}'.format(SLACK_CHANNEL, self.thread_ts, message))
        returned = self.slacker.api_call(
            'chat.postMessage',
            thread_ts=self.thread_ts,
            channel=SLACK_CHANNEL,
            username=self.username,
            icon_emoji=self.icon,
            text=message,
            attachments=attachments,
            reply_broadcast=reply_broadcast
        )
        log.debug('Returned from Slack: {}'.format(returned))

    def send_initial_message(self):
        """
        Sends message to Slack
        :return:
        """
        message = '{} Deployment Processing'.format(self.cluster_text)
        attachments = [{
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
                        },
                        {
                            'title': 'Logs',
                            'value': 'kubectl logs -f {}'.format(config.HOST_NAME),
                            'short': False
                        }
                    ]
                }]

        try:
            log.debug('Sending to Slack #{}: message={}'.format(SLACK_CHANNEL, message))
            returned = self.slacker.api_call(
                'chat.postMessage',
                channel=SLACK_CHANNEL,
                username=self.username,
                icon_emoji=self.icon,
                text=message,
                attachments=attachments
            )
            log.debug('Returned from Slack: {}'.format(returned))
            self.thread_ts = returned.get('ts')
        except Exception as error:
            log.error(error)

    def send_completion_message(
        self,
        error_message: str = None,
        error_handling_message: str = None,
        requires_scale_up: bool = False,
        requires_rollback_deployments: bool = False,
        requires_rollback_migration: bool = False
    ):
        has_error = error_message is not None

        if has_error:
            message = '@here\n:ultra_fire: Deployment Failed :ultra_fire:'

            attachments = [{
                        'fallback': 'Deployment Error={}'.format(error_message),
                        'color': 'danger',
                        'attachment_type': 'default',
                        'fields': [
                            {
                                'title': 'Deployment Error',
                                'value': error_message,
                                'short': False
                            },
                            {
                                'title': 'Recovery Status',
                                'value': error_handling_message,
                                'short': False
                            }
                        ]
                    }]

            if (requires_rollback_deployments):
                attachments[0]['fields'].append({
                    'title': 'Requires Deployment Rollback',
                    'value': '',
                    'short': False
                })
            if (requires_rollback_migration):
                attachments[0]['fields'].append({
                    'title': 'Requires Migration Rollback',
                    'value': '',
                    'short': False
                })
            if (requires_scale_up):
                attachments[0]['fields'].append({
                    'title': 'Requires Deployment Scale Up',
                    'value': '',
                    'short': False
                })
        else:
            message = '@here\n:party_yeet: {} Deployment Completed Successfully :party_yeet:'.format(self.cluster_text)
            attachments = [{
                        'color': 'good',
                        'attachment_type': 'default',
                        'fields': []
                    }]

        attachments[0]['fields'].append(
            {
                'title': 'Logs',
                'value': '{}{}'.format(BASE_LOG_URL, config.HOST_NAME),
                'short': False
            }
        )
        self.send_thread_reply(message=message, attachments=attachments, reply_broadcast=True)
