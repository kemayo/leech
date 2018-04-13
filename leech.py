#!/usr/bin/env python3

import click
import http.cookiejar
import json
import logging
import requests
import requests_cache
import sqlite3
from click_default_group import DefaultGroup

import sites
import ebook

__version__ = 2
USER_AGENT = 'Leech/%s +http://davidlynch.org' % __version__

logger = logging.getLogger(__name__)

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
        session = requests_cache.CachedSession('leech', expire_after=4 * 3600)
    else:
        session = requests.Session()

    lwp_cookiejar = http.cookiejar.LWPCookieJar()
    try:
        lwp_cookiejar.load('leech.cookies', ignore_discard=True)
    except Exception as e:
        pass
    session.cookies = lwp_cookiejar
    session.headers.update({
        'User-agent': USER_AGENT
    })
    return session

def open_story(url, session, site_options):
    site, url = sites.get(url)

    if not site:
        raise Exception("No site handler found")

    logger.info("Handler: %s (%s)", site, url)

    default_site_options = site.get_default_options()

    with open('leech.json') as store_file:
        store = json.load(store_file)
        login = store.get('logins', {}).get(site.__name__, False)
        configured_site_options = store.get('site_options', {}).get(site.__name__, {})

    overridden_site_options = json.loads(site_options)

    # The final options dictionary is computed by layering the default, configured,
    # and overridden options together in that order.
    options = dict(
        list(default_site_options.items()) +
        list(configured_site_options.items()) +
        list(overridden_site_options.items())
    )

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

@click.group(cls=DefaultGroup, default='download', default_if_no_args=True)
def cli():
    """Top level click group. Uses click-default-group to preserve most behavior from leech v1."""
    pass


@cli.command()
@click.option('--verbose', '-v', is_flag=True, help="verbose output")
def flush(verbose):
    """Flushes the contents of the cache."""
    configure_logging(verbose)
    requests_cache.install_cache('leech')
    requests_cache.clear()

    conn = sqlite3.connect('leech.sqlite')
    conn.execute("VACUUM")
    conn.close()

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
def download(url, site_options, cache, verbose):
    """Downloads a story and saves it on disk as a ebpub ebook."""
    configure_logging(verbose)
    session = create_session(cache)
    story = open_story(url, session, site_options)
    filename = ebook.generate_epub(story)
    logger.info("File created: " + filename)


if __name__ == '__main__':
    cli()
