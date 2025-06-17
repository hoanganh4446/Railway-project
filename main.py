import time
from keep_alive import keep_alive
import check

keep_alive()

while True:
    try:
        check.main()
    except Exception as e:
        print(f"⚠️ Lỗi: {e}")
    time.sleep(120)
