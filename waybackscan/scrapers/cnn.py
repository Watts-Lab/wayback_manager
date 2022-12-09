"""
CNN scraper is in a weird case because it has to be actually loaded by a web browser to get articles.
We will use a (by default) headless selenium for this, so it may be a RAM-eater, but headless firefox
has some clever tricks that prevent if from getting too out of hand.
"""
import waybackpy
from waybackpy.exceptions import WaybackError
from base import PublisherScraper
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.common.exceptions import WebDriverException
from collections import OrderedDict
import random
from time import sleep
import datetime

class CNNScraper(PublisherScraper):

    def __init__(self, verbose=False, headless=True):
        super(CNNScraper, self).__init__(verbose)
        self.headless = headless

    @property
    def front_page_url(self):
        return "https://www.cnn.com"

    def get_top_article_metadata(self, front_page):
        soup = BeautifulSoup(front_page, 'html.parser')

        # We're just going to take the core window headlines, that is, the ones that aren't associated with
        # a special interest group. These are the ones that are the most prominent on the page-on-load anyway.
        # We're also going to ignore the "Trending Now" ticker at the top of the page because it doesn't
        # give full headlines.

        # We get to skip the part in other scrapers where we select a top stories section because all the
        # main clickthrough articles are front and center and they have a data-analytics tag that we can leverage
        # Video articles have different data-analytics tags so this will skip them.

        top_arts = soup.find_all('h3', {"class": 'cd__headline',
                                        'data-analytics': {'_list-hierarchical-xs_article_',
                                                           '_list-large-vertical_article_',
                                                           '_list-hierarchical-xs_hyperlink_'
                                                           }})
        x_larges = soup.find_all('article', {"class": lambda s: "cd--large" in s})
        x_large_arts = {minisoup.find('h3') for minisoup in x_larges}  # Make a set that contains bigtext articles

        rank = 1
        # Rank is not made explicit on the CNN site per se, but after investigating a bit I'm pretty sure that
        # these list-hierarchical articles are automatically scraped in the order of their internal rank, barring
        # data-analytics type. So I believe that it goes: first xs_article, then the vertical articles, then the rest
        # of the articles in order.
        first = top_arts.pop(0)
        lverts = list(filter(lambda x: x['data-analytics'] == '_list-large-vertical_article_', top_arts))
        others = list(filter(lambda x: x['data-analytics'] != '_list-large-vertical_article_', top_arts))
        otherset = set(others)
        top_right = list(x_large_arts & otherset)
        others = list(otherset - x_large_arts)

        top_arts = [first] + lverts + top_right + others

        articles = OrderedDict()
        for art in top_arts:
            if rank > 10:
                break
            first_link = art.find('a')
            headline = art.find('span', {'class': 'cd__headline-text'})  # 🙄


            href = first_link.get('href')
            href_url = self.clean_wayback_url(href)
            if href_url is None:
                # This is our off-domain ones.
                continue
            # Skip over opinion pieces. Cnn stores them in a special folder 'opinions', for example the URL for a
            # gary kasparov penned piece on putin looks like:
            # https://www.cnn.com/2020/07/05/opinions/russian-democracy-is-a-farce-kasparov/index.html
            # CNN style also uses a different format so we can easily skip over it.
            if any(s in href_url for s in {'/opinions/', '/style/', '/interactive/'}):
                continue


            if self.verbose:
                print(href)
                print(headline.text)

            articles[href_url] = {
                'rank': rank,
                'href': href,
                'headline': headline.text,

                # Store original HTML tags
                'html': {
                    'a': str(first_link),  # mostly for compatibility, but CNN's structure is differenty
                    'headline': str(headline)
                }
            }
            rank += 1

        return articles

    def scrape_article(self, url, timestamp, retry=0, max_retry=5):
        html, archive = self.get_wayback_url(url, timestamp)
        asoup = BeautifulSoup(html, 'html.parser')

        if 'live-news' in url:
            # Find the headlines
            headline = asoup.find('h1')
            headline = headline.get_text()
            if self.verbose:
                print("Headline: " + headline)

            # Find the bodies, sub headlines, and quotes
            body = asoup.find('article')
            paragraphs = [section.text for section in body.find_all(['p', 'blockquote', 'h2'])]
        else:
            # Find the headline
            headline = asoup.find('h1', {'class': 'pg-headline'})
            try:
                headline = headline.get_text()
            except AttributeError as e:
                if retry > max_retry:
                    if self.verbose:
                        print("This article is broken. It's probably a special piece that isn't marked properly, "
                              "or isn't on the blacklist. Skipping...")
                    return None
                if self.verbose:
                    print("Didn't find any text, reloading the page...")
                sleep(5 + random.random())
                return self.scrape_article(url, timestamp, retry=retry+1, max_retry=max_retry)
            if self.verbose:
                print("Headline: " + headline)

            # Find the Body
            body = asoup.find('article')
            paragraphs = [section.text for section in body.find_all(['p', 'blockquote'])]
            if paragraphs[0].lower().startswith('opinion'):
                return None

        article_scrape = {
            'html': html,
            'title': headline,
            'paragraphs': paragraphs[1:],
            'archive_time': datetime.datetime.now() if archive is None else archive.timestamp,
        }

        return article_scrape

    def get_page(self, url):

        foxoptions = webdriver.FirefoxOptions()
        if self.headless:
            foxoptions.headless = True

        seldriver = webdriver.Firefox(options=foxoptions)
        while True:
            try:
                seldriver.get(url)
                break
            except WebDriverException:
                sleep(32)
        wait = WebDriverWait(seldriver, 60)  # Boosting this again since I had a timeout that didn't reproduce.
        # This is a terrible solution, but the selenium driver needs to behave differently on articles
        # and the front page...
        if url == self.front_page_url:
            wait.until(ec.presence_of_element_located((By.CLASS_NAME, 'link-banner')))
        else:
            wait.until(ec.presence_of_element_located((By.TAG_NAME, 'article')))

        front_page = seldriver.page_source
        seldriver.close()
        seldriver.quit()
        return front_page

    # We have to overload the get_wayback_url() function because CNN has some crazy long-loading BS that means that
    # simple requests just return a blank page.
    def get_wayback_url(self, url, timestamp,
                        max_retries=10, max_backoff=32, date_retry=0 # seconds
                        ):

        # I'm trying out something to reduce the load on Archive.org by scraping CNN's archived version of the
        # article first.
        if url != self.front_page_url:
            return self.get_page(url), None

        # First part is yanked directly from Jared's base code.
        wb = waybackpy.Url(url, self.user_agent)

        num_retries = 1
        while True:
            try:
                archive_near = wb.near(unix_timestamp=timestamp.timestamp())
                break
            except WaybackError as e:
                print(
                    'Failed retry %d / %d with timestamp' % (num_retries, max_retries),
                    timestamp,
                    timestamp.timestamp()
                )
                if num_retries < max_retries:
                    # print(e)
                    random_number_milliseconds = random.random()
                    wait_time = min(
                        (2 ** num_retries) + random_number_milliseconds,
                        max_backoff
                    )
                    print('Waiting %d seconds...' % wait_time)
                    sleep(wait_time)
                    num_retries += 1
                else:
                    raise e

        # Okay, now instead of relying on waybackpy's api, we're going to open up a selenium window.
        # Normally best practice is to boot up the driver in the __init__ function, but I think since we
        # want the CNN scraper to _feel_ the same as the others, I think it should just boot up a headless
        # one, get html, and close it as quickly as possible.

        front_page = self.get_page(archive_near.archive_url)

        return front_page, archive_near


# Testing script on our many days

if __name__ == '__main__':
    import pandas as pd
    from collections import defaultdict
    import pytz
    import datetime as dt
    scraper = CNNScraper(verbose=True)
    sampled_days_fp = '../../analysis/production_run/sampled_days_36.tsv'
    sampled_days = pd.read_csv(sampled_days_fp, sep='\t', index_col=0)
    article_dataset = defaultdict(dict)

    # %%

    init_scrape_hour = 18
    respect = 30
    est_timezone = pytz.timezone("US/Eastern")

    start_idx = 10
    for idx, date_str in enumerate(sampled_days['date'][start_idx:]):
        date = dt.datetime.strptime(date_str, '%Y-%m-%d')
        date += dt.timedelta(hours=init_scrape_hour)
        date = est_timezone.localize(date)

        print(start_idx + idx, date)

        articles = scraper.extract(date)

        publisher = scraper.front_page_url
        article_dataset[publisher][date] = articles
        print(f"Day {idx} successfully scraped, waiting {respect} (-ish) seconds before continuing...")
        sleep(respect - 3 + random.random()*6)