
import click
import glob
import os
import random
import uuid
import time
import logging
import urllib
import attr
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
_sites = []


def _default_uuid_string(self):
    rd = random.Random(x=self.url)
    return str(uuid.UUID(int=rd.getrandbits(8*16), version=4))


@attr.s
class Chapter:
    title = attr.ib()
    contents = attr.ib()
    date = attr.ib(default=False)


@attr.s
class Section:
    title = attr.ib()
    author = attr.ib()
    url = attr.ib()
    cover_url = attr.ib(default='')
    id = attr.ib(default=attr.Factory(_default_uuid_string, takes_self=True), converter=str)
    contents = attr.ib(default=attr.Factory(list))
    footnotes = attr.ib(default=attr.Factory(list))
    tags = attr.ib(default=attr.Factory(list))
    summary = attr.ib(default='')

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
    footnotes = attr.ib(factory=list, init=False)
    options = attr.ib(default=attr.Factory(
        lambda site: site.get_default_options(),
        True
    ))

    @classmethod
    def site_key(cls):
        if hasattr(cls, '_key'):
            return cls._key
        return cls.__name__

    @staticmethod
    def get_site_specific_option_defs():
        """Returns a list of click.option objects to add to CLI commands.

        It is best practice to ensure that these names are reasonably unique
        to ensure that they do not conflict with the core options, or other
        sites' options. It is OK for different site's options to have the
        same name, but pains should be taken to ensure they remain semantically
        similar in meaning.
        """
        return []

    @classmethod
    def get_default_options(cls):
        options = {}
        for option in cls.get_site_specific_option_defs():
            options[option.name] = option.default
        return options

    @classmethod
    def interpret_site_specific_options(cls, **kwargs):
        """Returns options summarizing CLI flags provided.

        Only includes entries the user has explicitly provided as flags
        / will not contain default values. For that, use get_default_options().
        """
        options = {}
        for option in cls.get_site_specific_option_defs():
            option_value = kwargs[option.name]
            if option_value is not None:
                options[option.name] = option_value
        return options

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

    def _soup(self, url, method='html5lib', delay=0, retry=3, retry_delay=10, **kw):
        page = self.session.get(url, **kw)
        if not page:
            if page.status_code == 403 and page.headers.get('Server', False) == 'cloudflare' and "captcha-bypass" in page.text:
                raise CloudflareException("Couldn't fetch, probably because of Cloudflare protection", url)
            if retry and retry > 0:
                real_delay = retry_delay
                if 'Retry-After' in page.headers:
                    real_delay = int(page.headers['Retry-After'])
                logger.warning("Load failed: waiting %s to retry (%s: %s)", real_delay, page.status_code, page.url)
                time.sleep(real_delay)
                return self._soup(url, method=method, retry=retry - 1, retry_delay=retry_delay, **kw)
            raise SiteException("Couldn't fetch", url)
        if delay and delay > 0 and not page.from_cache:
            time.sleep(delay)
        return BeautifulSoup(page.text, method)

    def _new_tag(self, *args, **kw):
        soup = BeautifulSoup("", 'html5lib')
        return soup.new_tag(*args, **kw)

    def _join_url(self, *args, **kwargs):
        return urllib.parse.urljoin(*args, **kwargs)

    def _footnote(self, contents, chapterid):
        """Register a footnote and return a link to that footnote"""

        # TODO: This embeds knowledge of what the generated filenames will be. Work out a better way.

        idx = len(self.footnotes) + 1

        # epub spec footnotes are all about epub:type on the footnote and the link
        # http://www.idpf.org/accessibility/guidelines/content/semantics/epub-type.php
        contents.name = 'div'
        contents.attrs['id'] = f'footnote{idx}'
        contents.attrs['epub:type'] = 'rearnote'

        # a backlink is essential for Kindle to think of this as a footnote
        # otherwise it doesn't get the inline-popup treatment
        # http://kindlegen.s3.amazonaws.com/AmazonKindlePublishingGuidelines.pdf
        # section 3.9.10
        backlink = self._new_tag('a', href=f'chapter{chapterid}.html#noteback{idx}')
        backlink.string = '^'
        contents.insert(0, backlink)

        self.footnotes.append(contents.prettify())

        # now build the link to the footnote to return, with appropriate
        # epub annotations.
        spoiler_link = self._new_tag('a')
        spoiler_link.attrs = {
            'id': f'noteback{idx}',
            'href': f'footnotes.html#footnote{idx}',
            'epub:type': 'noteref',
        }
        spoiler_link.string = str(idx)

        return spoiler_link

    def _clean(self, contents):
        """Clean up story content to be more ebook-friendly

        TODO: this expects a soup as its argument, so the couple of API-driven sites can't use it as-is
        """
        # Cloudflare is used on many sites, and mangles things that look like email addresses
        # e.g. Point_Me_@_The_Sky becomes
        # <a href="/cdn-cgi/l/email-protection" class="__cf_email__" data-cfemail="85d5eaecebf1dac8e0dac5">[email&#160;protected]</a>_The_Sky
        for a in contents.find_all('a', class_='__cf_email__', href='/cdn-cgi/l/email-protection'):
            # See: https://usamaejaz.com/cloudflare-email-decoding/
            enc = bytes.fromhex(a['data-cfemail'])
            email = bytes([c ^ enc[0] for c in enc[1:]]).decode('utf8')
            a.insert_before(email)
            a.decompose()
        return contents


@attr.s(hash=True)
class SiteSpecificOption:
    """Represents a site-specific option that can be configured.

    Will be added to the CLI as a click.option -- many of these
    fields correspond to click.option arguments."""
    name = attr.ib()
    flag_pattern = attr.ib()
    type = attr.ib(default=None)
    help = attr.ib(default=None)
    default = attr.ib(default=None)

    def as_click_option(self):
        return click.option(
            str(self.name),
            str(self.flag_pattern),
            type=self.type,
            # Note: This default not matching self.default is intentional.
            # It ensures that we know if a flag was explicitly provided,
            # which keeps it from overriding options set in leech.json etc.
            # Instead, default is used in site_cls.get_default_options()
            default=None,
            help=self.help if self.help is not None else ""
        )


class SiteException(Exception):
    pass


class CloudflareException(SiteException):
    pass


def register(site_class):
    _sites.append(site_class)
    return site_class


def get(url):
    for site_class in _sites:
        match = site_class.matches(url)
        if match:
            logger.info("Handler: %s (%s)", site_class, match)
            return site_class, match
    raise NotImplementedError("Could not find a handler for " + url)


def list_site_specific_options():
    """Returns a list of all site's click options, which will be presented to the user."""

    # Ensures that duplicate options are not added twice.
    # Especially important for subclassed sites (e.g. Xenforo sites)
    options = set()

    for site_class in _sites:
        options.update(site_class.get_site_specific_option_defs())
    return [option.as_click_option() for option in options]


# And now, a particularly hacky take on a plugin system:
# Make an __all__ out of all the python files in this directory that don't start
# with __. Then import * them.

modules = glob.glob(os.path.join(os.path.dirname(__file__), "*.py"))
__all__ = [os.path.basename(f)[:-3] for f in modules if not f.startswith("__")]

from . import *  # noqa
