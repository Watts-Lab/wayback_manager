from base import PublisherScraper
from bs4 import BeautifulSoup
from collections import OrderedDict
from utils import has_substr

class WashingtonpostScraper(PublisherScraper):

    def __init__(self, verbose = False):
        super().__init__(verbose)

    @property
    def front_page_url(self):
        return "https://washingtonpost.com"

    def get_top_article_metadata(self, front_page, top_k = 5):
        soup = BeautifulSoup(front_page, features='html.parser')

        rank = 1
        articles = OrderedDict()

        top_headlines = soup.find_all(['h1', 'h2', 'h3'], {'class': ('headline', 'font--headline')})
        headline_sizes = [headline.get('class')[1] for headline in top_headlines]

        # huge < large < medium < small < x-small < xx-small ...
        top_headlines_by_size = sorted(zip(top_headlines, headline_sizes), key = lambda x: x[1])
        top_headlines = [headline[0] for headline in top_headlines_by_size]

        for headline_tag in top_headlines:
            # Avoid links to opinions
            if headline_tag.find_parent('div', {'class': 'opinions-chain'}):
                continue

            first_link = headline_tag.find('a')
            href = first_link.get('href')
            href_url = self.clean_wayback_url(href)
            # Skip over stuff from washington post magazine, they're opinion and they break the archive's redirect algo
            # Also podcasts and the stuff in the "graphics" folder (I think they're investigative journalism...
            if any(s in href_url for s in ("/podcasts/", "/investigations/", "/graphics/", "/magazine/", "/lifestyle/")):
                if self.verbose:
                    print(f"Triggered a skip on {href_url}")
                continue

            # In june of 2020, the washington post made a separate front page for the coronavirus pandemic that
            # was permanenetly linked as an article to the front page. Since this is outside the scope of the project
            # we chose to exclude it.
            if href_url == "https://www.washingtonpost.com/coronavirus/":
                if self.verbose:
                    print(f"Triggered a skip on {href_url}")
                continue

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

        graphics = False
        # Different ways of encoding headline
        header = asoup.find('h1', {'data-qa': 'headline'})
        if header is None:
            header = asoup.find('h1', {'itemprop': 'headline'})
            if header is None:
                header = asoup.find('h2', {'class': 'pg-h1 balanced-headline'})
                # Wapo has these weird entertainment news articles that don't follow the rules. Here we'll just tell the subheading parser to prepare for that weirdness.
                graphics = True

        headline = header.get_text(separator=' \n ', strip=True)

        if graphics:
            subheading = asoup.find('h1', {'class': 'pg-intro'})
        else:
            subheading = asoup.find('h2', {'data-qa': 'subheadline'})
        if subheading:
            subheadline = subheading.get_text(separator=' \n ', strip=True)
            headline += ' \n ' + subheadline

        article_body = asoup.find('div', {'class': has_substr('article')})
        paragraphs = [p.get_text(separator = '\n') for p in article_body.find_all('p')]

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
    scraper = WashingtonpostScraper(verbose=True)
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