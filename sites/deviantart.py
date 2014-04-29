#!/usr/bin/python

import re
from bs4 import BeautifulSoup

from .stash import _extract_chapter


def match(url):
    # Need a collection page
    return re.match(r'^https?://[^.]+\.deviantart\.com/(?:gallery|favourites)/\d+/?', url)


def extract(url, fetch):
    page = fetch(url)
    soup = BeautifulSoup(page, 'html5lib')
    content = soup.find(id="output")
    if not content:
        return

    story = {}
    chapters = []

    if "gallery" in url:
        story['author'] = str(content.select('h1 a.u')[0].string)
    else:
        authors = set(str(author.string) for author in content.select('.stream .details a.u'))
        story['author'] = ', '.join(authors)

    story['title'] = str(content.find(class_="folder-title").string)

    thumbs = content.select(".stream a.thumb")
    if not thumbs:
        return
    for thumb in thumbs:
        try:
            if thumb['href'] is not '#':
                chapters.append(_extract_chapter(thumb['href'], fetch))
        except Exception as e:
            print(e)

    story['chapters'] = chapters

    return story
