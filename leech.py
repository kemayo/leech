#!/usr/bin/env python3

import click
import http.cookiejar
import json
import logging
import os
import requests
import requests_cache
import sqlite3
from click_default_group import DefaultGroup
from functools import reduce

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
    except Exception:
        # This file is very much optional, so this log isn't really necessary
        # logging.exception("Couldn't load cookies from leech.cookies")
        pass
    session.cookies.update(lwp_cookiejar)
    session.headers.update({
        'User-agent': USER_AGENT
    })
    return session


def load_on_disk_options(site):
    try:
        with open('leech.json') as store_file:
            store = json.load(store_file)
            login = store.get('logins', {}).get(site.site_key(), False)
            image_bool: bool = store.get('images', False)
            image_format: str = store.get('image_format', 'jpeg')
            compress_images: bool = store.get('compress_images', False)
            max_image_size: int = store.get('max_image_size', 1_000_000)
            configured_site_options = store.get('site_options', {}).get(site.site_key(), {})
            cover_options = store.get('cover', {})
            output_dir = store.get('output_dir', False)
    except FileNotFoundError:
        logger.info("Unable to locate leech.json. Continuing assuming it does not exist.")
        login = False
        image_bool = False
        image_format = 'jpeg'
        compress_images = False
        max_image_size = 1_000_000
        configured_site_options = {}
        cover_options = {}
        output_dir = False
    if output_dir and 'output_dir' not in configured_site_options:
        configured_site_options['output_dir'] = output_dir
    return configured_site_options, login, cover_options, image_bool, image_format, compress_images, max_image_size


def create_options(site, site_options, unused_flags):
    """Compiles options provided from multiple different sources
    (e.g. on disk, via flags, via defaults, via JSON provided as a flag value)
    into a single options object."""
    default_site_options = site.get_default_options()

    flag_specified_site_options = site.interpret_site_specific_options(**unused_flags)

    configured_site_options, login, cover_options, image_bool, image_format, compress_images, max_image_size = load_on_disk_options(site)

    overridden_site_options = json.loads(site_options)

    # The final options dictionary is computed by layering the default, configured,
    # and overridden, and flag-specified options together in that order.
    options = dict(
        list(default_site_options.items()) +
        list(configured_site_options.items()) +
        list(overridden_site_options.items()) +
        list(flag_specified_site_options.items()) +
        list(cover_options.items()) +
        list({'image_bool': image_bool, 'image_format': image_format, 'compress_images': compress_images, 'max_image_size': max_image_size }.items())
    )
    return options, login


def open_story(site, url, session, login, options):
    handler = site(
        session,
        options=options
    )

    if login:
        handler.login(login)

    try:
        story = handler.extract(url)
    except sites.SiteException as e:
        logger.error(e.args)
        return
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
    requests_cache.install_cache('leech')
    requests_cache.clear()

    conn = sqlite3.connect('leech.sqlite')
    conn.execute("VACUUM")
    conn.close()

    logger.info("Flushed cache")


@cli.command()
@click.argument('urls', nargs=-1, required=True)
@click.option(
    '--site-options',
    default='{}',
    help='JSON object encoding any site specific option.'
)
@click.option(
    '--output-dir',
    default=None,
    help='Directory to save generated ebooks'
)
@click.option('--cache/--no-cache', default=True)
@click.option('--normalize/--no-normalize', default=True, help="Whether to normalize strange unicode text")
@click.option('--verbose', '-v', is_flag=True, help="Verbose debugging output")
@site_specific_options  # Includes other click.options specific to sites
def download(urls, site_options, cache, verbose, normalize, output_dir, **other_flags):
    """Downloads a story and saves it on disk as an epub ebook."""
    configure_logging(verbose)
    session = create_session(cache)

    for url in urls:
        site, url = sites.get(url)
        options, login = create_options(site, site_options, other_flags)
        story = open_story(site, url, session, login, options)
        if story:
            filename = ebook.generate_epub(
                story, options,
                image_options={
                    'image_bool': options['image_bool'] or False,
                    'image_format': options['image_format'] or 'jpeg',
                    'compress_images': options['compress_images'] or False,
                    'max_image_size': options['max_image_size'] or 1_000_000
                },
                normalize=normalize,
                output_dir=output_dir or options.get('output_dir', os.getcwd())
            )
            logger.info("File created: " + filename)
        else:
            logger.warning("No ebook created")


if __name__ == '__main__':
    cli()
