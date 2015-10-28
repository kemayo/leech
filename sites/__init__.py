
from bs4 import BeautifulSoup

_sites = []

class Site:
    """A Site handles checking whether a URL might represent a site, and then
    extracting the content of a story from said site.
    """
    def __init__(self, fetch):
        super().__init__()
        self.fetch = fetch

    @staticmethod
    def matches(url):
        raise NotImplementedError()

    def extract(self, url):
        raise NotImplementedError()

    def _soup(self, url, method='html5lib'):
        page = self.fetch(url)
        if not page:
            raise SiteException("Couldn't fetch", url)
        return BeautifulSoup(page, method)

class SiteException(Exception):
    pass

def register(site_class):
    _sites.append(site_class)
    return site_class

def get(url):
    for site_class in _sites:
        if site_class.matches(url):
            return site_class

# And now, the things that will use this:
from . import xenforo, fanfictionnet, deviantart, stash
