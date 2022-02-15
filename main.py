import configparser
import os
from scrapers.nytimes import NYTimesScraper
from cdx import WaybackCDX, WAYBACK_FORMAT
import datetime
import pickle
import os
from tqdm import tqdm

HERE = os.path.dirname(__file__)
config = configparser.ConfigParser()
config.read(os.path.join(HERE, 'config.ini'))

if __name__ == '__main__':
    cdxer = WaybackCDX()
    scraper = NYTimesScraper()
    tqdm.write('Acquiring CDX data')
    intervals = cdxer.get_intervals('www.nytimes.com', hrs=1, period_start=datetime.datetime(2020, 1, 1),
                                    period_end=datetime.datetime(2020, 12, 31, 23, 59, 59))

    if not os.path.exists('/home/coen/Remote/Data/Wayback'):
        os.mkdir('/home/coen/Remote/Data/Wayback')
    if not os.path.exists('/home/coen/Remote/Data/Wayback/nytimes'):
        os.mkdir('/home/coen/Remote/Data/Wayback/nytimes')

    tqdm.write('Downloading data...')

    for timestamp in tqdm(intervals['timestamp']):
        article = scraper.scrape_article('www.nytimes.com', datetime.datetime.strptime(timestamp, WAYBACK_FORMAT))
        with open(f'/home/coen/Remote/Data/Wayback/nytimes/{timestamp}.pkl', 'wb') as f:
            pickle.dump(article, f)
