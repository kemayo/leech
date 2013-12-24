#!/usr/bin/python

import importlib
import os

import epub
from fetch import Fetch

fetch = Fetch("leech.db")

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

def leech(url):
    # we have: a page, which could be absolutely any part of a story, or not a story at all
    # check a bunch of things which are completely ff.n specific, to get text from it
    site = _get_site(url)
    if not site:
        return

    story = site.extract(url, fetch)

    metadata = {
        'title': story['title'],
        'author': story['author'],
        'unique_id': url,
    }
    html = []
    for i, chapter in enumerate(story['chapters']):
        html.append((chapter[0], 'chapter%d.html' % (i+1), html_template.format(title=chapter[0], text=chapter[1])))

    epub.make_epub(story['title'] + '.epub', html, metadata)

_sites = []

def _get_site(url):
    for site in _sites:
        if site.match(url):
            return site

def _load_sites():
    dirname = os.path.join(os.path.dirname(__file__), 'sites')
    for f in os.listdir(dirname):
        if not f.endswith('.py'):
            continue
        mod = importlib.import_module('sites.' + f.replace('.py', ''))
        _sites.append(mod)


if __name__ == '__main__':
    _load_sites()
    leech('https://www.fanfiction.net/s/4109686/3/Taking-Sights')
    pass
