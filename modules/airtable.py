import requests
from . import config
from shared.session import get_retry_session

def fetch_records():
    url = f"https://api.airtable.com/v0/{config.BASE_ID}/{config.TABLE_NAME}?view={config.VIEW_NAME}"
    headers = {"Authorization": f"Bearer {config.AIRTABLE_API_KEY}"}
    return requests.get(url, headers=headers)

def update_record(record_id, fields):
    url = f"https://api.airtable.com/v0/{config.BASE_ID}/{config.TABLE_NAME}/{record_id}"
    headers = {
        "Authorization": f"Bearer {config.AIRTABLE_API_KEY}",
        "Content-Type": "application/json"
    }
    return requests.patch(url, headers=headers, json={"fields": fields})
