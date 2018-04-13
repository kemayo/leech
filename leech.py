#!/usr/bin/env python

import argparse
import sys
import json
import http.cookiejar
import logging
import sqlite3

import sites
import ebook

import requests
import requests_cache

__version__ = 1
USER_AGENT = 'Leech/%s +http://davidlynch.org' % __version__

logger = logging.getLogger(__name__)


def leech(url, session, filename=None, args=None):
    # we have: a page, which could be absolutely any part of a story, or not a story at all
    # check a bunch of things which are completely ff.n specific, to get text from it
    site, url = sites.get(url)
    if not site:
        raise Exception("No site handler found")

    logger.info("Handler: %s (%s)", site, url)

    handler = site(session, args=args)

    with open('leech.json') as config_file:
        config = json.load(config_file)

        login = config.get('logins', {}).get(site.__name__, False)
        if login:
            handler.login(login)

        cover_options = config.get('cover', {})

    story = handler.extract(url)
    if not story:
        raise Exception("Couldn't extract story")

    return ebook.generate_epub(story, filename, cover_options=cover_options)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('url', help="url of a story to fetch", nargs='?')
    parser.add_argument('--filename', help="output filename (the title is used if this isn't provided)")
    parser.add_argument('--no-cache', dest='cache', action='store_false')
    parser.add_argument('--flush', dest='flush', action='store_true')
    parser.add_argument('-v', '--verbose', help="verbose output", action='store_true', dest='verbose')
    parser.set_defaults(cache=True, flush=False, verbose=False)
    args, extra_args = parser.parse_known_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(
            level=logging.INFO,
            format="[%(name)s] %(message)s"
        )

    if args.flush:
        requests_cache.install_cache('leech')
        requests_cache.clear()

        conn = sqlite3.connect('leech.sqlite')
        conn.execute("VACUUM")
        conn.close()

        logger.info("Flushed cache")
        sys.exit()

    if not args.url:
        sys.exit("URL is required")

    if args.cache:
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

    filename = leech(args.url, filename=args.filename, session=session, args=extra_args)
    logger.info("File created: %s", filename)
