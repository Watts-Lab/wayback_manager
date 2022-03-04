import configparser
import time
from scrapers.wsj import WSJScraper
from cdx import WaybackCDX, WAYBACK_FORMAT
import datetime
import pickle
import os
from tqdm import tqdm
import requests

HERE = os.path.dirname(__file__)
config = configparser.ConfigParser()
config.read(os.path.join(HERE, 'config.ini'))


def get_request(timestamp):
    try:
        r = requests.get(f'https://web.archive.org/web/{timestamp}/https://www.wsj.com/')
    except requests.exceptions.ConnectionError:
        time.sleep(60)
        r = requests.get(f'https://web.archive.org/web/{timestamp}/https://www.wsj.com/')
    except requests.exceptions.TooManyRedirects:
        new_timestamp_i = intervals.set_index('timestamp').index.get_loc(timestamp) + 1
        new_timestamp = intervals['timestamp'].iloc[new_timestamp_i]
        return get_request(new_timestamp)
    return r


if __name__ == '__main__':
    cdxer = WaybackCDX()
    scraper = WSJScraper()
    tqdm.write('Acquiring CDX data')
    intervals = cdxer.get_intervals('www.wsj.com', hrs=1, period_start=datetime.datetime(2015, 1, 1),
                                    period_end=datetime.datetime(2019, 12, 31, 23, 59, 59))

    if not os.path.exists('/home/coen/Remote/Data/Wayback'):
        os.mkdir('/home/coen/Remote/Data/Wayback')
    if not os.path.exists('/home/coen/Remote/Data/Wayback/wsj'):
        os.mkdir('/home/coen/Remote/Data/Wayback/wsj')
    if not os.path.exists('/home/coen/Remote/Data/Wayback/wsj/raw'):
        os.mkdir('/home/coen/Remote/Data/Wayback/wsj/raw')
    if not os.path.exists('/home/coen/Remote/Data/Wayback/wsj/articles'):
        os.mkdir('/home/coen/Remote/Data/Wayback/wsj/articles')

    tqdm.write('Downloading data...')

    for timestamp in tqdm(intervals['timestamp'][intervals['is_target']]):
        if os.path.exists(f'/home/coen/Remote/Data/Wayback/wsj/raw/{timestamp}.pkl'):
            continue
        r = get_request(timestamp)
        html = r.text
        try:
            article_metadata = scraper.get_top_article_metadata(html)
            with open(f'/home/coen/Remote/Data/Wayback/wsj/{timestamp}.pkl', 'wb') as f:
                pickle.dump(article_metadata, f)
            with open(f'/home/coen/Remote/Data/Wayback/wsj/raw/{timestamp}.pkl', 'wb') as f:
                pickle.dump(html, f)
            # for article in article_metadata:
            #     art_dump = scraper.extract(timestamp)
            #     with open(f'/home/coen/Remote/Data/Wayback/wsj/articles/{timestamp}.pkl', 'wb') as f:
            #         pickle.dump(art_dump, f)

        except AttributeError:
            with open(f'/home/coen/Remote/Data/Wayback/wsj/raw/{timestamp}.pkl', 'wb') as f:
                pickle.dump(html, f)
