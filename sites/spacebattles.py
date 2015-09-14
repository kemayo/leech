#!/usr/bin/python

import re
from . import register, Site, SiteException


@register
class SpaceBattles(Site):
    """SpaceBattles is a forum..."""

    @staticmethod
    def matches(url):
        return re.match(r'^https?://forums.(?:spacebattles|sufficientvelocity).com/threads/.*\d+/?.*', url)

    def extract(self, url):
        soup = self._soup(url)

        base = soup.head.base.get('href')

        story = {}
        story['title'] = str(soup.find('h1').string)
        story['author'] = str(soup.find('p', id='pageDescription').find('a', class_='username').string)

        marks = self._chapter_list(url)

        chapters = []
        for mark in marks:
            href = mark.get('href')
            if '/members' in href:
                continue
            if not href.startswith('http'):
                href = base + href
            chapters.append((str(mark.string), self._chapter(href)))

        story['chapters'] = chapters

        return story

    def _chapter_list(self, url):
        soup = self._soup(url)

        threadmarks_link = soup.find(class_="threadmarksTrigger")
        if not threadmarks_link:
            raise SiteException("No threadmarks")

        base = soup.head.base.get('href')
        soup = self._soup(base + threadmarks_link.get('href'))

        marks = soup.select('li.primaryContent.memberListItem a')
        if not marks:
            raise SiteException("No marks on threadmarks page")

        return marks

    def _chapter(self, url):
        print("Extracting chapter from", url)
        match = re.match(r'posts/(\d+)/?', url)
        if not match:
            match = re.match(r'.+#post-(\d+)$', url)
            if not match:
                print("Unparseable threadmark href", url)
        chapter_postid = match and match.group(1)
        chapter_soup = self._soup(url, 'html5lib')

        if chapter_postid:
            post = chapter_soup.find('li', id='post-'+chapter_postid)
        else:
            # just the first one in the thread, then
            post = chapter_soup.find('li', class_='message')

        return self._clean_chapter(post)

    def _clean_chapter(self, post):
        post = post.find('blockquote', class_='messageText')
        post.name = 'div'
        # mostly, we want to remove colors because the Kindle is terrible at them
        for tag in post.find_all(style=True):
            del(tag['style'])
        return post.prettify()


@register
class SpaceBattlesIndex(SpaceBattles):
    """A spacebattles thread with an index post"""
    @staticmethod
    def matches(url):
        return re.match(r'^https?://forums.(?:spacebattles|sufficientvelocity).com/posts/\d+/?.*', url)

    def _chapter_list(self, url):
        soup = self._soup(url)

        match = re.match(r'.+/posts/(\d+)/?', url)
        if not match:
            raise SiteException("Unparseable post URL", url)

        post = post = soup.find('li', id='post-' + match.group(1))
        links = post.find('blockquote', class_='messageText').find_all('a', class_='internalLink')
        if not links:
            raise SiteException("No links in index?")

        return links
