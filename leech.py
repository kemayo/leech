#!/usr/bin/env python

import argparse
import sys
import json
import datetime
import http.cookiejar
import collections

import sites
import epub
import cover

import requests
import requests_cache

__version__ = 1
USER_AGENT = 'Leech/%s +http://davidlynch.org' % __version__

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

frontmatter_template = '''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>Front Matter</title>
    <link rel="stylesheet" type="text/css" href="Styles/base.css" />
</head>
<body>
<div class="cover title">
    <h1>{title}<br />By {author}</h1>
    <dl>
        <dt>Source</dt>
        <dd>{unique_id}</dd>
        <dt>Started</dt>
        <dd>{started:%Y-%m-%d}</dd>
        <dt>Updated</dt>
        <dd>{updated:%Y-%m-%d}</dd>
        <dt>Downloaded on</dt>
        <dd>{now:%Y-%m-%d}</dd>
    </dl>
</div>
</body>
</html>
'''


def leech(url, session, filename=None, args=None):
    # we have: a page, which could be absolutely any part of a story, or not a story at all
    # check a bunch of things which are completely ff.n specific, to get text from it
    site = sites.get(url)
    if not site:
        raise Exception("No site handler found")

    handler = site(session, args=args)

    with open('leech.json') as store_file:
        store = json.load(store_file)
        login = store.get('logins', {}).get(site.__name__, False)
        if login:
            handler.login(login)

    story = handler.extract(url)
    if not story:
        raise Exception("Couldn't extract story")

    dates = list(story.dates())
    metadata = {
        'title': story.title,
        'author': story.author,
        'unique_id': url,
        'started': min(dates),
        'updated': max(dates),
    }

    # The cover is static, and the only change comes from the image which we generate
    html = [('Cover', 'cover.html', cover_template)]
    cover_image = ('images/cover.png', cover.make_cover(story.title, story.author).read(), 'image/png')

    html.append(('Front Matter', 'frontmatter.html', frontmatter_template.format(now=datetime.datetime.now(), **metadata)))

    html.extend(chapter_html(story))

    css = ('Styles/base.css', session.get('https://raw.githubusercontent.com/mattharrison/epub-css-starter-kit/master/css/base.css').text, 'text/css')

    filename = filename or story.title + '.epub'

    # print([c[0:-1] for c in html])
    filename = epub.make_epub(filename, html, metadata, extra_files=(css, cover_image))

    return filename


def chapter_html(story, titleprefix=None):
    chapters = []
    for i, chapter in enumerate(story):
        if hasattr(chapter, '__iter__'):
            # This is a Section
            chapters.extend(chapter_html(chapter, titleprefix=chapter.title))
        else:
            title = titleprefix and '{}: {}'.format(titleprefix, chapter.title) or chapter.title
            chapters.append((
                title,
                '{}/chapter{}.html'.format(story.id, i + 1),
                html_template.format(title=title, text=chapter.contents)
            ))
    if story.footnotes:
        chapters.append(("Footnotes", '{}/footnotes.html'.format(story.id), html_template.format(title="Footnotes", text='\n\n'.join(story.footnotes))))
    return chapters


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
