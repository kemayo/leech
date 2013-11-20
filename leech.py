#!/usr/bin/python

import re
from bs4 import BeautifulSoup

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
    story = _extract(url)

    metadata = {
        'title': story['title'],
        'author': story['author'],
        'unique_id': url,
    }
    html = []
    for i, chapter in enumerate(story['chapters']):
        html.append((chapter[0], 'chapter%d.html' % (i+1), html_template.format(title=chapter[0], text=chapter[1])))

    epub.make_epub(story['title'] + '.epub', html, metadata)

def _extract(url):
    # we have: a page, which could be absolutely any part of a story, or not a story at all
    # check a bunch of things which are completely ff.n specific, to get text from it
    page = fetch(url)
    soup = BeautifulSoup(page)
    content = soup.find(id="content_wrapper_inner")
    if not content:
        return

    story = {}
    chapters = []

    metadata = content.find(id='profile_top')
    story['title'] = str(metadata.find('b', class_="xcontrast_txt").string)
    story['author'] = str(metadata.find('a', class_="xcontrast_txt").string)

    chapter_select = content.find(id="chap_select")
    if chapter_select:
        base_url = re.search(r'(https?://[^/]+/s/\d+/?)', url)
        if not base_url:
            return
        base_url = base_url.group(0)

        # beautiful soup doesn't handle ffn's unclosed option tags at all well here
        options = re.findall(r'<option.+?value="?(\d+)"?[^>]*>([^<]+)', str(chapter_select))
        for option in options:
            chapters.append(_extract_chapter(base_url + option[0], option[1]))
    else:
        chapters.append(_extract_chapter(url, story['title']))

    story['chapters'] = chapters

    return story

def _extract_chapter(url, title):
    page = fetch(url)
    soup = BeautifulSoup(page, 'html5lib')

    content = soup.find(id="content_wrapper_inner")
    if not content:
        return

    text = content.find(id="storytext")

    # clean up some invalid xhtml attributes
    # TODO: be more thorough about this somehow
    for tag in text.find_all('hr'):
        if 'size' in tag.attrs:
            del(tag.attrs['size'])
        if 'noshade' in tag.attrs:
            del(tag.attrs['noshade'])

    return (title, text.prettify())

if __name__ == '__main__':
    leech('https://www.fanfiction.net/s/4510497/1/Neon-Genesis-Evangelion-Redux')
