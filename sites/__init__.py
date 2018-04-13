
import glob
import os
import uuid
import time
import logging
import attr
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
_sites = []


def _default_uuid_string(*args):
    return str(uuid.uuid4())


@attr.s
class Chapter:
    title = attr.ib()
    contents = attr.ib()
    date = attr.ib(default=False)
    id = attr.ib(default=attr.Factory(_default_uuid_string), convert=str)


@attr.s
class Section:
    title = attr.ib()
    author = attr.ib()
    url = attr.ib()
    id = attr.ib(default=attr.Factory(_default_uuid_string), convert=str)
    contents = attr.ib(default=attr.Factory(list))
    footnotes = attr.ib(default=attr.Factory(list))

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


@attr.s
class Site:
    """A Site handles checking whether a URL might represent a site, and then
    extracting the content of a story from said site.
    """
    session = attr.ib()
    footnotes = attr.ib(default=attr.Factory(list), init=False)
    options = attr.ib(default=attr.Factory(
        lambda site: site.get_default_options(),
        True
    ))

    @staticmethod
    def get_default_options():
        return {}

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

    def _soup(self, url, method='html5lib', retry=3, retry_delay=10, **kw):
        page = self.session.get(url, **kw)
        if not page:
            if retry and retry > 0:
                delay = retry_delay
                if 'Retry-After' in page.headers:
                    delay = int(page.headers['Retry-After'])
                logger.warning("Load failed: waiting %s to retry (%s)", delay, page)
                time.sleep(delay)
                return self._soup(url, method=method, retry=retry - 1, retry_delay=retry_delay, **kw)
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
        match = site_class.matches(url)
        if match:
            return site_class, match
    raise NotImplementedError("Could not find a handler for " + url)


# And now, a particularly hacky take on a plugin system:
# Make an __all__ out of all the python files in this directory that don't start
# with __. Then import * them.

modules = glob.glob(os.path.join(os.path.dirname(__file__), "*.py"))
__all__ = [os.path.basename(f)[:-3] for f in modules if not f.startswith("__")]

from . import *  # noqa
