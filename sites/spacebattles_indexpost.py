#!/usr/bin/python

import re
from bs4 import BeautifulSoup


def match(url):
    return re.match(r'^https?://forums.spacebattles.com/posts/\d+/?.*', url)

def extract(url, fetch):
    page = fetch(url)
    soup = BeautifulSoup(page, 'html5lib')

    base = soup.head.base.get('href')

    match = re.match(r'.+/posts/(\d+)/?', url)
    if not match:
        print("Unparseable post URL", url)
        return
    postid = match.group(1)

    story = {}
    story['title'] = str(soup.find('h1').string)
    story['author'] = str(soup.find('p', id='pageDescription').find('a', class_='username').string)

    post = post = soup.find('li', id='post-'+postid)
    links = post.find('blockquote', class_='messageText').find_all('a', class_='internalLink')
    if not links:
        print("No links in index?")

    chapters = []
    for link in links:
        href = link.get('href')
        if '/members/' in href:
            # skip links to users
            continue
        if not href.startswith('http'):
            href = base + href
        print("Extracting chapter from", href)
        match = re.match(r'.+#post-(\d+)$', href)
        if not match:
            match = re.match(r'.+/posts/(\d+)/?$', href)
            if not match:
                print("Unparseable index link href", href)
        chapter_postid = match and match.group(1)
        chapter_page = fetch(href)
        chapter_soup = BeautifulSoup(chapter_page, 'html5lib')

        if chapter_postid:
            post = chapter_soup.find('li', id='post-'+chapter_postid)
        else:
            # just the first one in the thread, then
            post = chapter_soup.find('li', class_='message')
        post = post.find('blockquote', class_='messageText')
        post.name = 'div'

        chapters.append((str(link.string), post.prettify()))

    story['chapters'] = chapters

    return story
