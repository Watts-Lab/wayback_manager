import argparse
from waybackscan.cdx import WaybackCDX
from datetime import datetime
import dateparser
import sys


class DateParse(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        super().__init__(option_strings, dest, nargs=nargs, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, dateparser.parse(values))


class TimeParse(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        super().__init__(option_strings, dest, nargs=nargs, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        out = []
        for value in values:
            out.append(dateparser.parse(value).time())
        setattr(namespace, self.dest, out)


class IntervalParse(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        super().__init__(option_strings, dest, nargs=nargs, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        out = []
        for value in values:
            out.append(round((datetime.now() - dateparser.parse(value)).total_seconds() / 3600))
        setattr(namespace, self.dest, out[0])


def cli():
    parser = argparse.ArgumentParser()
    targetgrp = parser.add_mutually_exclusive_group(required=True)
    targetgrp.add_argument("-p", "--publisher", type=str)
    targetgrp.add_argument("-u", "--url", type=str)
    dategrp = parser.add_argument_group()
    dategrp.add_argument("-s", "--start", type=str, action=DateParse)
    dategrp.add_argument("-e", "--end", type=str, action=DateParse)
    freqgrp = parser.add_mutually_exclusive_group()
    freqgrp.add_argument("-i", "--interval", type=str, action=IntervalParse, nargs=1)
    freqgrp.add_argument("-a", "--at", type=str, action=TimeParse, nargs=1)
    parser.add_argument("outfile", type=argparse.FileType(), nargs="?", default=sys.stdout)

    args = parser.parse_args()

    url = None
    if args.publisher:
        url = f"www.{args.publisher}.com"
        publisher = args.publisher
    elif args.url:
        url = args.url
    cdxer = WaybackCDX()

    if args.interval:
        output = cdxer.get_intervals(url, hrs=args.interval, period_start=args.start, period_end=args.end)
    if args.at:
        output = cdxer.get_at_time(url, at=args.at, period_start=args.start, period_end=args.end)
    else:
        output = cdxer.download_period(url, period_start=args.start, period_end=args.end)

    if args.at or args.interval:
        output[output['is_target']].to_csv(args.outfile, sep="\t")
    else:
        output.to_csv(args.outfile, sep='\t')


if __name__ == "__main__":
    cli()
