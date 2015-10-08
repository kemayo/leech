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
        try:
            return self._chapter_list_threadmarks(url)
        except SiteException as e:
            print("Tried threadmarks", e.msg)
            return self._chapter_list_index(url)

    def _chapter_list_threadmarks(self, url):
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

    def _chapter_list_index(self, url):
        post = self._post_from_url(url)
        if not post:
            raise SiteException("Unparseable post URL", url)

        links = post.find('blockquote', class_='messageText').find_all('a', class_='internalLink')
        if not links:
            raise SiteException("No links in index?")

        return links

    def _chapter(self, url):
        print("Extracting chapter from", url)
        post = self._post_from_url(url)

        return self._clean_chapter(post)

    def _post_from_url(self, url):
        # URLs refer to specific posts, so get just that one
        # if no specific post referred to, get the first one
        match = re.match(r'posts/(\d+)/?', url)
        if not match:
            match = re.match(r'.+#post-(\d+)$', url)
            # could still be nothing here
        postid = match and match.group(1)
        soup = self._soup(url, 'html5lib')

        if postid:
            return soup.find('li', id='post-'+postid)

        # just the first one in the thread, then
        return soup.find('li', class_='message')

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
        return self._chapter_list_index(url)
