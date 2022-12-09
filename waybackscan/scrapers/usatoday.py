from base import PublisherScraper
from bs4 import BeautifulSoup
from collections import OrderedDict
from utils import has_substr, not_has_substr
import string

class USATodayScraper(PublisherScraper):

    def __init__(self, verbose = False):
        super().__init__(verbose)

    @property
    def front_page_url(self):
        return "https://www.usatoday.com/"

    def get_top_article_metadata(self, front_page, top_k = 5):
        soup = BeautifulSoup(front_page, features='html.parser')

        rank = 1
        articles = OrderedDict()

        table_rank = {
            'hero': 1,
            'list': 2,
            'briefTile': 3,
            'brief': 3,
            'tile': 4
        }

        top_table_links = soup.find_all('a', {'data-t-l': has_substr('able|')})
        table_type = [link.get('data-t-l', '').split('|')[-1] for link in top_table_links]

        # Remove digits to lookup in dict
        table_rank = [table_rank.get(t_type.rstrip(string.digits + ':'), float('inf')) for t_type in table_type]

        ranked_links = sorted(zip(top_table_links, table_rank), key=lambda x: x[1])
        if not ranked_links:
            links = soup.find_all('a', {"class": has_substr('hfwmm')})
            ranked_links = zip(links, range(len(links)))
        for link_tag, _ in ranked_links:
            href = link_tag.get('href')
            if href is None:
                continue

            href_url = self.clean_wayback_url(href)

            if '/picture-gallery/' in href_url:
                continue

            headline = link_tag.get_text(separator=' \n ', strip=True)

            articles[href_url] = {
                'rank': rank,
                'href': href,
                'headline': headline,

                # Store original HTML tags
                'html': {
                    'headline': str(link_tag)
                }
            }

            rank += 1

            if rank > top_k:
                break

        return articles

    def scrape_article(self, url, timestamp):
        html, archive = self.get_wayback_url(url, timestamp)
        asoup = BeautifulSoup(html, features='html.parser')

        header = asoup.find('h1')
        if not header:
            header = asoup.find

        # Gets subtitle
        headline = header.get_text(separator=' \n ', strip=True)
        if self.verbose:
            print(headline)

        article_body = asoup.find('div', {'class': ['gnt_ar_b']})

        if article_body:
            paragraphs = [p.get_text(separator = '\n', strip=True) for p in article_body.find_all('p')]
        else:
            paragraphs = [p.get_text(separator='\n', strip=True) for p in asoup.find_all('p', {"class": "p-text"})]

        article_scrape = {
            'html': html,
            'title': headline,
            'paragraphs': paragraphs,
            'archive_time': archive.timestamp
        }
        return article_scrape


if __name__ == '__main__':
    import pandas as pd
    from collections import defaultdict
    import pytz
    import datetime as dt
    scraper = USATodayScraper(verbose=True)
    sampled_days_fp = '../../analysis/production_run/sampled_days_36.tsv'
    sampled_days = pd.read_csv(sampled_days_fp, sep='\t', index_col=0)
    article_dataset = defaultdict(dict)

    # %%

    init_scrape_hour = 18
    est_timezone = pytz.timezone("US/Eastern")

    start_idx = 7
    for idx, date_str in enumerate(sampled_days['date'][start_idx:]):
        date = dt.datetime.strptime(date_str, '%Y-%m-%d')
        date += dt.timedelta(hours=init_scrape_hour)
        date = est_timezone.localize(date)

        print(start_idx + idx, date)

        articles = scraper.extract(date)


        publisher = scraper.front_page_url
        article_dataset[publisher][date] = articles