from base import PublisherScraper
from bs4 import BeautifulSoup
from collections import OrderedDict
from .utils import has_substr


class WSJScraper(PublisherScraper):

    def __init__(self, verbose = False):
        super().__init__(verbose)

    @property
    def front_page_url(self):
        return "https://wsj.com"

    def get_top_article_metadata(self, front_page, top_k = 5):
        soup = BeautifulSoup(front_page, features='html.parser')

        rank = 1
        articles = OrderedDict()

        main = soup.find_all('article')

        # This goes column depth first
        headlines = [art.find('h3') for art in main]
        headlines = [h for h in headlines if h is not None]  # Some mild jank sorry.
        for headline_tag in headlines:

            first_link = headline_tag.find('a')
            href = first_link.get('href')
            href_url = self.clean_wayback_url(href)

            # Skip over blogs (and crosswords are also on "blogs." second level.
            if href_url.startswith("https://blogs."):
                continue

            # Gets headline and subheading
            headline = headline_tag.get_text(separator=' \n ', strip=True)

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
        html, archive = self.get_wayback_url(url, timestamp)
        asoup = BeautifulSoup(html, features='html.parser')

        header = asoup.find('h1', {'class': has_substr('article-headline')})
        if header is None:
            header = asoup.find('h1')  # I removed the banner wrap

        headline = header.get_text(separator=' \n ', strip=True)

        if '/livecoverage/' in url:
            paragraphs = []
            cards = asoup.find_all('div', {'class': 'LiveCoverageCard'})
            for card in cards:
                card_header = card.find('div', {'class': has_substr('header')})
                if card_header:
                    card_headline = card_header.find('h3')
                    if card_headline:
                        paragraphs.append(card_headline.get_text())

                card_text = card.find('div', {'class': 'Text'})
                if card_text:
                    for par in card_text.find_all('p'):
                        paragraphs.append(par.get_text(' '))
        else:
            article_body = asoup.find('div', {'class': 'wsj-snippet-body'})
            try:
                paragraphs = [p.get_text(separator = '\n') for p in article_body.find_all('p')]
            except AttributeError:
                print('Hit attribute error, possibly we hit the paywall??')  # TODO: Figure this out
                # Sometimes we hit a paywall on wall street journal articles. Most of the time it's the 6th article
                # So we're leaving them out of the study. There are some examples where it happens earlier.
                paragraphs = None

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
    scraper = WSJScraper(verbose=True)
    sampled_days_fp = '../../analysis/production_run/sampled_days_36.tsv'
    sampled_days = pd.read_csv(sampled_days_fp, sep='\t', index_col=0)
    article_dataset = defaultdict(dict)

    # %%

    init_scrape_hour = 18
    est_timezone = pytz.timezone("US/Eastern")

    start_idx = 12
    for idx, date_str in enumerate(sampled_days['date'][start_idx:]):
        date = dt.datetime.strptime(date_str, '%Y-%m-%d')
        date += dt.timedelta(hours=init_scrape_hour)
        date = est_timezone.localize(date)

        print(start_idx + idx, date)

        articles = scraper.extract(date)


        publisher = scraper.front_page_url
        article_dataset[publisher][date] = articles
