from base import PublisherScraper
from bs4 import BeautifulSoup
from collections import OrderedDict
from utils import has_substr

class TheGuardianScraper(PublisherScraper):

    def __init__(self, verbose = False):
        super().__init__(verbose)

    @property
    def front_page_url(self):
        return "https://theguardian.com/us"

    def get_top_article_metadata(self, front_page, top_k = 10):
        soup = BeautifulSoup(front_page, features='html.parser')

        rank = 1
        articles = OrderedDict()

        news_cards = soup.find('div', {'class': 'fc-container__inner'})

        sections = soup.find_all('section', {'class': 'fc-container'})
        for section in sections:
            if section.get('id') == 'headlines':
                items = section.find_all('div', {'class': 'fc-item__container'})
                for article in items:
                    header = article.find(attrs={'class': 'fc-item__title'})
                    first_link = header.find('a')

                    href = first_link.get('href')
                    href_url = self.clean_wayback_url(href)

                    if any([s in href_url for s in ['/ng-interactive/', '/video/']]):
                        continue

                    headline = header.get_text(separator=' / ', strip=True)
                    if self.verbose:
                        print(f'Headline: {headline}')

                    articles[href_url] = {
                        'rank': rank,
                        'href': href,
                        'headline': headline,

                        # Store original HTML tags
                        'html': {
                            'headline': str(first_link)
                        }
                    }
                    rank += 1

                # Stop after we processes headlines
                break
            elif rank < 5:
                # Only get first story of feature
                top_story = section.find('div', {'class': has_substr('container'),
                                                 'data-link': lambda x: not has_substr('-helper')(x)})
                if top_story is None:
                    if section.find(['a', 'div'], {'class': [has_substr('coronavirus-newsletter'),
                                                             'coronavirus-thrasher',
                                                             has_substr('__contribute')]}):
                        continue  # They made this a persistent headline so it messes with our system sometimes.

                first_link = top_story.find('a', {'data-link-name': 'article'})
                if first_link is None:
                    continue

                href = first_link.get('href')
                href_url = self.clean_wayback_url(href)

                if any([s in href_url for s in ['/ng-interactive/', '/video/']]):
                    continue

                headline = first_link.get_text(separator=' ', strip=True)

                articles[href_url] = {
                    'rank': rank,
                    'href': href,
                    'headline': headline,

                    # Store original HTML tags
                    'html': {
                        'headline': str(first_link)
                    }
                }
                rank += 1

        return articles

    def scrape_article(self, url, timestamp):
        html, archive = self.get_wayback_url(url, timestamp)
        asoup = BeautifulSoup(html, features='html.parser')

        header = asoup.find('h1')
        headline = header.get_text(separator=' ').strip('\n')
        if self.verbose:
            print(headline)

        if '/live/' in url:
            updates = asoup.find_all('div', {'itemprop': 'liveBlogUpdate'})
            paragraphs = []
            for update in updates:
                for par in update.find_all('p'):
                    if 'published-time' in par.get('class', []):
                        continue

                    paragraphs.append(par.get_text())
        else:
            body = asoup.find('div', {'itemprop': 'articleBody'})
            if body:
                paragraphs = [p.get_text() for p in body.find_all('p')]
            else:
                paragraphs = [p.get_text() for p in asoup.find_all('p')]

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
    scraper = TheGuardianScraper(verbose=True)
    sampled_days_fp = '../../analysis/production_run/sampled_days_36.tsv'
    sampled_days = pd.read_csv(sampled_days_fp, sep='\t', index_col=0)
    article_dataset = defaultdict(dict)

    # %%

    init_scrape_hour = 18
    est_timezone = pytz.timezone("US/Eastern")

    start_idx = 0
    for idx, date_str in enumerate(sampled_days['date'][start_idx:]):
        date = dt.datetime.strptime(date_str, '%Y-%m-%d')
        date += dt.timedelta(hours=init_scrape_hour)
        date = est_timezone.localize(date)

        print(start_idx + idx, date)

        articles = scraper.extract(date)


        publisher = scraper.front_page_url
        article_dataset[publisher][date] = articles
