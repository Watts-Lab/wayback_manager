from base import PublisherScraper
from bs4 import BeautifulSoup
from collections import OrderedDict
from waybackpy.exceptions import WaybackError

class FoxnewsScraper(PublisherScraper):

    def __init__(self, verbose = False):
        super().__init__(verbose)

    @property
    def front_page_url(self):
        return "https://www.foxnews.com/"

    def get_top_article_metadata(self, front_page):
        soup = BeautifulSoup(front_page, features='html.parser')

        main_body = soup.find_all('div', {'class': 'collection-spotlight'})
        secondary = soup.find_all('div', {'class': 'main-secondary'})

        rank = 1
        articles = OrderedDict()
        for collection in main_body + secondary:
            article_tags = collection.find_all('article', {'class': 'article'})

            for article in article_tags:
                header = article.find('h2', {'class': 'title'})
                first_link = header.find('a')

                href = first_link.get('href')
                href_url = self.clean_wayback_url(href)
                if not href_url:
                    continue
                if any(s in href_url for s in {"/video.", "foxbusiness.com", "/lifestyle/"}):
                    continue

                headline = first_link.get_text(separator=' ')
                if self.verbose:
                    print(headline)

                articles[href_url] = {
                    'rank': rank,
                    'href': href,
                    'headline': headline,

                    # Store original HTML tags
                    'html': {
                        'headline': str(header)
                    }
                }
                rank += 1
                if rank > 5:
                    break

        return articles

    def scrape_article(self, url, timestamp):
        try:
            html, archive = self.get_wayback_url(url, timestamp)
        except WaybackError as e:
            return None
        asoup = BeautifulSoup(html, features='html.parser')

        header = asoup.find('h1', {'class': 'headline'})
        headline = header.get_text()

        article_content = asoup.find('div', {'class': 'article-body'})
        paragraphs = [p.get_text() for p in article_content.find_all('p', recursive=False)]

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
    scraper = FoxnewsScraper(verbose=True)
    sampled_days_fp = '../../analysis/production_run/sampled_days_36.tsv'
    sampled_days = pd.read_csv(sampled_days_fp, sep='\t', index_col=0)
    article_dataset = defaultdict(dict)

    init_scrape_hour = 18
    est_timezone = pytz.timezone("US/Eastern")

    start_idx = 5
    for idx, date_str in enumerate(sampled_days['date'][start_idx:]):
        date = dt.datetime.strptime(date_str, '%Y-%m-%d')
        date += dt.timedelta(hours=init_scrape_hour)
        date = est_timezone.localize(date)

        print(f'Searching Day: {start_idx + idx}, Date/Time:{date}')

        articles = scraper.extract(date)

        publisher = scraper.front_page_url
        article_dataset[publisher][date] = articles
