from base import PublisherScraper
from bs4 import BeautifulSoup
from collections import OrderedDict
from utils import has_substr

class VoxScraper(PublisherScraper):

    def __init__(self, verbose = False):
        super().__init__(verbose)

    @property
    def front_page_url(self):
        return "https://vox.com"

    def get_top_article_metadata(self, front_page, top_k = 10):
        soup = BeautifulSoup(front_page, features='html.parser')

        rank = 1
        articles = OrderedDict()

        entry_boxes = soup.find_all('div', {'data-analytics-placement': has_substr('hero')})
        for article in entry_boxes:
            header = article.find('h2', {'class': has_substr('title')})

            first_link = header.find('a')
            href = first_link.get('href')
            href_url = self.clean_wayback_url(href)
            headline = header.get_text(separator=' ')

            subheading = header.find_next_sibling('p')
            if subheading:
                headline += ' \n ' + subheading.get_text()

            # Skip over articles linking to "The Highlight", a special editorial column by Vox.
            if '/the-highlight/' in href_url:
                continue

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

        header = asoup.find('h1', {'class': has_substr('title')})
        if header is None:
            if self.verbose:
                print('Could not find any content, skipping...')
            return None

        headline = header.get_text(separator=' \n ', strip=True)

        subtitle = header.find_next_sibling('p', {'class': has_substr('summary')})
        if subtitle:
            headline += ' \n ' + subtitle.get_text(separator=' \n ')

        content = asoup.find('div', {'class': has_substr('entry-content')})

        if content is None:
            if self.verbose:
                print('Could not find any content, skipping...')
            return None

        paragraphs = [p.get_text(separator = '\n') for p in content.find_all('p')]

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
    scraper = VoxScraper(verbose=True)
    sampled_days_fp = '../../analysis/production_run/sampled_days_36.tsv'
    sampled_days = pd.read_csv(sampled_days_fp, sep='\t', index_col=0)
    article_dataset = defaultdict(dict)

    # %%

    init_scrape_hour = 18
    est_timezone = pytz.timezone("US/Eastern")

    # Vox has this weird "DECADE IN REVIEW" page listed as an article on jan 1 2020,
    # so I don't really know what to do with it. It's editorial anyway, but I'm just skipping for now.
    # TODO: Handle New years specials.

    start_idx = 0
    for idx, date_str in enumerate(sampled_days['date'][start_idx:]):
        date = dt.datetime.strptime(date_str, '%Y-%m-%d')
        date += dt.timedelta(hours=init_scrape_hour)
        date = est_timezone.localize(date)

        print(start_idx + idx, date)

        articles = scraper.extract(date)


        publisher = scraper.front_page_url
        article_dataset[publisher][date] = articles