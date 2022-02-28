import pandas as pd
import json
import requests
import datetime
from utils import intervals
from tqdm import tqdm

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
        cdx_req = self.cdx_format.replace('$URL', url)
        if period_end is not None:
            period_end_wbc = period_end.strftime(WAYBACK_FORMAT)
            cdx_req = cdx_req.replace('$END', period_end_wbc)
        else:
            cdx_req = cdx_req.replace('&to=$END', '')
        if period_start is not None:
            period_start_wbc = period_start.strftime(WAYBACK_FORMAT)
            cdx_req = cdx_req.replace('$START', period_start_wbc)
        else:
            cdx_req = cdx_req.replace('&from=$START', '')
        raw_json = requests.get(cdx_req)
        listy_data = json.loads(raw_json.text)
        first_line = listy_data.pop(0)
        df = pd.DataFrame.from_records(listy_data, columns=first_line)
        df['datetime'] = df['timestamp'].apply(lambda s: datetime.datetime.strptime(s, WAYBACK_FORMAT))
        return df

    def get_intervals(self, url, hrs=1, period_start=None, period_end=None):
        if period_start and period_end:
            df = self.download_period(url, period_start, period_end)
        else:
            df = self.download_all(url)
        reference_times = intervals(period_start, period_end, hrs=hrs)
        storage_collection = df['datetime'].copy(deep=True).sort_values()
        target_times = set()
        for time in tqdm(list(reference_times)):
            storage_collection = storage_collection[storage_collection >= time]
            target_times.add(storage_collection.iloc[0])
        new_df = df.copy(deep=True)
        new_df['is_target'] = df['datetime'].isin(target_times)
        return new_df


if __name__ == '__main__':
    scr = WaybackCDX()
    print(scr.get_intervals('www.nytimes.com', hrs=1, period_start=datetime.datetime(2015, 1, 1),
                            period_end=datetime.datetime(20, 12, 31, 23, 59, 59)))
