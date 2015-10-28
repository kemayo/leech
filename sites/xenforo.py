#!/usr/bin/python

import re
from . import register, Site, SiteException


class XenForo(Site):
    """XenForo is forum software that powers a number of fiction-related forums."""

    domain = False

    @classmethod
    def matches(cls, url):
        return re.match(r'^https?://%s/threads/.*\d+/?.*' % cls.domain, url)

    def login(self, login_details):
        # Todo: handle non-https?
        post = {
            'login': login_details[0],
            'password': login_details[1],
        }
        self.fetch.session.post('https://%s/login/login' % self.domain, data=post)
        print("Logged in as", login_details[0])

    def extract(self, url):
        soup = self._soup(url)

        base = soup.head.base.get('href')

        story = {}
        story['title'] = soup.find('h1').get_text()
        story['author'] = soup.find('p', id='pageDescription').find('a', class_='username').get_text()

        marks = self._chapter_list(url)

        chapters = []
        for mark in marks:
            href = mark.get('href')
            if '/members' in href:
                continue
            if not href.startswith('http'):
                href = base + href
            print("Fetching chapter", mark.string, href)
            chapters.append((str(mark.string), self._chapter(href)))

        story['chapters'] = chapters

        return story

    def _chapter_list(self, url):
        try:
            return self._chapter_list_threadmarks(url)
        except SiteException as e:
            print("Tried threadmarks", e.args)
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
        post = self._post_from_url(url)

        return self._clean_chapter(post)

    def _post_from_url(self, url):
        # URLs refer to specific posts, so get just that one
        # if no specific post referred to, get the first one
        match = re.search(r'posts/(\d+)/?', url)
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


class XenForoIndex(XenForo):
    @classmethod
    def matches(cls, url):
        return re.match(r'^https?://%s/posts/\d+/?.*' % cls.domain, url)

    def _chapter_list(self, url):
        return self._chapter_list_index(url)


@register
class SpaceBattles(XenForo):
    domain = 'forums.spacebattles.com'


@register
class SpaceBattlesIndex(XenForoIndex):
    domain = 'forums.spacebattles.com'


@register
class SufficientVelocity(XenForo):
    domain = 'forums.sufficientvelocity.com'


@register
class QuestionableQuesting(XenForo):
    domain = 'forum.questionablequesting.com'


@register
class QuestionableQuestingIndex(QuestionableQuesting, XenForoIndex):
    pass
