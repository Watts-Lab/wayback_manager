import configparser
import os
import scrapers
from misc import scraper_lookup

HERE = os.path.dirname(__file__)
config = configparser.ConfigParser()
config.read(os.path.join(HERE, 'config.ini'))

if __name__ == '__main__':
    thing = scraper_lookup('NYTimes')()
    print(str(thing))
