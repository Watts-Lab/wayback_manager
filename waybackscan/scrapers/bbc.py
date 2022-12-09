import numpy as np

from .base import PublisherScraper
from bs4 import BeautifulSoup
from collections import OrderedDict
from .utils import has_substr

class BBCScraper(PublisherScraper):

    def __init__(self, verbose = False):
        super().__init__(verbose)

    @property
    def front_page_url(self):
        return "https://www.bbc.com/"

    def get_top_article_metadata(self, front_page):
        """Extracts top articles for BBC news front_page

        Based on 1-23-20:
            - there's a section called "module--promo"
                - includes "top articles"
                - then comes the "content-block" which includes "News" and "Sport"
        """
        soup = BeautifulSoup(front_page, features='html.parser')

        # Find top stories DIV
        top_stories = soup.find(
            'section',
            {'class':"module--promo"}
        )
        top_story_links = top_stories.find_all('a', {'class': 'media__link'})

        rank = 1
        articles = OrderedDict()
        for link in top_story_links:
            href = link.get('href')
            href_url = self.clean_wayback_url(href)
            if href_url is None:
                continue
            if any(s in href_url for s in {'/live/', '/worklife/', '/travel/', '/future/'}):
                continue

            headline = link.text.strip()


            articles[href_url] = {
                'rank': rank,
                'href': href,
                'headline': headline,

                # Store original HTML tags
                'html': {
                    'headline': str(headline)
                }
            }
            rank += 1

        return articles

    def scrape_culture_article(self, soup):
        if soup.find('div', {'id': 'story-page'}):
            story_body = soup.find('div', {'id': 'story-page'})

            header = story_body.find('h1', {'class': 'primary-heading'})
            headline = header.text

            body_content = story_body.find('div', {'class': 'body-content'})
            paragraphs = [p.text for p in body_content.find_all('p')]

        else:
            header = soup.find('div', {'class': 'article-headline__text'})
            if header is None:
                return None
            headline = header.text

            article_body = soup.find('div', {'class': 'article__body-content'})
            text_cards = article_body.find_all('div', {'class': ''})
            paragraphs = []
            for card in text_cards:
                pars = [p.text for p in card.find_all('p')]
                paragraphs.extend([p for p in pars if not p.startswith('More like this')])

        article_scrape = {
            'title': headline,
            'paragraphs': paragraphs
        }
        return article_scrape


    def scrape_news_article(self, soup):
        article_scrape = {}

        headline = soup.find('h1')
        if headline is not None: 
            headline = headline.text

        article_body = soup.find('div', {'property': 'articleBody'})
        if not article_body:
            article_body = soup.find('div', {'class': 'story-body'})
        if not article_body:
            article_body = soup.find('article')
        paragraphs = [p.text for p in article_body.find_all(['p', 'h2'])]
        if not paragraphs:
            paragraphs = [p.text for p in article_body.find_all('div', {'data-component': 'text-block'})]
        if headline is None:
            headline = paragraphs[0]
        if self.verbose:
            print(headline)
        article_scrape = {
            'title': headline,
            'paragraphs': paragraphs
        }


        return article_scrape

    def scrape_live_news_article(self, soup):
        header = soup.find(lambda tag: tag.get('id', '').endswith('event-title'))
        headline = header.text

        article_paragraphs = soup.find_all(
            'li',
            {'class': has_substr('post-container')}
        )
        paragraphs = []
        for sub_articles in article_paragraphs:
            title = sub_articles.find('h3', {'class': has_substr('title')})
            if title.find_all('span'):
                title = ' '.join([span.text for span in title.find_all('span')])
            else:
                title = title.text

            body = sub_articles.find_all('div', {'class': has_substr('qa-post-body')})
            par_text = [p.text for b in body for p in b.find_all('p')]

            paragraphs.append([title] + par_text)

        article_scrape = {
            'title': headline,
            'paragraphs': paragraphs
        }
        return article_scrape

    def scrape_article(self, url, timestamp):
        html, archive = self.get_wayback_url(url, timestamp)
        if html is None:
            return None
        asoup = BeautifulSoup(html, features='html.parser')

        # Find what part of the site we are on

        if '/culture/' in url:
            print('Culture article')
            article_scrape = self.scrape_culture_article(asoup)
        elif '/news/' in url:
            # Live article
            if '/live/' in url:
                article_scrape = self.scrape_live_news_article(asoup)
            # News article
            else:
                article_scrape = self.scrape_news_article(asoup)
        else:
            # Default: attempt news
            article_scrape = self.scrape_news_article(asoup)
        if article_scrape is None:
            return None
        article_scrape['html'] = html
        return article_scrape


if __name__ == '__main__':
    import pandas as pd
    from collections import defaultdict
    import pytz
    import datetime as dt
    scraper = BBCScraper(verbose=True)
    sampled_days_fp = '../../analysis/production_run/sampled_days_36.tsv'
    sampled_days = pd.read_csv(sampled_days_fp, sep='\t', index_col=0)
    article_dataset = defaultdict(dict)

    init_scrape_hour = 18
    est_timezone = pytz.timezone("US/Eastern")

    start_idx = 28
    for idx, date_str in enumerate(sampled_days['date'][start_idx:]):
        date = dt.datetime.strptime(date_str, '%Y-%m-%d')
        date += dt.timedelta(hours=init_scrape_hour)
        date = est_timezone.localize(date)

        print(f'Searching Day: {start_idx + idx}, Date/Time:{date}')

        articles = scraper.extract(date)

        publisher = scraper.front_page_url
        article_dataset[publisher][date] = articles
