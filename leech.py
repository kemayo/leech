#!/usr/bin/env python

import argparse
import sys
import json
import http.cookiejar

import sites
import ebook

import requests
import requests_cache

__version__ = 1
USER_AGENT = 'Leech/%s +http://davidlynch.org' % __version__


def leech(url, session, filename=None, args=None):
    # we have: a page, which could be absolutely any part of a story, or not a story at all
    # check a bunch of things which are completely ff.n specific, to get text from it
    site, url = sites.get(url)
    if not site:
        raise Exception("No site handler found")

    print("Handler", site, url)

    handler = site(session, args=args)

    with open('leech.json') as store_file:
        store = json.load(store_file)
        login = store.get('logins', {}).get(site.__name__, False)
        if login:
            handler.login(login)

    story = handler.extract(url)
    if not story:
        raise Exception("Couldn't extract story")

    return ebook.generate_epub(story, filename)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('url', help="url of a story to fetch", nargs='?')
    parser.add_argument('--filename', help="output filename (the title is used if this isn't provided)")
    parser.add_argument('--no-cache', dest='cache', action='store_false')
    parser.add_argument('--flush', dest='flush', action='store_true')
    parser.set_defaults(cache=True, flush=False)
    args, extra_args = parser.parse_known_args()

    if args.flush:
        requests_cache.install_cache('leech')
        requests_cache.clear()
        print("Flushed cache")
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
    print("File created:", filename)
