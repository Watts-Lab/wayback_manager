#!/usr/bin/env python
import argparse
from waybackscan.cdx import WaybackCDX
from datetime import datetime
from pytz import timezone
from tzlocal import get_localzone
import dateparser
import sys

URL_EXCEPTIONS = {
        "abcnews": "www.abcnews.go.com",
        "npr": "www.npr.org",
        "pbs": "www.pbs.org/newshour",
        "bbc": "www.bbc.com/news"
        }
HERE = get_localzone()


class DateParse(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        super().__init__(option_strings, dest, nargs=nargs, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        parsed_date = dateparser.parse(values)
        if not parsed_date.tzinfo:
            parsed_date = parsed_date.replace(tzinfo=HERE)
        setattr(namespace, self.dest, parsed_date)


class TimeParse(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        super().__init__(option_strings, dest, nargs=nargs, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        out = []
        for value in values:
            outdate = dateparser.parse(value)
            if not outdate.tzinfo:
                outdate = outdate.replace(tzinfo=HERE)
            out.append(outdate.timetz())
        setattr(namespace, self.dest, out)


class IntervalParse(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        super().__init__(option_strings, dest, nargs=nargs, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        out = []
        for value in values:
            tardate = dateparser.parse(value)
            if not tardate.tzinfo:
                tardate = tardate.replace(tzinfo=HERE)
            tartz = tardate.tzinfo
            out.append(round((datetime.now().replace(tzinfo=tartz) - tardate).total_seconds() / 3600))
        setattr(namespace, self.dest, out[0])

class PublisherParse(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if values in URL_EXCEPTIONS:
            setattr(namespace, 'url', URL_EXCEPTIONS[values])
        else:
            setattr(namespace, 'url', f'www.{values}.com')


def cli():
    parser = argparse.ArgumentParser()
    targetgrp = parser.add_mutually_exclusive_group(required=True)
    targetgrp.add_argument("-p", "--publisher", type=str, action=PublisherParse)
    targetgrp.add_argument("-u", "--url", type=str)
    dategrp = parser.add_argument_group()
    dategrp.add_argument("-s", "--start", type=str, action=DateParse)
    dategrp.add_argument("-e", "--end", type=str, action=DateParse)
    freqgrp = parser.add_mutually_exclusive_group()
    freqgrp.add_argument("-i", "--interval", type=str, action=IntervalParse, nargs=1)
    freqgrp.add_argument("-a", "--at", type=str, action=TimeParse, nargs='+')
    parser.add_argument("outfile", type=argparse.FileType(), nargs="?", default=sys.stdout)
    parser.add_argument("-f", "--fail_ok", action='store_false')

    args = parser.parse_args()
    
    url = args.url
    cdxer = WaybackCDX()

    if args.interval:
        output = cdxer.get_intervals(url, hrs=args.interval, period_start=args.start, period_end=args.end, filt=args.fail_ok)
    elif args.at:
        output = cdxer.get_at_time(url, at=args.at, period_start=args.start, period_end=args.end, filt=args.fail_ok)
    else:
        output = cdxer.download_period(url, period_start=args.start, period_end=args.end, filt=args.fail_ok)

    if args.at or args.interval:
        output[output['is_target']].to_csv(args.outfile, sep="\t", index=None)
    else:
        output.to_csv(args.outfile, sep='\t', index=None)


if __name__ == "__main__":
    cli()
