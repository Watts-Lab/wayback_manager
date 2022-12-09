import datetime
from urllib.parse import urlparse
from datetime import timedelta


def intervals(start: datetime.datetime, end: datetime.datetime, hrs=1):
    leap = datetime.timedelta(hours=hrs)
    if start.minute != 0:
        start = start - datetime.timedelta(minutes=start.minute)
    time = start
    while time <= end:
        yield time
        time += leap


def ref_times(start: datetime.datetime, end: datetime.datetime, at):
    for i in range((end - start).days + 1):
        for subtime in at:
            timei = start + timedelta(days=i)
            timei = timei.replace(hour=subtime.hour, minute=subtime.minute, second=subtime.second, microsecond=subtime.microsecond)
            yield timei


def pubcode(url):
    parseresult = urlparse(url)
    return parseresult.netloc.split('.')[1]
