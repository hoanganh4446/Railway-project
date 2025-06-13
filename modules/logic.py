import datetime
from . import config, airtable, telegram

# Ngưỡng cảnh báo dạng (số giờ, nhãn)
ALERT_THRESHOLDS = [
    (1, "1 giờ"),
    (0.5, "30 phút"),
    (1/6, "10 phút")
]

def parse_time(iso_str):
    if not iso_str:
        return None
    return datetime.datetime.fromisoformat(iso_str.rstrip('Z')).astimezone(config.VN_TZ)

def calculate_running_time(start_time, now, paused_total):
    return round(((now - start_time).total_seconds() / 3600) - paused_total, 2)

def handle_pause(record, now, paused_total):
    is_paused = record.get('Is Paused', False)
    paused_start_str = record.get('Paused Start Time')
    paused_start = parse_time(paused_start_str)
    update_payload = {}

    if is_paused and not paused_start:
        update_payload['Paused Start Time'] = now.isoformat()
    elif not is_paused and paused_start:
        added = round((now - paused_start).total_seconds() / 3600, 2)
        paused_total = round(paused_total + added, 2)
        update_payload.update({
            'Paused Time (hrs)': added,
            'Total Pause Time (hours)': paused_total,
            'Last Resume Time': now.isoformat(),
            'Paused Start Time': None
        })

    return update_payload, paused_total

def should_send_warning(remaining_test):
    for hours, label in ALERT_THRESHOLDS:
        if 0 <= remaining_test - hours <= 0.05:
            return hours, label
    return None, None

def process_device(record, now):
    fields = record.get('fields', {})
    device_id        = fields.get('Device ID')
    start_date_str   = fields.get('Start Date')
    paused_total     = fields.get('Total Pause Time (hours)', 0)
    target_hours     = fields.get('Target Time (hours)', 100)
    test_interval    = fields.get('Test Interval (hours)', 100)
    last_tested_at   = fields.get('Last Tested At (hours)', 0)
    status           = fields.get('Status', 'Unknown')
    testing          = fields.get('Testing', False)
    location         = fields.get('Location', 'Unknown')

    if not device_id or not start_date_str:
        return

    update_payload = {}

    if not testing and status == "AP Testing":
        update_payload['Status'] = 'In progress'

    if testing:
        if update_payload:
            airtable.update_record(record['id'], update_payload)
            print(f"✅ Đã reset Status cho {device_id}")
        return

    start_time = parse_time(start_date_str)
    pause_updates, paused_total = handle_pause(fields, now, paused_total)
    update_payload.update(pause_updates)

    running_time = calculate_running_time(start_time, now, paused_total)
    if not fields.get('Is Paused', False):
        update_payload['Running Time (hours)'] = running_time

    next_test = last_tested_at + test_interval
    remaining_test = round(next_test - running_time, 2)
    test_time = start_time + datetime.timedelta(hours=next_test + paused_total)

    if remaining_test <= 0:
        update_payload.update({
            'Status': 'AP Testing',
            'Testing': True,
            'Last Tested At (hours)': running_time,
            'Location': 'AP'
        })

    expected_end = start_time + datetime.timedelta(hours=target_hours + paused_total + last_tested_at)
    update_payload['Expected End'] = expected_end.isoformat()

    # Log gọn gàng
    print(f"--- Thiết bị: {device_id} ---")
    print(f"Location:      {location}")
    print(f"Status:        {status}")
    print(f"Start:         {start_time.strftime('%Y-%m-%d %H:%M:%S%z')}")
    print(f"Now:           {now.strftime('%Y-%m-%d %H:%M:%S%z')}")
    print(f"Paused total:  {paused_total:.2f} giờ")
    print(f"Running:       {running_time:.2f} giờ")
    print(f"Target:        {target_hours} giờ")
    print(f"Next Test:     {next_test:.2f} giờ")
    print(f"Remaining:     {remaining_test:.2f} giờ")
    print(f"Expected End:  {expected_end.strftime('%Y-%m-%d %H:%M:%S%z')}")

    hours, label = should_send_warning(remaining_test)
    if label:
        telegram.notify_device(device_id, next_test, test_time, label)

    if update_payload:
        res = airtable.update_record(record['id'], update_payload)
        if res.status_code == 200:
            print(f"✅ Đã cập nhật {device_id}")
        else:
            print(f"❌ Lỗi cập nhật {device_id}: {res.text}")
