from base import PublisherScraper
from bs4 import BeautifulSoup
from collections import OrderedDict
from utils import has_substr

class HuffpostScraper(PublisherScraper):

    def __init__(self, verbose = False):
        super().__init__(verbose)

    @property
    def front_page_url(self):
        return "https://www.huffpost.com/"

    def get_top_article_metadata(self, front_page, top_k = 5):
        soup = BeautifulSoup(front_page, features='html.parser')

        rank = 1
        articles = OrderedDict()

        front_top = soup.find('div', {'class': 'front-page-top'})
        if front_top:
            top_headline = front_top.find('div', {'class': has_substr('headline__text')})

            first_link = top_headline.find('a')

            href = first_link.get('href')
            href_url = self.clean_wayback_url(href)
            headline = first_link.get_text()

            articles[href_url] = {
                'rank': rank,
                'href': href,
                'headline': headline,

                # Store original HTML tags
                'html': {
                    'headline': str(top_headline)
                }
            }
            rank += 1

        ## There are two front-page-contents
        latest_news = soup.find_all('div', {'class': 'front-page-content'})
        news_cards = [c for div in latest_news for c in div.find_all('div', {'class': 'card'})]

        for article in news_cards:
            link = article.find('a', {'class' : 'card__headline'})

            href = link.get('href')
            href_url = self.clean_wayback_url(href)
            if '/highline/' in href_url:
                continue
            headline = link.get_text()

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
        html, archive = self.get_wayback_url(url, timestamp)
        asoup = BeautifulSoup(html, features='html.parser')

        # Huffington post categorizes their "entries" with this label tag.
        label = asoup.find('a', {'class': 'label'})
        if label is not None:
            print(label.text)
            if label.text in {'Wellness', 'Relationships', 'Style & Beauty', 'Food & Drink'}:
                return None

        header = asoup.find('div', {'class': 'headline'})
        headline = header.get_text(separator=' ')

        article_content = asoup.find_all('div', {'class': 'text'})
        paragraphs = [p.get_text() for text in article_content for p in text.find_all('p')]

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
    scraper = HuffpostScraper(verbose=True)
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
