# telegram.py
import requests
from . import config
from shared.session import get_retry_session
session = get_retry_session()

def send_telegram_message(message):
    url = f'https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage'
    data = {'chat_id': config.CHAT_ID, 'text': message}
    return session.post(url, data=data)

def notify_device(device_id, remaining_hours, test_time, warn_label):
    time_str = test_time.strftime('%H:%M ngày %d/%m/%Y')
    msg = (
        f"🔔 Thiết bị {device_id} sắp đến {remaining_hours:.2f} giờ\n"
        f"⏱️ Thời gian dự kiến: {time_str}\n"
        f"📍 Yêu cầu kiểm tra thiết bị trong vòng {warn_label} tới."
    )
    send_telegram_message(msg)
