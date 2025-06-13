# daily_report.py
import datetime
from modules import config, airtable, telegram

def send_daily_summary():
    now = datetime.datetime.now(config.VN_TZ)
    if now.hour != 7:
        return

    response = airtable.fetch_records()
    if response.status_code != 200:
        print("❌ Lỗi lấy dữ liệu trong daily report")
        return

    records = response.json().get('records', [])
    lines = []
    for rec in records:
        fields = rec.get('fields', {})
        device_id = fields.get('Device ID', 'Unknown')
        remaining = fields.get('Next Test (hours)', 0)
        status = fields.get('Status', 'Unknown')
        lines.append(f"📍 {device_id} | {status} | Còn {remaining:.1f} giờ")

    if not lines:
        return

    summary = "📊 Báo cáo tổng hợp lúc 7h sáng:\n" + "\n".join(lines)
    telegram.send_telegram_message(summary)
