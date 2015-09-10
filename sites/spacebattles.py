#!/usr/bin/python

import re
from bs4 import BeautifulSoup


def match(url):
    return re.match(r'^https?://forums.(?:spacebattles|sufficientvelocity).com/threads/.*\d+/?.*', url)

def extract(url, fetch):
    page = fetch(url)
    soup = BeautifulSoup(page, 'html5lib')

    base = soup.head.base.get('href')

    story = {}
    story['title'] = str(soup.find('h1').string)
    story['author'] = str(soup.find('p', id='pageDescription').find('a', class_='username').string)

    threadmarks_link = soup.find(class_="threadmarksTrigger")
    if not threadmarks_link:
        print("No threadmarks")
        return

    page = fetch(base + threadmarks_link.get('href'))
    soup = BeautifulSoup(page, 'html5lib')

    marks = soup.select('li.primaryContent.memberListItem')
    if not marks:
        print("No marks on threadmarks page")
        return

    chapters = []
    for mark in marks:
        href = mark.a.get('href')
        print("Extracting chapter from", href)
        match = re.match(r'posts/(\d+)/?', href)
        if not match:
            match = re.match(r'.+#post-(\d+)$', href)
            if not match:
                print("Unparseable threadmark href", href)
        chapter_postid = match and match.group(1)
        chapter_page = fetch(base + href)
        chapter_soup = BeautifulSoup(chapter_page, 'html5lib')

        if chapter_postid:
            post = chapter_soup.find('li', id='post-'+chapter_postid)
        else:
            # just the first one in the thread, then
            post = chapter_soup.find('li', class_='message')
        post = post.find('blockquote', class_='messageText')
        post.name = 'div'

        chapters.append((str(mark.a.string), post.prettify()))

    story['chapters'] = chapters

    return story
