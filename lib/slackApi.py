import config
import logging
from slackclient import SlackClient

log = logging.getLogger(__name__)

SLACK_CHANNEL = "adgo_deployments"
BASE_LOG_URL = "https://console.cloud.google.com/logs/viewer?project=sonic-wavelet-124006&resource=container&filters=label:container.googleapis.com%2Fpod_name:"

MIGRATION_TEXT_MAP = ["None", ":hotsprings: Hot", ":snowflake: Cold"]


class SlackApi:
    """
    Wrapper for slack to send deployment status updates
    """

    def __init__(self):
        is_production = config.APP_ENV == "production"
        self.slacker = SlackClient(token=config.SLACK_TOKEN)
        self.cluster_text = "Production" if is_production else "Development"
        self.image = config.IMAGE
        self.icon = ":release:" if is_production else ":canned_food:"
        self.username = "{} Deployer".format(self.cluster_text)
        self.migration_text = MIGRATION_TEXT_MAP[config.MIGRATION_LEVEL]
        self.thread_ts = 0

    def send_message(self, **kwargs):
        """
        Sends message to Slack
        """
        try:
            log.debug(
                "Sending to Slack #{}: text={}".format(
                    SLACK_CHANNEL, kwargs.get("text")
                )
            )
            returned = self.slacker.api_call(
                "chat.postMessage",
                channel=SLACK_CHANNEL,
                username=self.username,
                icon_emoji=self.icon,
                **kwargs,
            )
            log.debug("Returned from Slack: {}".format(returned))
            self.thread_ts = returned.get("ts")
        except Exception as error:
            log.error(error)

    def send_thread_reply(self, text, **kwargs):
        """
        Sends message to Slack thread
        """
        self.send_message(thread_ts=self.thread_ts, text=text, **kwargs)

    def send_initial_message(self):
        text = "{} Deployment Processing".format(self.cluster_text)
        attachments = [
            {
                "fallback": "Image={} Migrations={}".format(
                    self.image, self.migration_text
                ),
                "color": "good",
                "attachment_type": "default",
                "fields": [
                    {"title": "Image", "value": self.image, "short": False},
                    {
                        "title": "Migrations",
                        "value": self.migration_text,
                        "short": False,
                    },
                    {
                        "title": "Logs",
                        "value": "kubectl logs -f {}".format(config.HOST_NAME),
                        "short": False,
                    },
                ],
            }
        ]

        self.send_message(text=text, attachments=attachments)

    def send_completion_message(
        self,
        error_message: str = None,
        error_handling_message: str = None,
        deployments: list = [],
        requires_migration_rollback: bool = False,
    ):
        has_error = error_message is not None

        if has_error:
            text = "<!here|here>\n:fire: {} Deployment Failed :fire:".format(
                self.cluster_text
            )

            attachments = [
                {
                    "fallback": "{} Deployment Error={}".format(
                        self.cluster_text, error_message
                    ),
                    "color": "danger",
                    "attachment_type": "default",
                    "fields": [
                        {
                            "title": "Deployment Error",
                            "value": error_message,
                            "short": False,
                        },
                        {
                            "title": "Recovery Status",
                            "value": error_handling_message,
                            "short": False,
                        },
                    ],
                }
            ]

            if requires_migration_rollback:
                attachments[0]["fields"].append(
                    {
                        "title": "RESOLVE ISSUES OR ROLLBACK MIGRATION",
                        "value": "",
                        "short": False,
                    }
                )

            for deployment in deployments:
                scaled_down = deployment.get("scaled_down", False)
                updated_image = deployment.get("updated_image", False)
                if scaled_down or updated_image:
                    attachments.append(
                        {
                            "fallback": "{} Error".format(deployment["name"]),
                            "color": "danger",
                            "attachment_type": "default",
                            "text": "*{}*".format(deployment["name"]),
                            "fields": [],
                        }
                    )
                    if scaled_down:
                        attachments[-1]["fields"].append(
                            {
                                "title": "Requires Scale Up",
                                "value": "Desired Replicas: {}".format(
                                    deployment["replicas"]
                                ),
                                "short": False,
                            }
                        )
                    if updated_image:
                        attachments[-1]["fields"].append(
                            {
                                "title": "Requires Image Rollback",
                                "value": "Desired Image: {}".format(
                                    deployment["image"]
                                ),
                                "short": False,
                            }
                        )
        else:
            text = "<!here|here>\n:yeet: {} Deployment Completed Successfully :yeet:".format(
                self.cluster_text
            )
            attachments = [
                {
                    "fallback": "{} Deployment Success".format(self.cluster_text),
                    "color": "good",
                    "attachment_type": "default",
                    "fields": [],
                }
            ]

        attachments[0]["actions"] = [
            {
                "type": "button",
                "name": "logs",
                "text": "View GCP Logs",
                "url": "{}{}".format(BASE_LOG_URL, config.HOST_NAME),
                "style": "primary",
            }
        ]

        self.send_thread_reply(text, attachments=attachments, reply_broadcast=True)
