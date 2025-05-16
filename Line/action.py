import configSetting
import requests
import json


def send_msg_to_bot(msg: str) -> None:
    headers = {
        'Authorization': f'Bearer {configSetting.line_bot_access_token}',
        'Content-Type': 'application/json'}
    body = {
        'to': configSetting.line_bot_group_id,
        'messages': [{
            'type': 'text',
            'text': f'{msg}'
        }]
    }
    resp = requests.request('POST', 'https://api.line.me/v2/bot/message/push', headers=headers, data=json.dumps(body).encode('utf-8'))