import config
import logging
from slackclient import SlackClient

log = logging.getLogger(__name__)

SLACK_CHANNEL = 'adgo_deployments'
BASE_LOG_URL = 'https://console.cloud.google.com/logs/viewer?project=sonic-wavelet-124006&resource=container&filters=label:container.googleapis.com%2Fpod_name:'

MIGRATION_TEXT_MAP = ['None', ':hotsprings: Hot', ':snowflake: Cold']


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
        self.migration_text = MIGRATION_TEXT_MAP[config.MIGRATION_LEVEL]
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
        """
        message = '{} Deployment Processing'.format(self.cluster_text)
        attachments = [{
                    'fallback': 'Image={} Migrations={}'.format(self.image, self.migration_text),
                    'color': 'good',
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
        deployments: list = [],
        requires_migration_rollback: bool = False
    ):
        has_error = error_message is not None

        if has_error:
            message = '<@here>\n:ultra_fire: {} Deployment Failed :ultra_fire:'.format(self.cluster_text)

            attachments = [{
                        'fallback': '{} Deployment Error={}'.format(self.cluster_text, error_message),
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

            if (requires_migration_rollback):
                attachments[0]['fields'].append({
                    'title': 'RESOLVE ISSUES OR ROLLBACK MIGRATION',
                    'value': '',
                    'short': False
                })

            for deployment in deployments:
                scaled_down = deployment.get('scaled_down', False)
                updated_image = deployment.get('updated_image', False)
                if (scaled_down or updated_image):
                    attachments.append({
                        'fallback': '{} Error'.format(deployment['name']),
                        'color': 'danger',
                        'attachment_type': 'default',
                        'text': '*{}*'.format(deployment['name']),
                        'fields': []
                    })
                    if (scaled_down):
                        attachments[-1]['fields'].append(
                            {
                                'title': 'Requires Scale Up',
                                'value': 'Desired Replicas: {}'.format(deployment['replicas']),
                                'short': False
                            },
                        )
                    if (updated_image):
                        attachments[-1]['fields'].append(
                            {
                                'title': 'Requires Image Rollback',
                                'value': 'Desired Image: {}'.format(deployment['image']),
                                'short': False
                            },
                        )
        else:
            message = '<@here>\n:party_yeet: {} Deployment Completed Successfully :party_yeet:'.format(self.cluster_text)
            attachments = [{
                        'fallback': '{} Deployment Success'.format(self.cluster_text),
                        'color': 'good',
                        'attachment_type': 'default',
                        'fields': []
                    }]

        attachments[0]['actions'] = [{
                "type": "button",
                "name": "logs",
                "text": "View GCP Logs",
                "url": '{}{}'.format(BASE_LOG_URL, config.HOST_NAME),
                "style": "primary",
        }]

        self.send_thread_reply(message=message, attachments=attachments, reply_broadcast=True)
