
import glob
import os
import argparse
import uuid
from bs4 import BeautifulSoup

_sites = []


class Chapter:
    def __init__(self, title, contents, date=False, chapterid=None):
        if not chapterid:
            chapterid = str(uuid.uuid4())
        self.id = chapterid
        self.title = title
        self.contents = contents
        self.date = date


class Section:
    def __init__(self, title, author, sectionid=None):
        if not sectionid:
            sectionid = str(uuid.uuid4())
        self.id = sectionid
        self.title = title
        self.author = author
        # Will contain a mix of Sections and Chapters
        self.contents = []
        self.footnotes = []

    def __iter__(self):
        return self.contents.__iter__()

    def __getitem__(self, index):
        return self.contents.__getitem__(index)

    def __setitem__(self, index, value):
        return self.contents.__setitem__(index, value)

    def __len__(self):
        return len(self.contents)

    def add(self, value, index=None):
        if index is not None:
            self.contents.insert(index, value)
        else:
            self.contents.append(value)

    def dates(self):
        for chapter in self.contents:
            if hasattr(chapter, '__iter__'):
                yield from chapter.dates()
            elif chapter.date:
                yield chapter.date


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

    def _footnote(self, contents, chapterid):
        """Register a footnote and return a link to that footnote"""

        # TODO: This embeds knowledge of what the generated filenames will be. Work out a better way.

        idx = len(self.footnotes) + 1

        # epub spec footnotes are all about epub:type on the footnote and the link
        # http://www.idpf.org/accessibility/guidelines/content/semantics/epub-type.php
        contents.name = 'div'
        contents.attrs['id'] = "footnote{}".format(idx)
        contents.attrs['epub:type'] = 'rearnote'

        # a backlink is essential for Kindle to think of this as a footnote
        # otherwise it doesn't get the inline-popup treatment
        # http://kindlegen.s3.amazonaws.com/AmazonKindlePublishingGuidelines.pdf
        # section 3.9.10
        backlink = self._new_tag('a', href="chapter{}.html#noteback{}".format(chapterid, idx))
        backlink.string = '^'
        contents.insert(0, backlink)

        self.footnotes.append(contents.prettify())

        # now build the link to the footnote to return, with appropriate
        # epub annotations.
        spoiler_link = self._new_tag('a')
        spoiler_link.attrs = {
            'id': 'noteback{}'.format(idx),
            'href': "footnotes.html#footnote{}".format(idx),
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
