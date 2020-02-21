import requests
import config
import logging

from requests.auth import HTTPBasicAuth
from jinja2 import Environment, FileSystemLoader

loader = FileSystemLoader("templates")
template_env = Environment(loader=loader)

MAILGUN_URL = f"https://api.mailgun.net/v3/{config.MAILGUN_DOMAIN}"


def send(recipients, subject, body):
    auth = HTTPBasicAuth(username="api", password=config.MAILGUN_KEY)

    response = requests.post(
        f"{MAILGUN_URL}/messages",
        auth=auth,
        data={
            "subject": subject,
            "from": "release@adgo.io",
            "to": config.MAILGUN_TO,
            "html": body,
        },
    )

    logging.info("Mail response=%s", response.json())


def send_notification_email(cards):
    title = f"{config.PROJECT.title()} Release Notification | {config.TAG}"
    email_template = template_env.get_template("email_notification.html")

    send(
        recipients=[config.MAILGUN_TO],
        subject=title,
        body=email_template.render(cards=cards, title=title),
    )
