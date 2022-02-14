from base import PublisherScraper
from bs4 import BeautifulSoup
from collections import OrderedDict

class BreitbartScraper(PublisherScraper):

    def __init__(self, verbose = False):
        super().__init__(verbose)

    @property
    def front_page_url(self):
        return "https://www.breitbart.com/"

    def get_top_article_metadata(self, front_page):
        soup = BeautifulSoup(front_page, features='html.parser')

        top_article = soup.find('section', {'class': 'top_article_main'}).find_all('article')
        side_articles = soup.find('section', {'class': 'featured_side'}).find_all('article')

        rank = 1
        articles = OrderedDict()
        for article in top_article + side_articles:
            header = article.find('h2')
            first_link = header.find('a')
            headline = first_link.get_text(separator = ' ')

            href = first_link.get('href')
            href_url = self.clean_wayback_url(href)
            if '/clips' in href_url:
                continue

            if self.verbose:
                print(href_url, headline)

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
                # TODO: Revisit this later. I added it because below-the-fold articles are less commonly archived.
                break

        return articles

    def scrape_article(self, url, timestamp):
        html, archive = self.get_wayback_url(url, timestamp)
        asoup = BeautifulSoup(html, features='html.parser')

        article = asoup.find('article')
        header = article.find('header').find('h1')
        headline = header.get_text()

        article_content = article.find('div', {'class': 'entry-content'})
        paragraphs = [p.get_text() for p in article_content.find_all('p')]

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
    scraper = BreitbartScraper(verbose=True)
    sampled_days_fp = '../../analysis/production_run/sampled_days_36.tsv'
    sampled_days = pd.read_csv(sampled_days_fp, sep='\t', index_col=0)
    article_dataset = defaultdict(dict)

    init_scrape_hour = 18
    est_timezone = pytz.timezone("US/Eastern")

    start_idx = 24

    for idx, date_str in enumerate(sampled_days['date'][start_idx:]):
        date = dt.datetime.strptime(date_str, '%Y-%m-%d')
        date += dt.timedelta(hours=init_scrape_hour)
        date = est_timezone.localize(date)

        print(f'Searching Day: {start_idx + idx}, Date/Time:{date}')

        articles = scraper.extract(date)

        publisher = scraper.front_page_url
        article_dataset[publisher][date] = articles
