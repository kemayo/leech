
import glob
import os
import argparse
import collections
from bs4 import BeautifulSoup

_sites = []


Chapter = collections.namedtuple('Chapter', ['title', 'contents', 'date'])


class Site:
    """A Site handles checking whether a URL might represent a site, and then
    extracting the content of a story from said site.
    """
    def __init__(self, session, args=None):
        super().__init__()
        self.session = session
        self.footnotes = []
        self.options = self._parse_args(args)

    @staticmethod
    def matches(url):
        raise NotImplementedError()

    def extract(self, url):
        """Download a story from a given URL

        Args:
            url (string): A valid URL for this Site
        Returns:
            story (dict) containing keys:
                title (string)
                author (string)
                chapters (list): list of Chapters (namedtuple, defined above)
        """
        raise NotImplementedError()

    def login(self, login_details):
        raise NotImplementedError()

    def _parse_args(self, args):
        parser = argparse.ArgumentParser()
        self._add_arguments(parser)
        return parser.parse_args(args)

    def _add_arguments(self, parser):
        pass

    def _soup(self, url, method='html5lib', **kw):
        page = self.session.get(url, **kw)
        if not page:
            raise SiteException("Couldn't fetch", url)
        return BeautifulSoup(page.text, method)

    def _new_tag(self, *args, **kw):
        soup = BeautifulSoup("", 'html5lib')
        return soup.new_tag(*args, **kw)

    def _footnote(self, contents, backlink_href=''):
        """Register a footnote and return a link to that footnote"""

        idx = len(self.footnotes) + 1

        # epub spec footnotes are all about epub:type on the footnote and the link
        # http://www.idpf.org/accessibility/guidelines/content/semantics/epub-type.php
        contents.name = 'div'
        contents.attrs['id'] = "footnote%d" % idx
        contents.attrs['epub:type'] = 'rearnote'

        # a backlink is essential for Kindle to think of this as a footnote
        # otherwise it doesn't get the inline-popup treatment
        # http://kindlegen.s3.amazonaws.com/AmazonKindlePublishingGuidelines.pdf
        # section 3.9.10
        backlink = self._new_tag('a', href="%s#noteback%d" % (backlink_href, idx))
        backlink.string = '^'
        contents.insert(0, backlink)

        self.footnotes.append(contents.prettify())

        # now build the link to the footnote to return, with appropriate
        # epub annotations.
        spoiler_link = self._new_tag('a')
        spoiler_link.attrs = {
            'id': 'noteback%d' % idx,
            'href': "footnotes.html#footnote%d" % idx,
            'epub:type': 'noteref',
        }
        spoiler_link.string = str(idx)

        return spoiler_link


class SiteException(Exception):
    pass


def register(site_class):
    _sites.append(site_class)
    return site_class


def get(url):
    for site_class in _sites:
        if site_class.matches(url):
            return site_class


# And now, a particularly hacky take on a plugin system:
# Make an __all__ out of all the python files in this directory that don't start
# with __. Then import * them.

modules = glob.glob(os.path.join(os.path.dirname(__file__), "*.py"))
__all__ = [os.path.basename(f)[:-3] for f in modules if not f.startswith("__")]

from . import *  # noqa
