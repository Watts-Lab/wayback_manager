"""Random functions that don't belong anywhere else"""
from configparser import ParsingError
import scrapers
import sys


def flag(s):
    if s.lower() in {'on', 'true', 'yes', '1'}:
        return True
    elif s.lower() in {'off', 'false', 'no', '0'}:
        return False
    else:
        raise ParsingError(f"{s} is not a valid flag for boolean parameters.")


def scraper_lookup(s):
    return getattr(sys.modules['scrapers'], s)
