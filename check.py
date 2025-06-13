import datetime
from modules import config, airtable, logic

def main():
    response = airtable.fetch_records()

    if response.status_code != 200:
        print("❌ Lỗi lấy dữ liệu Airtable")
        print(response.text)
        return

    now = datetime.datetime.now(config.VN_TZ)
    records = response.json().get('records', [])

    for record in records:
        logic.process_device(record, now)
