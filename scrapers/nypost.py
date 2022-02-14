from base import PublisherScraper
from bs4 import BeautifulSoup
from collections import OrderedDict
from utils import has_substr
from waybackpy.exceptions import WaybackError

class NYPostScraper(PublisherScraper):

    def __init__(self, verbose = False):
        super().__init__(verbose)

    @property
    def front_page_url(self):
        return "https://www.nypost.com/"

    def get_top_article_metadata(self, front_page, top_k = 5):
        soup = BeautifulSoup(front_page, features='html.parser')

        rank = 1
        articles = OrderedDict()

        top_stories = soup.find_all('article', {'class': 'top-story'})

        for article in top_stories:
            header = article.find('div', {'class': 'headline-container'})
            link = header.find('a') or header.find_parent('a')

            href = link.get('href')
            href_url = self.clean_wayback_url(href)
            if href_url is None:
                continue
            if any(s in href_url for s in {'/video/'}):
                continue
            # Avoids decorators before headlines
            headline = header.find('h3').get_text(separator='\n').strip()

            articles[href_url] = {
                'rank': rank,
                'href': href,
                'headline': headline,

                # Store original HTML tags
                'html': {
                    'headline': str(link)
                }
            }
            rank += 1

            if rank > top_k:
                break

        return articles

    def scrape_article(self, url, timestamp):
        try:
            html, archive = self.get_wayback_url(url, timestamp)
        except WaybackError:
            if self.verbose:
                print('Got an error, probably a permanent redirect. If this happens a bunch of times in a row, '
                      'look into it.')
            return None
        asoup = BeautifulSoup(html, features='html.parser')

        article = asoup.find('div', {'class': 'article-header'})

        header = article.find('h1')
        headline = header.get_text(separator='\n').strip()

        content = article.find('div', {'class': 'entry-content'})
        if content is None:
            if self.verbose:
                print('Could not find any content, skipping...')
            return None

        paragraphs = []
        for par in content.find_all('p'):
            if 'credit' in par.get('class', []):
                continue
            if par.get_text().startswith('View Slideshow'):
                continue

            paragraphs.append(par.get_text(separator= ' '))

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
    scraper = NYPostScraper(verbose=True)
    sampled_days_fp = '../../analysis/production_run/sampled_days_36.tsv'
    sampled_days = pd.read_csv(sampled_days_fp, sep='\t', index_col=0)
    article_dataset = defaultdict(dict)

    init_scrape_hour = 18
    est_timezone = pytz.timezone("US/Eastern")

    start_idx = 0
    for idx, date_str in enumerate(sampled_days['date'][start_idx:]):
        date = dt.datetime.strptime(date_str, '%Y-%m-%d')
        date += dt.timedelta(hours=init_scrape_hour)
        date = est_timezone.localize(date)

        print(f'Searching Day: {start_idx + idx}, Date/Time:{date}')

        articles = scraper.extract(date)

        publisher = scraper.front_page_url
        article_dataset[publisher][date] = articles
