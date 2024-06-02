import datetime
import arrow
import tempfile
import os
import json

from ics import Calendar
from urllib.request import urlretrieve
from urllib.parse import urlparse, unquote


def months_strs(month):
    month_names = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
                   "November", "December"]
    return month_names[month - 1]


def weekdays_strs(weekday):
    weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    return weekday_names[weekday]


if __name__ == '__main__':
    try:
        with open(f"settings.json", "r") as settings:
            json_parsed = json.load(settings)
            ics_url = json_parsed["IcsUrl"]
            prev_months = json_parsed["PrevMonths"]
            billing_tags = json_parsed["Tag"]
            amount_per_hour = json_parsed["AmountPerHour"]
    except:
        ics_url = "https://example.com/calendar/Example.ics"
        # Show events since previous n months. 0 = Current month
        prev_months = 0
        billing_tag = ""
        amount_per_hour = 20

    ics_url = unquote(ics_url)
    parsed_url = urlparse(ics_url)
    file_full = os.path.basename(parsed_url.path)
    split_file_full = os.path.splitext(file_full)
    file_name = split_file_full[0]
    file_ext = split_file_full[1]

    temp_path = tempfile.gettempdir()
    today_str = arrow.now().strftime("%Y%m%d")
    ics_filepath = f"{temp_path}{os.sep}{file_name}-{today_str}{file_ext}"

    urlretrieve(ics_url, ics_filepath)

    with open(ics_filepath, mode='r', encoding='utf-8') as file:
        ics_txt = file.read()

    cal = Calendar(ics_txt)

    last_month = arrow.now().shift(months=prev_months)
    events_month = sorted([e for e in cal.events if e.begin.month == last_month.month], key=lambda e: e.begin)

    print(months_strs(last_month.month))
    total_duration = datetime.timedelta()

    cur_day = None
    for event in events_month:
        if billing_tag == "" and len(event.categories) == 0:
            continue

        weekday_name = weekdays_strs(event.begin.weekday())
        weekday_name_short = weekday_name[0:3]
        if cur_day is None or cur_day != event.begin.day:
            cur_day = event.begin.day
            print(f'\t{weekday_name_short} {event.begin.strftime("%d/%m/%Y")}')

        event_hours = int(event.duration.total_seconds() // 3600)
        event_minutes = int(event.duration.total_seconds() % 3600 // 60)
        event_minutes_str = '{:02}'.format(event_minutes)
        event_duration_str = f"{event_hours}h{event_minutes_str}\'"

        if billing_tag != "":
            if len(event.categories) == 0:
                continue
            tag = event.categories.pop()
            if tag.lower() != billing_tag.lower():
                continue
            prefix = f"[{tag}]"
        else:
            prefix = ""

        print(f'\t\t{event.begin.strftime("%H:%M")} a {event.end.strftime("%H:%M")} ({event_duration_str}): {prefix} {event.name}')
        total_duration += event.duration

    hours = int(total_duration.total_seconds() // 3600)
    minutes = int(total_duration.total_seconds() % 3600 // 60)
    minutes_str = '{:02}'.format(minutes)
    print(f"Horas: {hours}h{minutes_str}\'")

    amount_hours = amount_per_hour * hours
    amount_per_quarter = amount_per_hour // 4
    quarter_count = minutes // 15
    amount_quarter = quarter_count * amount_per_quarter
    amount_total = amount_hours + amount_quarter
    print(f"Importe: {amount_total}€ ({amount_per_hour}€/h)")
