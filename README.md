# Wayback Manager

A collection of tools for dealing with the wayback machine. Provides the command `waybackscan` in addition to being a helpful library.

# Installation

```
pip install git+https://github.com/Watts-Lab/wayback_manager.git
```

## A note on timezones

Timezones are tricky, implicit timezones can cause hard-to-fix bugs. But for ease-of-use, the cli will assume you mean local time unless you specifically say otherwise. The parser should support most time codes.
For timezone abbreviations, you need to provide standard and daylight information, you can't just pass Eastern/Mountain/Central/Pacific (yet). Please use standard time unless absolutely necessary.

# Usage

First, you must provide either a URL to scan, or a domain (assumes the url is `www.$DOMAIN.com`).
With no temporal options, this will scan the entire archive.
A url can be provided with `--url` or `-u`, and a domain can be provided with `-p` or `--publisher`. 
Publisher mode is mainly for compatibility with the News Observatory project, and for most circumstances you should use the url mode.

```
waybackscan -u "www.nytimes.com"
```

Or

```
waybackscan -p nytimes
```

This will return a TSV with ~260,000 rows, each one representing an archival post.
The output TSVs have the following columns:
|Column|Explanation|
|------|-----------|
|urlkey|Provided by wayback machine, unified URL representation|
|timestamp|Time of scrape, in WAYBACK FORMAT '%Y%m%d%H%M%S'|
|original|Non-unified URL|
|mimetype|Mimetype, usually useless, but can be used to determine if the scrape is worth grabbing, encodes the document type|
|statuscode|HTTP status code of scrape, 200 means all good, most others means you need to toss that row|
|digest|Internal Wayback Machine ID|
|length|Length of document in characters (I think, wayback docs don't give units)|
|datetime|time of scrape, in python format '%Y-%m-%d %H:%M:%S'|

By default, any entries where statuscode is not 200 will be dropped after downloading but before temporal filtering..

## Temporal options

You may provide a start date, an end date, and either an interval or an at time. I might add cron formatting later.
The dates are passed through `dateparser` so most formats should be accepted so long as they're unambiguous.
Start dates are specified with `-s` or `--start`.
End dates are specified with `-e` or `--end`.

```
waybackscan -p nytimes -s "Jan 1 2015"
```

Returns all scrapes from the NYTimes since Jan 1 2015.

```
waybackscan -p nytimes -e "Jan 1 2020"
```

Returns all scrapes from the NYTimes before Jan 1 2020

```
waybackscan -p nytimes -s "01-01-2020" -e "Dec 31 2020 at 23:59:59"
```

Returns all scrapes from the NYTimes from the Calendar Year 2020.

An interval (rounds to the nearest calendar hour) can be provided with `-i` or `--interval`.

```
waybackscan -p nytimes -s "01-01-2020 at 10:00 PM" -i "6 hours"
```

Returns a scrape roughly every 6 hours (closest scrape to target time without being before) from Jan 1 2020, starting at 2200 hours and ending right now.

An "at" time can be given to get the scrape closest to that time (without being before) each day in the target period.

```
waybackscan -p nytimes -s "Jan 1 2022" -e "Jan 1 2023" -a "4:00 PM"
```

Will give a scrape for every day in 2022, aiming for 4 PM.

Multiple "at" times can be provided as a list of options.
```
waybackscan -p nytimes -s "Jan 1 2022" -e "Jan 1 2023" -a "9:00 AM" "5:00PM"
```
Will give two scrapes for every day in 2022, one at the start of every day and one at the end.

# 200 mode

The command line flag `-f` or `--fail_ok` will remove a filtering step after downloading that removes all entries such that the status code is not 200.

