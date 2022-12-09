from bbc import BBCScraper
from breitbart import BreitbartScraper
from cnn import CNNScraper
from foxnews import FoxnewsScraper
from huffpost import HuffpostScraper
from nbcnews import NBCNewsScraper
from nytimes import NYTimesScraper
from theguardian import TheGuardianScraper
from usatoday import USATodayScraper
from vox import VoxScraper
from washingtonpost import WashingtonpostScraper
from wsj import WSJScraper
import pandas as pd
from collections import defaultdict
import pytz
import datetime as dt

scrapers = [BBCScraper(verbose=True), BreitbartScraper(verbose=True), CNNScraper(verbose=True), FoxnewsScraper(verbose=True),
            HuffpostScraper(verbose=True), NBCNewsScraper(verbose=True), NYTimesScraper(verbose=True), TheGuardianScraper(verbose=True), USATodayScraper(verbose=True),
            VoxScraper(verbose=True), WashingtonpostScraper(verbose=True), WSJScraper(verbose=True)]

article_dataset = defaultdict(dict)
for s in scrapers:
    sampled_days_fp = '../../analysis/production_run/sampled_days_36.tsv'
    sampled_days = pd.read_csv(sampled_days_fp, sep='\t', index_col=0)

    init_scrape_hour = 18
    est_timezone = pytz.timezone("US/Eastern")

    start_idx = 0

    for idx, date_str in enumerate(sampled_days['date'][start_idx:]):
        date = dt.datetime.strptime(date_str, '%Y-%m-%d')
        date += dt.timedelta(hours=init_scrape_hour)
        date = est_timezone.localize(date)

        print(f'Searching Day: {start_idx + idx}, Date/Time:{date}')

        articles = s.extract(date)

        publisher = s.front_page_url
        article_dataset[publisher][date] = articles

pd.DataFrame(article_dataset).to_csv('scrape.csv')