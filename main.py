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


def rollback_months(prev_months):
    start_month = arrow.now().shift(months=-prev_months)
    current_month = arrow.now()
    months_to_show = []
    m = start_month
    while m.year < current_month.year or (m.year == current_month.year and m.month <= current_month.month):
        months_to_show.append(m)
        m = m.shift(months=1)
    return months_to_show


def print_header():
    col_date     = 10
    col_start    = 5
    col_end      = 5
    col_elapsed  = 8
    col_tags     = 20
    col_billable = 10
    col_cost     = 7

    header = (
        f"{'Date':<{col_date}} | {'Start':<{col_start}} | {'End':<{col_end}} | "
        f"{'Elapsed':<{col_elapsed}} | {'Tags':<{col_tags}} | {'Is Billable':<{col_billable}} | "
        f"{'Cost':<{col_cost}} | Description"
    )
    separator = "-" * len(header)
    print(header)
    print(separator)
    return col_date, col_start, col_end, col_elapsed, col_tags, col_billable, col_cost, separator


def download_ical_to_file(ics_url):
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
    return ics_filepath


if __name__ == '__main__':
    try:
        with open(f"settings.json", "r") as settings:
            json_parsed = json.load(settings)
            ics_url = json_parsed["IcsUrl"]
            prev_months = json_parsed["PrevMonths"]
            tags_included_raw = json_parsed["TagsIncluded"]
            tags_excluded_raw = json_parsed.get("TagsExcluded", "")
            amount_per_hour = json_parsed["AmountPerHour"]
    except:
        ics_url = "https://example.com/calendar/Example.ics"
        # Show events since previous n months. 0 = Current month
        prev_months = 0
        tags_included_raw = ""
        tags_excluded_raw = ""
        amount_per_hour = 20

    tags_included = [x.strip() for x in tags_included_raw.split(',') if x.strip()]
    tags_excluded = [x.strip() for x in tags_excluded_raw.split(',') if x.strip()]

    ics_filepath = download_ical_to_file(ics_url)
    with open(ics_filepath, mode='r', encoding='utf-8') as file:
        ics_txt = file.read()

    cal = Calendar(ics_txt)
    grand_total_duration = datetime.timedelta()
    months_to_show = rollback_months(prev_months)

    for month_arrow in months_to_show:
        events_month = sorted(
            [e for e in cal.events if e.begin.month == month_arrow.month and e.begin.year == month_arrow.year],
            key=lambda e: e.begin
        )

        print(f"{months_strs(month_arrow.month)} {month_arrow.year}")
        month_duration = datetime.timedelta()
        col_date, col_start, col_end, col_elapsed, col_tags, col_billable, col_cost, separator = print_header()

        for event in events_month:
            event_hours = int(event.duration.total_seconds() // 3600)
            event_minutes = int(event.duration.total_seconds() % 3600 // 60)
            event_minutes_str = '{:02}'.format(event_minutes)
            event_duration_str = f"{event_hours}h{event_minutes_str}\'"

            event_tags_lower = [t.lower() for t in event.categories]
            tags_str = ', '.join(sorted(event.categories)) if event.categories else ''

            included = (
                len(tags_included) == 0 or any(t.lower() in event_tags_lower for t in tags_included)
            ) and not any(t.lower() in event_tags_lower for t in tags_excluded)

            if included:
                event_cost = amount_per_hour * event_hours + (event_minutes // 15) * (amount_per_hour // 4)
                month_duration += event.duration
            else:
                event_cost = 0

            print(
                f"{event.begin.strftime('%d/%m/%Y'):<{col_date}} | "
                f"{event.begin.strftime('%H:%M'):<{col_start}} | "
                f"{event.end.strftime('%H:%M'):<{col_end}} | "
                f"{event_duration_str:<{col_elapsed}} | "
                f"{tags_str:<{col_tags}} | "
                f"{'Yes' if included else 'No':<{col_billable}} | "
                f"{str(event_cost) + '€':<{col_cost}} | "
                f"{event.name}"
            )

        print(separator)

        hours = int(month_duration.total_seconds() // 3600)
        minutes = int(month_duration.total_seconds() % 3600 // 60)
        minutes_str = '{:02}'.format(minutes)
        print(f"Horas: {hours}h{minutes_str}\'")

        amount_hours = amount_per_hour * hours
        amount_per_quarter = amount_per_hour // 4
        quarter_count = minutes // 15
        amount_quarter = quarter_count * amount_per_quarter
        amount_total = amount_hours + amount_quarter
        print(f"Importe: {amount_total}€ ({amount_per_hour}€/h)")
        print()

        grand_total_duration += month_duration

    if len(months_to_show) > 1:
        total_hours = int(grand_total_duration.total_seconds() // 3600)
        total_minutes = int(grand_total_duration.total_seconds() % 3600 // 60)
        total_minutes_str = '{:02}'.format(total_minutes)
        print(f"--- TOTAL ---")
        print(f"Horas: {total_hours}h{total_minutes_str}\'")
        amount_hours = amount_per_hour * total_hours
        amount_per_quarter = amount_per_hour // 4
        quarter_count = total_minutes // 15
        amount_quarter = quarter_count * amount_per_quarter
        amount_total = amount_hours + amount_quarter
        print(f"Importe: {amount_total}€ ({amount_per_hour}€/h)")
