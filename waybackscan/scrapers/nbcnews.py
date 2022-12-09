from base import PublisherScraper
from bs4 import BeautifulSoup
from collections import OrderedDict
from utils import has_substr
from waybackpy.exceptions import WaybackError

class NBCNewsScraper(PublisherScraper):

    def __init__(self, verbose = False):
        super().__init__(verbose)

    @property
    def front_page_url(self):
        return "https://www.nbcnews.com/"

    def get_top_article_metadata(self, front_page, top_k = 10):
        soup = BeautifulSoup(front_page, features='html.parser')

        rank = 1
        articles = OrderedDict()

        cover_headline = soup.find('div', {'class': has_substr('cover-spread__headline')})
        if cover_headline:
            first_link = cover_headline.find('a')

            href = first_link.get('href')
            href_url = self.clean_wayback_url(href)
            headline = first_link.get_text()

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

        ## There are two front-page-contents
        main_content = soup.find('div', {'class': 'layout-rightRailTabbed'})
        news_cards = main_content.find_all(['div', 'h2'], {'class': has_substr('headline')})

        # print(news_cards)
        for article in news_cards:
            if article.name == 'h2':
                first_link = article.find('a')
            else:
                info = article.find('div', {'class': has_substr('info')})
                if info:
                    headline = info.find({'h3', 'h2'})
                    first_link = headline.find('a')
                else:
                    continue

            if first_link is None:
                continue

            href = first_link.get('href')
            href_url = self.clean_wayback_url(href)
            if href_url is None:
                continue
            if any(s in href_url for s in {'/slideshow/', '/opinion/'}):
                continue
            headline = first_link.get_text()

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

        header = asoup.find('h1', {'data-test': 'article-hero__headline'})
        if header is None:
            if self.verbose:
                print('Could not find any content, skipping...')
            return None

        headline = header.parent.get_text(separator='\n')

        article_content = asoup.find('div', {'class': 'article-body__content'})
        # print(article_content)


        paragraphs = []
        for par in article_content.find_all(['p', 'h2']):
            if par.get('data-test') == 'byline':
                continue
            if par.text.startswith("Download the"):
                continue

            paragraphs.append(par.get_text(separator='\n'))

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
    scraper = NBCNewsScraper(verbose=True)
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
