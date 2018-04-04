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
    return {
        'frames': [
            {
                "text": text,
                "icon": icon
            }
        ]
    }
