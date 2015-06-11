#!/usr/bin/python

import re
from bs4 import BeautifulSoup


def match(url):
    return re.match(r'^https?://forums.spacebattles.com/threads/.*\d+/?.*', url)

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

    marks = soup.find_all('li', class_='primaryContent memberListItem')
    if not marks:
        print("No marks on threadmarks page")
        return

    chapters = []
    for mark in marks:
        href = mark.a.get('href')
        print("Extracting chapter from", href)
        match = re.match(r'posts/(\d+)/?', href)
        if not match:
            print("Unparseable threadmark href", href)
            return
        postid = match.group(1)
        chapter_page = fetch(base + href)
        chapter_soup = BeautifulSoup(chapter_page, 'html5lib')

        post = chapter_soup.find('li', id='post-'+postid).find('blockquote', class_='messageText')
        post.name = 'div'

        chapters.append((str(mark.a.string), post.prettify()))

    story['chapters'] = chapters

    return story
