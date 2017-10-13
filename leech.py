#!/usr/bin/env python3

import click
from click_default_group import DefaultGroup

import requests
import requests_cache
import http.cookiejar
import json

import sites
import ebook

__version__ = 2
USER_AGENT = 'Leech/%s +http://davidlynch.org' % __version__


def uses_session(command):
    """Decorator for click commands that need a session."""
    @click.option('--cache/--no-cache', default=True)
    def wrapper(cache, **kwargs):
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
        return command(session=session, **kwargs)
    wrapper.__name__ = command.__name__
    return wrapper


def uses_story(command):
    """Decorator for click commands that need a story."""
    @click.argument('url')
    @click.option(
        '--site-options',
        default='{}',
        help='JSON object encoding any site specific option.'
    )
    @uses_session
    def wrapper(url, session, site_options, **kwargs):
        site, url = sites.get(url)
        if not site:
            raise Exception("No site handler found")

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

        command(story=story, **kwargs)
    wrapper.__name__ = command.__name__
    return wrapper


@click.group(cls=DefaultGroup, default='download', default_if_no_args=True)
def cli():
    """Top level click group. Uses click-default-group to preserve most behavior from leech v1."""
    pass


@cli.command()
def flush():
    """"Flushes the contents of the cache."""
    requests_cache.install_cache('leech')
    requests_cache.clear()
    print("Flushed cache")


@cli.command()
@uses_story
def download(story):
    """Downloads a story and saves it on disk as a ebpub ebook."""
    filename = ebook.generate_epub(story)
    print("File created:", filename)


if __name__ == '__main__':
    cli()
