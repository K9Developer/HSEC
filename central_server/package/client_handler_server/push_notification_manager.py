import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request

SERVICE_ACCOUNT_FILE = './certs/serviceAccountKey.json'
PROJECT_ID = 'hsec-c39e5'

def __get_access_token():
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=['https://www.googleapis.com/auth/cloud-platform']
    )
    credentials.refresh(Request())
    return credentials.token

def send_notification(
    token: str,
    title: str,
    body: str,
    logger=None,
    data: dict | None = None,
    click_url: str = "/notifications",
) -> None:
   
    access_token = __get_access_token()

    message: dict = {
        "message": {
            "token": token,

            "notification": {
                "title": title,
                "body": body,
            },

            "webpush": {
                "headers": {
                    "Urgency": "high",
                },
                "fcm_options": {
                    "link": click_url,
                },
                "notification": { 
                    "title": title,
                    "body": body,
                },
            },

            "data": data or {},
        }
    }

    url = f"https://fcm.googleapis.com/v1/projects/{PROJECT_ID}/messages:send"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    resp = requests.post(url, headers=headers, json=message, timeout=10)
   
    if resp.status_code != 200:
        if logger:
            logger.error(f"Failed to send notification: {resp.status_code} - {resp.text}")
        else:
            print(f"Failed to send notification: {resp.status_code} - {resp.text}")
