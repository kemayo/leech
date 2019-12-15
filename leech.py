#!/usr/bin/env python3

import click
import http.cookiejar
import json
import logging
import os.path
import requests
import requests_cache
from appdirs import AppDirs
from click_default_group import DefaultGroup
from functools import reduce
from pathlib import Path

import sites
import ebook

__version__ = 2
USER_AGENT = 'Leech/%s +http://davidlynch.org' % __version__

logger = logging.getLogger(__name__)


class AppFilenames:
    def __init__(self):
        self._dirs = AppDirs(appname='leech', appauthor="davidlynch.org")

    @property
    def cookies(self):
        return os.path.join(self._dirs.user_cache_dir, 'leech.cookies')

    @property
    def options(self):
        return os.path.join(self._dirs.user_config_dir, 'leech.json')

    @property
    def cache(self):
        return os.path.join(self._dirs.user_cache_dir, 'request_cache')

    def ensure_cache_directory_exists(self):
        self._ensure_directory(self._dirs.user_cache_dir)

    def _ensure_directory(self, dirname):
        path = Path(dirname)
        if not path.exists():
            path.mkdir(mode=0o700, parents=True)
        assert path.is_dir(), f"expected {path} to be a directory!"


_appFilenames = AppFilenames()


def configure_logging(verbose):
    if verbose:
        logging.basicConfig(
            level=logging.DEBUG,
            format="[%(name)s @ %(levelname)s] %(message)s"
        )
    else:
        logging.basicConfig(
            level=logging.INFO,
            format="[%(name)s] %(message)s"
        )


def create_session(cache):
    if cache:
        _appFilenames.ensure_cache_directory_exists()
        try:
            # Extra logging if this fails, since the sqlite exception isn't good about
            # showing what it's trying to access.
            session = requests_cache.CachedSession(_appFilenames.cache, expire_after=4 * 3600)
        except Exception:
            logger.error("failed to create request cache at %s", _appFilenames.cache)
            raise
    else:
        session = requests.Session()

    lwp_cookiejar = http.cookiejar.LWPCookieJar()
    try:
        lwp_cookiejar.load(_appFilenames.cookies, ignore_discard=True)
    except FileNotFoundError:
        # This file is very much optional, so this log isn't really necessary
        # logging.exception("Couldn't load cookies from leech.cookies")
        pass
    session.cookies = lwp_cookiejar
    session.headers.update({
        'User-agent': USER_AGENT
    })
    return session


def load_on_disk_options(site):
    try:
        with open(_appFilenames.options) as store_file:
            store = json.load(store_file)
    except FileNotFoundError:
        logger.info("Unable to locate %s. Continuing assuming it does not exist.", _appFilenames.options)
        login = False
        configured_site_options = {}
        cover_options = {}
    else:
        login = store.get('logins', {}).get(site.site_key(), False)
        configured_site_options = store.get('site_options', {}).get(site.site_key(), {})
        cover_options = store.get('cover', {})

    return configured_site_options, login, cover_options


def create_options(site, site_options, unused_flags):
    """Compiles options provided from multiple different sources
    (e.g. on disk, via flags, via defaults, via JSON provided as a flag value)
    into a single options object."""
    default_site_options = site.get_default_options()

    flag_specified_site_options = site.interpret_site_specific_options(**unused_flags)

    configured_site_options, login, cover_options = load_on_disk_options(site)

    overridden_site_options = json.loads(site_options)

    # The final options dictionary is computed by layering the default, configured,
    # and overridden, and flag-specified options together in that order.
    options = dict(
        list(default_site_options.items()) +
        list(configured_site_options.items()) +
        list(overridden_site_options.items()) +
        list(flag_specified_site_options.items()) +
        list(cover_options.items())
    )
    return options, login


def open_story(site, url, session, login, options):
    handler = site(
        session,
        options=options
    )

    if login:
        handler.login(login)

    story = handler.extract(url)
    if not story:
        raise Exception("Couldn't extract story")
    return story


def site_specific_options(f):
    option_list = sites.list_site_specific_options()
    return reduce(lambda cmd, decorator: decorator(cmd), [f] + option_list)


@click.group(cls=DefaultGroup, default='download', default_if_no_args=True)
def cli():
    """Top level click group. Uses click-default-group to preserve most behavior from leech v1."""
    pass


@cli.command()
@click.option('--verbose', '-v', is_flag=True, help="verbose output")
def flush(verbose):
    """Flushes the contents of the cache."""
    configure_logging(verbose)
    cached_session = create_session(cache=True)
    cached_session.cache.clear()

    logger.info("Flushed cache")


@cli.command()
@click.argument('url')
@click.option(
    '--site-options',
    default='{}',
    help='JSON object encoding any site specific option.'
)
@click.option('--cache/--no-cache', default=True)
@click.option('--verbose', '-v', is_flag=True, help="Verbose debugging output")
@site_specific_options  # Includes other click.options specific to sites
def download(url, site_options, cache, verbose, **other_flags):
    """Downloads a story and saves it on disk as a ebpub ebook."""
    configure_logging(verbose)
    session = create_session(cache)

    site, url = sites.get(url)
    options, login = create_options(site, site_options, other_flags)
    story = open_story(site, url, session, login, options)

    filename = ebook.generate_epub(story, options)
    logger.info("File created: " + filename)


if __name__ == '__main__':
    cli()
