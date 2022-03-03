from .base import PublisherScraper
from bs4 import BeautifulSoup
from collections import OrderedDict

class NYTimesScraper(PublisherScraper):

    def __init__(self, verbose = False):
        super().__init__(verbose)

    @property
    def front_page_url(self):
        return "https://www.nytimes.com/"

    def get_top_article_metadata(self, front_page):
        soup = BeautifulSoup(front_page, features='html.parser')

        # Find top stories DIV
        top_stories = soup.find(
            'section',
            {'data-block-tracking-id':"Top Stories"}
        )

        rank = 1
        articles = OrderedDict()
        for child in top_stories.children:
            first_link = child.find('a')
            headline = first_link.find('span')

            if not headline is None:
                href = first_link.get('href')
                href_url = self.clean_wayback_url(href)

                # TODO: Consider adding support for live coverage blogs, while it isn't super relevant for Ratio,
                #  it may come up for speed of news.
                if href_url is None:
                    return None

                if any(s in href_url for s in {'/interactive/', '/live/'}):
                    continue

                if self.verbose:
                    print(href)
                    print(headline, headline.text)

                articles[href_url] = {
                    'rank': rank,
                    'href': href,
                    'headline': headline.text,

                    # Store original HTML tags
                    'html': {
                        'a': str(first_link),
                        'headline': str(headline)
                    }
                }
                rank += 1

        return articles

    def scrape_article(self, url, timestamp):
        html, archive = self.get_wayback_url(url, timestamp)
        asoup = BeautifulSoup(html, features='html.parser')

        # Find headline
        headline = asoup.find('title')
        headline = headline.text
        print(headline)

        # Find body
        body = asoup.find('section', {'name': 'articleBody'})
        paragraphs = [par.text for section in body.find_all('div', {'class': 'StoryBodyCompanionColumn'}) for par in section.find_all('p')]

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
    scraper = NYTimesScraper(verbose=True)
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
