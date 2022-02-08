import datetime


def intervals(start: datetime.datetime, end: datetime.datetime, hrs=1):
    leap = datetime.timedelta(hours=hrs)
    if start.minute != 0:
        start = start - datetime.timedelta(minutes=start.minute)
    time = start
    while time <= end:
        yield time
        time += leap
