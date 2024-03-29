import pandas as pd
import json
import requests
import datetime
import time
from .utils import intervals, ref_times
from pytz import  UTC
from tzlocal import get_localzone

WAYBACK_FORMAT = '%Y%m%d%H%M%S'
HERE = get_localzone()


class WaybackCDX:
    def __init__(self):
        self.cdx_format = \
            'https://web.archive.org/cdx/search/cdx?url=$URL&output=json&from=$START&to=$END'
        self.closest_format = \
            'https://web.archive.org/cdx/search/cdx?url=$URL&limit=1&closest=$TIME&sort=closest&output=json&from=$TIME'

    def download_all(self, url, filt=True):
        raw_json = requests.get(
            self.cdx_format.replace('$URL', url).replace('&from=$START&to=$END', ''))
        listy_data = json.loads(raw_json.text)
        first_line = listy_data.pop(0)
        df = pd.DataFrame.from_records(listy_data,
                                       columns=first_line)
        df['datetime'] = df['timestamp'].apply(lambda s: datetime.datetime.strptime(s, WAYBACK_FORMAT).replace(tzinfo=UTC))
        if filt:
            df = df[df['statuscode'] == '200']
        return df

    def download_period(self, url, period_start: datetime.datetime, period_end: datetime.datetime, filt=True):
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
        df['datetime'] = df['timestamp'].apply(lambda s: datetime.datetime.strptime(s, WAYBACK_FORMAT).replace(tzinfo=UTC))
        if filt:
            df = df[df['statuscode'] == '200']
        return df

    def get_closest(self, url, target: datetime.datetime, retries=0, max_retries=30):
        # https://github.com/internetarchive/wayback/issues/237#issuecomment-1042577291
        cdx_req = self.closest_format.replace('$URL', url)
        cdx_req = cdx_req.replace("$TIME", target.strftime(WAYBACK_FORMAT))
        try:
            raw_json = requests.get(cdx_req)
        except requests.exceptions.ConnectionError as e:
            if retries >= max_retries:
                raise e
            else:
                time.sleep(5)
                return self.get_closest(url, target, retries=retries+1)
        try:
            listy_data = json.loads(raw_json.text)
        except json.decoder.JSONDecodeError as e:
            if retries >= max_retries:
                raise e
            else:
                time.sleep(5)
                return self.get_closest(url, target, retries=retries+1)
        first_line = listy_data.pop(0)
        df = pd.DataFrame.from_records(listy_data, columns=first_line)
        df['datetime'] = df['timestamp'].apply(lambda s: datetime.datetime.strptime(s, WAYBACK_FORMAT))
        return df.iloc[0]
   
   # def nearest_without_being_before(df: pd.DataFrame, dates: list[datetime.datetime], tol=1):
       # delta = datetime.timedelta(hrs=tol)
       # end = [d + delta for d in dates]




    def get_intervals(self, url, hrs=1, period_start=None, period_end=None, filt=True):
        if period_start and period_end:
            df = self.download_period(url, period_start, period_end, filt=filt)
        else:
            df = self.download_all(url, filt=filt)
        reference_times = intervals(period_start, period_end, hrs=hrs)
        storage_collection = df['datetime'].copy(deep=True).sort_values()
        # Trying to find a higher performing method
        target_times = set()
        for time in list(reference_times):
            storage_collection = storage_collection[storage_collection >= time]
            try:
                target_times.add(storage_collection.iloc[0])
            except IndexError:
                pass
        new_df = df.copy(deep=True)
                
        new_df['is_target'] = df['datetime'].isin(target_times)
        new_df = new_df.drop_duplicates(subset='timestamp', keep='first')
        return new_df

    def get_at_time(self, url, at=(datetime.time(hour=9, tzinfo=HERE)), period_start=None, period_end=None, filt=True):
        if period_start or period_end:
            df = self.download_period(url, period_start, period_end, filt=filt)
        else:
            df = self.download_all(url, filt=filt)
        if not period_start:
            period_start = df.datetime.min()
        if not period_end:
            period_end = df.datetime.max()
        reference_times = ref_times(period_start, period_end, at)
        storage_collection = df['datetime'].copy(deep=True).sort_values()
        target_times = set()
        for time in list(reference_times):
            storage_collection = storage_collection[storage_collection >= time]
            try:
                target_times.add(storage_collection.iloc[0])
            except IndexError:
                pass
        new_df = df.copy(deep=True)
        new_df['is_target'] = df['datetime'].isin(target_times)
        new_df = new_df.drop_duplicates(subset='timestamp', keep='first')
        return new_df


if __name__ == '__main__':
    scr = WaybackCDX()
    print(scr.get_intervals('www.nytimes.com', hrs=1, period_start=datetime.datetime(2015, 1, 1),
                            period_end=datetime.datetime(20, 12, 31, 23, 59, 59)))
