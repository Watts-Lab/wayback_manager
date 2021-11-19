import pandas as pd
import json
import requests
import datetime

WAYBACK_FORMAT = '%Y%m%d%H%M%S'

class WaybackCDX:
    def __init__(self):
        self.cdx_format = \
            'https://web.archive.org/cdx/search/cdx?url=$URL&output=json&from=$START&to=$END'

    def download_all(self, url):
        raw_json = requests.get(
            self.cdx_format.replace('$URL', url).replace('&from=$START&to=$END', ''))
        listy_data = json.loads(raw_json.text)
        first_line = listy_data.pop(0)
        df = pd.DataFrame.from_records(listy_data,
                                       columns=first_line)

        return df

    def download_period(self, url, period_start: datetime.datetime, period_end: datetime.datetime):
        period_start_wbc = period_start.strftime(WAYBACK_FORMAT)
        period_end_wbc = period_end.strftime(WAYBACK_FORMAT)
        raw_json = requests.get(
            self.cdx_format.replace('$URL', url).replace('$START', period_start_wbc).replace('$END', period_end_wbc))
        listy_data = json.loads(raw_json.text)
        first_line = listy_data.pop(0)
        df = pd.DataFrame.from_records(listy_data, columns=first_line)
        return df

    def get_intervals(self, url, hrs=1, period_start=None, period_end=None):
        df = self.download_all(url)


if __name__ == '__main__':
    scr = WaybackCDX()
    print(scr.download_period('www.nytimes.com', datetime.datetime(2020, 1, 1), datetime.datetime(2020, 12, 31)).head())


