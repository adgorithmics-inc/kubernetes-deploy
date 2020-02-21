import requests
import config
from lib.mailgun import send_notification_email

VERSION = 1
URL = f"https://api.trello.com/{VERSION}"


def handle_response(path, response):
    if response.status_code != 200:
        raise ValueError(f"Something went wrong requesting {path}: {response.text}")

    return response.json()


def get(path):
    response = requests.get(
        url=f"{URL}/{path}",
        params={"key": config.TRELLO_KEY, "token": config.TRELLO_TOKEN},
    )
    return handle_response(path, response)


def post(path, params):
    params["key"] = config.TRELLO_KEY
    params["token"] = config.TRELLO_TOKEN
    response = requests.post(url=f"{URL}/{path}", params=params)
    return handle_response(path, response)


def put(path, params):
    params["key"] = config.TRELLO_KEY
    params["token"] = config.TRELLO_TOKEN

    response = requests.put(url=f"{URL}/{path}", data=params)
    return handle_response(path, response)


def get_cards():
    return get(path=f"lists/{config.TRELLO_LIST_ID}/cards")


def archive(card_id):
    put(path=f"cards/{card_id}", params={"closed": "true"})


def add_comment(card_id):
    post(
        path=f"cards/{card_id}/actions/comments",
        params={"text": f"released as part of {config.TAG}"},
    )


def cleanup_trello():
    if not config.TRELLO_SEND_NOTIFICATION:
        return
    cards = get_cards()
    for card in cards:
        add_comment(card_id=card["id"])
        archive(card_id=card["id"])
    send_notification_email(cards)
