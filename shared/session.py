# shared/session.py
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def get_retry_session():
    session = requests.Session()
    retries = Retry(
        total=3,               # Thử lại tối đa 3 lần
        backoff_factor=1,      # Tăng thời gian chờ giữa các lần retry
        status_forcelist=[500, 502, 503, 504]  # Retry nếu gặp các mã lỗi này
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount('https://', adapter)
    session.mount('http://', adapter)
    return session
