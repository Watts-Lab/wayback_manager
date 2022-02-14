from base import PublisherScraper
from bs4 import BeautifulSoup
from collections import OrderedDict
from utils import has_substr

class ABCNewsScraper(PublisherScraper):

    def __init__(self, verbose = False):
        super().__init__(verbose)

    @property
    def front_page_url(self):
        return "https://www.abcnews.go.com/"

    def get_top_article_metadata(self, front_page, top_k = 5):
        soup = BeautifulSoup(front_page, features='html.parser')

        rank = 1
        articles = OrderedDict()

        top_row = soup.find('div', {'class': 'hp-trio'})
        top_stories = top_row.find_all('figure', {'class': 'story'})
        for story in top_stories:
            story_caption = story.find_next_sibling('figcaption')

            first_link = story_caption.find('a')
            href = first_link.get('href')
            href_url = self.clean_wayback_url(href, remove_params = False)

            headline = first_link.get_text(separator=' \n ', strip=True)

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

        headline_list = top_row.find('article', {'class': 'headlines'})
        headline_links = headline_list.find_all('a')
        for headline_tag in headline_links:
            href = headline_tag.get('href')
            href_url = self.clean_wayback_url(href, remove_params = False)
            if href_url is None:
                continue

            headline = headline_tag.get_text(separator=' \n ', strip=True)

            articles[href_url] = {
                'rank': rank,
                'href': href,
                'headline': headline,

                # Store original HTML tags
                'html': {
                    'headline': str(headline_tag)
                }
            }
            rank += 1

            if rank > top_k:
                break

        if self.verbose:
            print(list(articles.keys()), sep='\n')

        return articles

    def scrape_article(self, url, timestamp):
        html, archive = self.get_wayback_url(url, timestamp)
        asoup = BeautifulSoup(html, features='html.parser')

        header = asoup.find('div', {'class': 'Article__Headline'})

        # Gets subtitle
        headline = header.get_text(separator=' \n ', strip=True)

        article_body = asoup.find(attrs={'class': 'Article__Content'})
        paragraphs = [p.get_text(separator = '\n', strip=True) for p in article_body.find_all('p')]

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
    scraper = ABCNewsScraper(verbose=True)
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
