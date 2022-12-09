import json
import pickle
import random
import re
import requests
import waybackpy

import datetime as dt

from bs4 import BeautifulSoup
from collections import OrderedDict
from time import sleep
from urllib.parse import urljoin, urlparse
from waybackpy.exceptions import WaybackError



class PublisherScraper:

    def __init__(self, verbose = False):
        self.user_agent = "Mozilla/5.0 (Windows NT 5.1; rv:40.0) Gecko/20100101 Firefox/40.0"
        self.verbose = verbose

    @property
    def front_page_url(self):
        raise NotImplementedError()


    def clean_wayback_url(self, url, remove_params = True):
        """Return a url cleaned with various wayback machine prefix and suffixes"""
        # TODO - this breaks for certain


        if url == 'javascript:void(0);':
            return None

        if self.front_page_url.strip('(https://)|(www\.)|(/us)') not in url:
            # Had to add the US suffix for the guardian ~ Coen
            print('Different domain', url)
            return None

        web_archive = 'https://web.archive.org'

        # 1. first check if link starts with web.archive
        #       if so, remove
        if url.startswith(web_archive):
            url = url[len(web_archive):]

        # Remove anything before the https
        if self.verbose and 'http' not in url:
            print(url)

        href_url = url[url.index('http'):]

        if remove_params:
            url_without_params = urljoin(href_url, urlparse(href_url).path)
            return url_without_params

        return href_url

    def get_wayback_url(
        self, url, timestamp,
        max_retries = 10, max_backoff = 32, # seconds
        date_retry=0
    ):
        wb = waybackpy.Url(url, self.user_agent)

        num_retries = 1
        while True:
            try:
                archive_near = wb.near(unix_timestamp = timestamp.timestamp())
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
                    print(f'Could Not Find article {url}. ERR01')
                    return None, None

        try:
            front_page = requests.get(archive_near.archive_url).text

        except UnicodeDecodeError:  # Our web parser throws this if the wayback machine doesn't have that webpage.
            return None, None

        return front_page, archive_near

    def get_front_page_html(self, timestamp):
        """Return HTML for front page"""
        return self.get_wayback_url(self.front_page_url, timestamp)

    def get_top_article_metadata(self, front_page):
        """Return dictionary with article_url : { metadata } for top articles"""
        raise NotImplementedError()

    def scrape_article(self, url, timestamp):
        """Return scraped body, headline, and metadata for a given article"""
        raise NotImplementedError()

    def extract(self, timestamp):

        front_page, front_archive = self.get_front_page_html(timestamp)
        if self.verbose:
            print('Frontpage Archive url:', front_archive.archive_url)

        articles = self.get_top_article_metadata(front_page)
        a = 0

        for article_url in articles.keys():
            if self.verbose:
                print(article_url)

            article_scrape = self.scrape_article(
                article_url,
                front_archive.timestamp
            )
            if article_scrape is None:
                continue
            a += 1
            articles[article_url]['scrape'] = article_scrape
            if a >= 5:
                break

        # articles['archive_time'] = front_archive.timestamp

        return articles
