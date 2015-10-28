#!/usr/bin/env python

import argparse
import importlib
import os
import json

import sites
import epub
from fetch import Fetch

fetch = Fetch("leech")

html_template = '''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>{title}</title>
</head>
<body>
<h1>{title}</h1>
{text}
</body>
</html>
'''


def leech(url, filename=None, cache=True):
    # we have: a page, which could be absolutely any part of a story, or not a story at all
    # check a bunch of things which are completely ff.n specific, to get text from it
    site = sites.get(url)
    if not site:
        raise Exception("No site handler found")

    handler = site(fetch, cache=cache)

    with open('leech.json') as store_file:
        store = json.load(store_file)
        login = store.get('logins', {}).get(site.__name__, False)
        if login:
            handler.login(login)

    story = handler.extract(url)
    if not story:
        raise Exception("Couldn't extract story")

    metadata = {
        'title': story['title'],
        'author': story['author'],
        'unique_id': url,
    }
    html = []
    for i, chapter in enumerate(story['chapters']):
        html.append((chapter[0], 'chapter%d.html' % (i + 1), html_template.format(title=chapter[0], text=chapter[1])))

    filename = filename or story['title'] + '.epub'

    filename = epub.make_epub(filename, html, metadata)

    return filename

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('url', help="url of a story to fetch")
    parser.add_argument('--filename', help="output filename (the title is used if this isn't provided)")
    parser.add_argument('--no-cache', dest='cache', action='store_false')
    parser.set_defaults(cache=True)
    args = parser.parse_args()

    filename = leech(args.url, filename=args.filename, cache=args.cache)
    print("File created:", filename)
