
from bs4 import BeautifulSoup

_sites = []

class Site:
    """A Site handles checking whether a URL might represent a site, and then
    extracting the content of a story from said site.
    """
    def __init__(self, fetch, cache=True):
        super().__init__()
        self.fetch = fetch
        self.cache = cache

    @staticmethod
    def matches(url):
        raise NotImplementedError()

    def extract(self, url):
        raise NotImplementedError()

    def login(self, login_details):
        raise NotImplementedError()

    def _soup(self, url, method='html5lib', **kw):
        page = self.fetch(url, cached=self.cache, **kw)
        if not page:
            raise SiteException("Couldn't fetch", url)
        return BeautifulSoup(page, method)

    def _new_tag(self, *args, **kw):
        soup = BeautifulSoup("", 'html5lib')
        return soup.new_tag(*args, **kw)

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
