import configparser
import time
from cdx import WaybackCDX, WAYBACK_FORMAT
import datetime
import pickle
import os
from tqdm import tqdm
import requests

HERE = os.path.dirname(__file__)
config = configparser.ConfigParser()
config.read(os.path.join(HERE, 'config.ini'))
URL = "www.pbs.org/newshour"
PUBCODE = "pbsnewshour"

def get_request(timestamp, intervals):
    try:
        r = requests.get(f'https://web.archive.org/web/{timestamp}id_/https://{URL}')
    except requests.exceptions.ConnectionError:
        time.sleep(60)
        r = requests.get(f'https://web.archive.org/web/{timestamp}id_/https://{URL}')
    except requests.exceptions.TooManyRedirects:
        time.sleep(60)
        new_timestamp_i = int(intervals.set_index('timestamp').index.get_loc(timestamp)) + 1
        new_timestamp = intervals['timestamp'].iloc[new_timestamp_i]
        return get_request(new_timestamp, intervals)
    return r


if __name__ == '__main__':
    cdxer = WaybackCDX()
    tqdm.write('Acquiring CDX data')
    yesterday = datetime.datetime.now() - datetime.timedelta(days=3)
    intervals = cdxer.get_intervals(URL, hrs=1, period_start=datetime.datetime(2018, 1, 1),
                                    period_end=yesterday)

    if not os.path.exists('/home/coen/Public/Wayback'):
        os.mkdir('/home/coen/Public/Wayback')
    if not os.path.exists(f'/home/coen/Public/Wayback/{pubcode}'):
        os.mkdir(f'/home/coen/Public/Wayback/{pubcode}')
    if not os.path.exists(f'/home/coen/Public/Wayback/{pubcode}/raw'):
        os.mkdir(f'/home/coen/Public/Wayback/{pubcode}/raw')
    if not os.path.exists(f'/home/coen/Public/Wayback/{pubcode}/articles'):
        os.mkdir(f'/home/coen/Public/Wayback/{pubcode}/articles')
    if not os.path.exists(f'/home/coen/Public/Wayback/{pubcode}/parsed'):
        os.mkdir(f'/home/coen/Public/Wayback/{pubcode}/parsed')

    tqdm.write('Downloading data...')

    for timestamp in tqdm(intervals['timestamp'][intervals['is_target']]):
        if os.path.exists(f'/home/coen/Public/Wayback/{pubcode}/raw/{timestamp}.pkl'):
            continue
        r = get_request(timestamp, intervals)
        html = r.text
        with open(f'/home/coen/Public/Wayback/{pubcode}/raw/{timestamp}.pkl', 'wb') as f:
            pickle.dump(html, f)
