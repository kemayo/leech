#!/usr/bin/python

import re
from bs4 import BeautifulSoup

def match(url):
    ## e.g. https://www.fanfiction.net/s/4109686/3/Taking-Sights
    return re.match(r'^https?://www\.fanfiction\.net/s/\d+/?.*', url)

def extract(url, fetch):
    page = fetch(url)
    soup = BeautifulSoup(page, 'html5lib')
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
            chapters.append(_extract_chapter(base_url + option[0], option[1], fetch))
    else:
        chapters.append(_extract_chapter(url, story['title'], fetch))

    story['chapters'] = chapters

    return story

def _extract_chapter(url, title, fetch):
    print("Extracting chapter from", url)
    page = fetch(url)
    soup = BeautifulSoup(page, 'html5lib')

    content = soup.find(id="content_wrapper_inner")
    if not content:
        return

    text = content.find(id="storytext")

    # clean up some invalid xhtml attributes
    # TODO: be more selective about this somehow
    try:
        for tag in text.find_all(True):
            tag.attrs = None
    except Exception as e:
        print("Trouble cleaning attributes", e)

    return (title, text.prettify())
