#!/usr/bin/python

import re
from bs4 import BeautifulSoup


def match(url):
    # Need a stack page
    return re.match(r'^https?://sta\.sh/2.+/?.*', url)


def extract(url, fetch):
    page = fetch(url)
    soup = BeautifulSoup(page, 'html5lib')
    content = soup.find(id="stash-body")
    if not content:
        return

    story = {}
    chapters = []

    # metadata = content.find(id='profile_top')
    story['title'] = str(soup.find(class_="stash-folder-name").h2.string)
    story['author'] = str(soup.find('span', class_="oh-stashlogo-name").string).rstrip("'s")

    thumbs = content.select(".stash-folder-stream .thumb")
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


def _extract_chapter(url, fetch):
    print("Extracting chapter from", url)
    page = fetch(url)
    soup = BeautifulSoup(page, 'html5lib')

    content = soup.find(class_="journal-wrapper")
    if not content:
        raise Exception("No content")

    title = str(content.find(class_="gr-top").find(class_='metadata').h2.a.string)

    text = content.find(class_="text")

    # clean up some invalid xhtml attributes
    # TODO: be more selective about this somehow
    try:
        for tag in text.find_all(True):
            tag.attrs = None
    except Exception as e:
        raise Exception("Trouble cleaning attributes", e)

    return (title, text.prettify())
