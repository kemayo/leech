#!/usr/bin/env python

import argparse
import importlib
import os
import json

import sites
import epub
import cover
from fetch import Fetch

fetch = Fetch("leech")

html_template = '''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
    <title>{title}</title>
    <link rel="stylesheet" type="text/css" href="Styles/base.css" />
</head>
<body>
<h1>{title}</h1>
{text}
</body>
</html>
'''

cover_template = '''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>Cover</title>
    <link rel="stylesheet" type="text/css" href="Styles/base.css" />
</head>
<body>
<div class="cover">
<svg version="1.1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
  width="100%" height="100%" viewBox="0 0 573 800" preserveAspectRatio="xMidYMid meet">
<image width="600" height="800" xlink:href="images/cover.png" />
</svg>
</div>
</body>
</html>
'''


def leech(url, filename=None, cache=True, args=None):
    # we have: a page, which could be absolutely any part of a story, or not a story at all
    # check a bunch of things which are completely ff.n specific, to get text from it
    site = sites.get(url)
    if not site:
        raise Exception("No site handler found")

    handler = site(fetch, cache=cache, args=args)

    with open('leech.json') as store_file:
        store = json.load(store_file)
        login = store.get('logins', {}).get(site.__name__, False)
        if login:
            handler.login(login)

    story = handler.extract(url)
    if not story:
        raise Exception("Couldn't extract story")

    dates = [c[2] for c in story['chapters'] if c[2]]
    metadata = {
        'title': story['title'],
        'author': story['author'],
        'unique_id': url,
        'started': min(dates),
        'updated': max(dates),
    }
    html = [('Cover', 'cover.html', cover_template)]
    for i, chapter in enumerate(story['chapters']):
        html.append((chapter[0], 'chapter%d.html' % (i + 1), html_template.format(title=chapter[0], text=chapter[1])))

    if 'footnotes' in story and story['footnotes']:
        html.append(("Footnotes", 'footnotes.html', html_template.format(title="Footnotes", text=story['footnotes'])))

    css = ('Styles/base.css', fetch('https://raw.githubusercontent.com/mattharrison/epub-css-starter-kit/master/css/base.css'), 'text/css')
    cover_image = ('images/cover.png', cover.make_cover(story['title'], story['author']).read(), 'image/png')

    filename = filename or story['title'] + '.epub'

    filename = epub.make_epub(filename, html, metadata, extra_files=(css, cover_image))

    return filename

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('url', help="url of a story to fetch")
    parser.add_argument('--filename', help="output filename (the title is used if this isn't provided)")
    parser.add_argument('--no-cache', dest='cache', action='store_false')
    parser.set_defaults(cache=True)
    args, extra_args = parser.parse_known_args()

    filename = leech(args.url, filename=args.filename, cache=args.cache, args=extra_args)
    print("File created:", filename)
