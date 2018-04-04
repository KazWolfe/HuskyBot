import json

import requests

APP_BASE = "https://developer.lametric.com/api/v1/dev/widget/update/com.lametric.{app_id}"


def push_to_lametric(app_id: str, data: dict, access_token: str):
    headers = {
        "Accept": "application/json",
        "X-Access-Token": access_token,
        "Cache-Control": "no-cache"
    }

    return requests.post(url=APP_BASE.format(app_id=app_id), data=json.dumps(data), headers=headers)


def build_data(icon: str, text: str) -> dict:
    """
    Create a LaMetric Data Packet for transmission.

    In order to streamline building the JSON data the LaMetric API needs, this method exists. Pass in
    what you need, get a nice dict out.

    :param icon: The Icon ID from the website you would like to pass.
    :param text: The text (up to 255? characters) to display on the device.
    :return: Returns a dict (not str!) for consumption/sending by the API.
    """
    return {
        'frames': [
            {
                "text": text,
                "icon": icon
            }
        ]
    }
