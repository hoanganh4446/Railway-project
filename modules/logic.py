import datetime
from . import config, airtable, telegram

# Ngưỡng cảnh báo dạng (số giờ, nhãn)
ALERT_THRESHOLDS = [(1, "1 giờ"), (0.5, "30 phút"), (1 / 6, "10 phút")]

def parse_time(iso_str):
    if not iso_str:
        return None
    return datetime.datetime.fromisoformat(iso_str.rstrip('Z')).astimezone(
        config.VN_TZ)

def calculate_running_time(start_time, now, paused_total):
    return round(((now - start_time).total_seconds() / 3600) - paused_total, 2)

def handle_pause(record, now, paused_total):
    is_paused = record.get('Is Paused', False)
    paused_start_str = record.get('Paused Start Time')
    paused_start = parse_time(paused_start_str)
    status = record.get('Status', '')
    update_payload = {}

    if is_paused:
        if not paused_start_str:  # Only set Paused Start Time if it is None
            update_payload['Paused Start Time'] = now.isoformat()
        if status != 'Tạm dừng':  # Only update status if it's not already paused
            update_payload['Status'] = 'Pause'

    elif not is_paused and paused_start:
        # Calculate the total paused time and reset the pause
        added = round((now - paused_start).total_seconds() / 3600, 2)
        paused_total = round(paused_total + added, 2)
        update_payload.update({
            'Paused Time (hrs)': added,
            'Total Pause Time (hours)': paused_total,
            'Paused Start Time': None,
            'Last Resume Time': now.isoformat(),
            'Status': 'Running'  # Resume status
        })

    return update_payload, paused_total


def should_send_warning(remaining_test):
    # Ngưỡng cảnh báo, có thể điều chỉnh theo yêu cầu
    ALERT_THRESHOLDS = [(1, "1 giờ"), (0.5, "30 phút"), (1 / 6, "10 phút")]

    # Kiểm tra nếu remaining_test nhỏ hơn ngưỡng
    for hours, label in ALERT_THRESHOLDS:
        if remaining_test <= hours:
            return hours, label  # Trả về mức cảnh báo và nhãn (label)

    return None, None  # Nếu không có cảnh báo

def process_device(record, now):
    fields = record.get('fields', {})
    device_id = fields.get('Device ID')
    start_date_str = fields.get('Start Date')
    paused_total = fields.get('Total Pause Time (hours)', 0)
    status = fields.get('Status', 'Unknown')

    if not device_id or not start_date_str:
        return

    update_payload = {}

    start_time = parse_time(start_date_str)
    pause_updates, paused_total = handle_pause(fields, now, paused_total)
    update_payload.update(pause_updates)

    if fields.get("Is Paused") and status != "Pause":
        # Only update the Airtable if it's a pause status change
        if update_payload:
            airtable.update_record(record['id'], update_payload)
            print(f"✅ Đã cập nhật trạng thái Pause cho {device_id}")
        return

    running_time = calculate_running_time(start_time, now, paused_total)
    if not fields.get('Is Paused', False):
        update_payload['Running Time (hours)'] = running_time

    test_interval = fields.get('Test Interval (hours)', 100)  # Ensure it's set if missing
    last_tested_at = fields.get('Last Tested At (hours)', 0) # Get Last Tested At, default to 0

    # Tính toán next_test theo giờ
    next_test_hours = round(paused_total + last_tested_at + test_interval, 2)

    # Chuyển đổi next_test_hours thành đối tượng datetime
    # test_time là thời điểm thực tế cần kiểm tra tiếp theo
    test_time = start_time + datetime.timedelta(hours=next_test_hours)

    # Định dạng test_time thành chuỗi để lưu vào trường Single line text
    update_payload['Next Test (hours)'] = test_time.strftime('%Y-%m-%d %H:%M:%S')

    remaining_test = round(next_test_hours - running_time, 2)

    if remaining_test <= 0:
        if not fields.get("Is Paused"):  # Mark the device as paused if needed
            update_payload.update({
                'Is Paused': True,
                'Paused Start Time': now.isoformat(),
                'Last Tested At (hours)': running_time, # Update Last Tested At when pausing due to test completion
                'Status': 'Pause'
            })

    # Calculate the Expected End based on Total Pause Time and Target Time
    expected_end = start_time + datetime.timedelta(hours=(fields.get('Target Time (hours)', 100) + paused_total))
    update_payload['Expected End'] = expected_end.isoformat()

    print(f"--- Thiết bị: {device_id} ---")
    print(f"Location:        {fields.get('Location', 'Unknown')}")
    print(f"Status:          {status}")
    print(f"Start:           {start_time.strftime('%Y-%m-%d %H:%M:%S%z')}")
    print(f"Now:             {now.strftime('%Y-%m-%d %H:%M:%S%z')}")
    print(f"Paused total:    {paused_total:.2f} giờ")
    print(f"Running:         {running_time:.2f} giờ")
    print(f"Target:          {fields.get('Target Time (hours)', 100)} giờ")
    print(f"Last Tested At:  {last_tested_at:.2f} giờ")
    print(f"Test Interval:   {test_interval:.2f} giờ")
    print(f"Next Test Time:  {test_time.strftime('%Y-%m-%d %H:%M:%S')}") # In ra định dạng mới
    print(f"Remaining:       {remaining_test:.2f} giờ")
    print(f"Expected End:    {expected_end.strftime('%Y-%m-%d %H:%M:%S%z')}")


    # Send warning if applicable
    hours, label = should_send_warning(remaining_test)
    if label:
        telegram.notify_device(device_id, next_test_hours, test_time, label) # Truyền next_test_hours cho Telegram

    # Update Airtable with any changes
    if update_payload:
        res = airtable.update_record(record['id'], update_payload)
        if res.status_code == 200:
            print(f"✅ Đã cập nhật {device_id}")
        else:
            print(f"❌ Lỗi cập nhật {device_id}: {res.text}")