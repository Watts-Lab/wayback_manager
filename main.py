import configparser
import time
from scrapers.nytimes import NYTimesScraper
from cdx import WaybackCDX, WAYBACK_FORMAT
import datetime
import pickle
import os
from tqdm import tqdm
import requests

HERE = os.path.dirname(__file__)
config = configparser.ConfigParser()
config.read(os.path.join(HERE, 'config.ini'))


def get_request(timestamp, intervals):
    try:
        r = requests.get(f'https://web.archive.org/web/{timestamp}/https://www.nytimes.com/')
    except requests.exceptions.ConnectionError:
        time.sleep(60)
        r = requests.get(f'https://web.archive.org/web/{timestamp}/https://www.nytimes.com/')
    except requests.exceptions.TooManyRedirects:
        time.sleep(60)
        new_timestamp_i = int(intervals.set_index('timestamp').index.get_loc(timestamp)) + 1
        new_timestamp = intervals['timestamp'].iloc[new_timestamp_i]
        return get_request(new_timestamp, intervals)
    return r


if __name__ == '__main__':
    cdxer = WaybackCDX()
    scraper = NYTimesScraper()
    tqdm.write('Acquiring CDX data')
    yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
    intervals = cdxer.get_intervals('www.nytimes.com', hrs=1, period_start=datetime.datetime(2020, 1, 1),
                                    period_end=yesterday)

    if not os.path.exists('/home/coen/Remote/Data/Wayback'):
        os.mkdir('/home/coen/Remote/Data/Wayback')
    if not os.path.exists('/home/coen/Remote/Data/Wayback/nytimes'):
        os.mkdir('/home/coen/Remote/Data/Wayback/nytimes')
    if not os.path.exists('/home/coen/Remote/Data/Wayback/nytimes/raw'):
        os.mkdir('/home/coen/Remote/Data/Wayback/nytimes/raw')
    if not os.path.exists('/home/coen/Remote/Data/Wayback/nytimes/articles'):
        os.mkdir('/home/coen/Remote/Data/Wayback/nytimes/articles')

    tqdm.write('Downloading data...')

    for timestamp in tqdm(intervals['timestamp'][intervals['is_target']]):
        if os.path.exists(f'/home/coen/Remote/Data/Wayback/nytimes/raw/{timestamp}.pkl'):
            continue
        r = get_request(timestamp, intervals)
        html = r.text
        try:
            article_metadata = scraper.get_top_article_metadata(html)
            with open(f'/home/coen/Remote/Data/Wayback/nytimes/{timestamp}.pkl', 'wb') as f:
                pickle.dump(article_metadata, f)
            with open(f'/home/coen/Remote/Data/Wayback/nytimes/raw/{timestamp}.pkl', 'wb') as f:
                pickle.dump(html, f)
            # for article in article_metadata:
            #     art_dump = scraper.extract(timestamp)
            #     with open(f'/home/coen/Remote/Data/Wayback/nytimes/articles/{timestamp}.pkl', 'wb') as f:
            #         pickle.dump(art_dump, f)

        except AttributeError:
            with open(f'/home/coen/Remote/Data/Wayback/nytimes/raw/{timestamp}.pkl', 'wb') as f:
                pickle.dump(html, f)
