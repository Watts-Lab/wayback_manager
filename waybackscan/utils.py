from datetime import datetime, timedelta
import re
from dateutil import rrule
from pytz import UTC
from tzlocal import get_localzone

HERE = get_localzone()

"""A la elliot, just copying it here so we dont step on each others toes"""
def clean_text(text):
    flags = [
        "(ap)",
        "associated press",
        "(cnn)",
        "reuters",
        "VIDEO:",
        "breaking news",
        "getty image",
        "your inbox",
        "The news and stories that matter, delivered weekday mornings",
        "mailto:",
        "Your browser does not support",
        "article is in your queue",
        "Image",
        "Credit",
        " for The New York Times",
        "/The New York Times",
        "Here's what to know",
        "Return to menu",
    ]

    pattern_inline = re.compile(
        "[<>\[]http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
    )
    text = pattern_inline.sub("", text)

    out_text = []
    for sent in re.split(r"(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s", text):
        if (
            sent
            and not any(x in sent for x in flags)
            and len([x for x in sent.split(" ") if not x.isupper()]) > 0
        ):
            out_text.append(sent)

    return " ".join(out_text)

def intervals(start: datetime, end: datetime, hrs=1):
    leap = timedelta(hours=hrs)
    if start.minute != 0:
        start = start - timedelta(minutes=start.minute)
    time = start
    while time <= end:
        yield time
        time += leap

WAYBACK_FORMAT = '%Y%m%d%H%M%S'

def date_extract(s, comp: re.Pattern):
    match_obj = comp.search(s)
    if match_obj:
        return match_obj.group(0)
    else:
        return None


def xform(s, fmt=WAYBACK_FORMAT, tz=UTC):
    # This feels kinda hacky but it might work?
    today = datetime.now()
    datestring = today.strftime(fmt)
    dateformat_pattern = re.sub(r"\d", r"\\d", datestring)
    extracted_string = date_extract(s, re.compile(dateformat_pattern))
    if extracted_string:
        return datetime.strptime(extracted_string, fmt).replace(tzinfo=tz)
    else:
        print(f"datestring {s} does not appear to contain a date in "
              f"format {fmt}, please check your input data, "
              f"this datestring will be dropped!")
        return None


def bins(start: datetime, end: datetime, resolution: str):
    assert resolution in {"years", "days", "months", "weeks", "hours"}
    rrule_str = resolution[:-1].upper() + "LY"
    interval = getattr(rrule, rrule_str)
    corr_delta = len(list(rrule.rrule(interval, dtstart=start, until=end)))
    return corr_delta

def ref_times(start: datetime, end: datetime, at):
    for i in range((end - start).days + 1):
        for subtime in at:
            timei = start + timedelta(days=i)
            if not subtime.tzinfo:
                tz_at = HERE
            else:
                tz_at = subtime.tzinfo
            timei = timei.replace(hour=subtime.hour, minute=subtime.minute, second=subtime.second, microsecond=subtime.microsecond, tzinfo=tz_at)
            yield timei

