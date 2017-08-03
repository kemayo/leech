#!/usr/bin/python

import datetime
import re
from . import register, Site, SiteException, Section, Chapter


class XenForo(Site):
    """XenForo is forum software that powers a number of fiction-related forums."""

    domain = False

    @classmethod
    def matches(cls, url):
        match = re.match(r'^(https?://%s/threads/[^/]*\d+)/?.*' % cls.domain, url)
        if match:
            return match.group(1) + '/'

    def login(self, login_details):
        # Todo: handle non-https?
        post = {
            'login': login_details[0],
            'password': login_details[1],
        }
        self.session.post('https://%s/login/login' % self.domain, data=post)
        print("Logged in as", login_details[0])

    def extract(self, url):
        soup = self._soup(url)

        base = soup.head.base.get('href')

        story = Section(
            title=soup.select('div.titleBar > h1')[0].get_text(),
            author=soup.find('p', id='pageDescription').find('a', class_='username').get_text()
        )

        marks = [
            mark for mark in self._chapter_list(url)
            if '/members' not in mark.get('href') and '/threadmarks' not in mark.get('href')
        ]
        marks = marks[self.options.offset:self.options.limit]

        for idx, mark in enumerate(marks, 1):
            href = mark.get('href')
            if not href.startswith('http'):
                href = base + href
            title = str(mark.string).strip()
            print("Fetching chapter", title, href)
            chapter = Chapter(title=title, contents="")
            contents, post_date = self._chapter(href, idx)
            chapter.contents = contents
            chapter.date = post_date
            story.add(chapter)

        story.footnotes = self.footnotes
        self.footnotes = []

        return story

    def _chapter_list(self, url):
        try:
            return self._chapter_list_threadmarks(url)
        except SiteException as e:
            print("Tried threadmarks", e.args)
            return self._chapter_list_index(url)

    def _chapter_list_threadmarks(self, url):
        soup = self._soup(url)

        threadmarks_link = soup.find(class_="threadmarksTrigger", href=True)
        if not threadmarks_link:
            threadmarks_link = soup.select('.threadmarkMenus a.OverlayTrigger')[0]

        if not threadmarks_link:
            raise SiteException("No threadmarks")

        href = threadmarks_link.get('href')
        base = soup.head.base.get('href')
        soup = self._soup(base + href)

        marks = soup.select('.threadmarks li.primaryContent.threadmarkListItem a, .threadmarks li.primaryContent.threadmarkItem a')
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

        if self.options.include_index:
            fake_link = self._new_tag('a', href=url)
            fake_link.string = "Index"
            links.insert(0, fake_link)

        return links

    def _chapter(self, url, chapterid):
        post = self._post_from_url(url)

        return self._clean_chapter(post, chapterid), self._post_date(post)

    def _post_from_url(self, url):
        # URLs refer to specific posts, so get just that one
        # if no specific post referred to, get the first one
        match = re.search(r'posts/(\d+)/?', url)
        if not match:
            match = re.match(r'.+#post-(\d+)$', url)
            # could still be nothing here
        postid = match and match.group(1)
        if postid:
            # create a proper post-url, because threadmarks can sometimes
            # mess up page-wise with anchors
            url = 'https://%s/posts/%s/' % (self.domain, postid)
        soup = self._soup(url, 'html5lib')

        if postid:
            return soup.find('li', id='post-' + postid)

        # just the first one in the thread, then
        return soup.find('li', class_='message')

    def _clean_chapter(self, post, chapterid):
        post = post.find('blockquote', class_='messageText')
        post.name = 'div'
        # mostly, we want to remove colors because the Kindle is terrible at them
        for tag in post.find_all(style=True):
            if tag['style'] == 'color: transparent' and tag.text == 'TAB':
                # Some stories fake paragraph indents like this. The output
                # stylesheet will handle this just fine.
                tag.decompose()
            else:
                del(tag['style'])
        for tag in post.find_all(class_='quoteExpand'):
            tag.decompose()
        # spoilers don't work well, so turn them into epub footnotes
        for idx, spoiler in enumerate(post.find_all(class_='ToggleTriggerAnchor')):
            spoiler_title = spoiler.find(class_='SpoilerTitle')
            if self.options.spoilers:
                link = self._footnote(spoiler.find(class_='SpoilerTarget').extract(), chapterid)
                if spoiler_title:
                    link.string = spoiler_title.get_text()
            else:
                if spoiler_title:
                    link = '[SPOILER: {}]'.format(spoiler_title.get_text())
                else:
                    link = '[SPOILER]'
            new_spoiler = self._new_tag('div')
            new_spoiler.append(link)
            spoiler.replace_with(new_spoiler)
        return post.prettify()

    def _post_date(self, post):
        maybe_date = post.find(class_='DateTime')
        if 'data-time' in maybe_date.attrs:
            return datetime.datetime.fromtimestamp(int(maybe_date['data-time']))
        if 'title' in maybe_date.attrs:
            # title="Feb 24, 2015 at 1:17 PM"
            return datetime.datetime.strptime(maybe_date['title'], "%b %d, %Y at %I:%M %p")
        raise SiteException("No date", maybe_date)

    def _add_arguments(self, parser):
        parser.add_argument('--include-index', dest='include_index', action='store_true', default=False)
        parser.add_argument('--offset', dest='offset', type=int, default=None)
        parser.add_argument('--limit', dest='limit', type=int, default=None)
        parser.add_argument('--skip-spoilers', dest='spoilers', action='store_false', default=True)


class XenForoIndex(XenForo):
    @classmethod
    def matches(cls, url):
        match = re.match(r'^(https?://%s/posts/\d+)/?.*' % cls.domain, url)
        if match:
            return match.group(1) + '/'

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
