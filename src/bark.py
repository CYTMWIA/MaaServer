import requests


def notify(key: str, title: str, body: str):
    requests.post(
        f"https://api.day.app/{key}",
        json={
            "title": title,
            "body": body,
        },
    )
