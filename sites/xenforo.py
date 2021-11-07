#!/usr/bin/python

import datetime
import re
import logging
from bs4 import BeautifulSoup

from . import register, Site, SiteException, SiteSpecificOption, Section, Chapter

logger = logging.getLogger(__name__)


class XenForo(Site):
    """XenForo is forum software that powers a number of fiction-related forums."""

    domain = False

    @staticmethod
    def get_site_specific_option_defs():
        return Site.get_site_specific_option_defs() + [
            SiteSpecificOption(
                'include_index',
                '--include-index/--no-include-index',
                default=False,
                help="If true, the post marked as an index will be included as a chapter."
            ),
            SiteSpecificOption(
                'skip_spoilers',
                '--skip-spoilers/--include-spoilers',
                default=True,
                help="If true, do not transcribe any tags that are marked as a spoiler."
            ),
            SiteSpecificOption(
                'offset',
                '--offset',
                type=int,
                help="The chapter index to start in the chapter marks."
            ),
            SiteSpecificOption(
                'limit',
                '--limit',
                type=int,
                help="The chapter to end at at in the chapter marks."
            ),
        ]

    @classmethod
    def matches(cls, url):
        match = re.match(r'^(https?://%s/threads/[^/]*\d+/(?:\d+/)?reader)/?.*' % cls.domain, url)
        if match:
            return match.group(1)
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
        logger.info("Logged in as %s", login_details[0])

    def extract(self, url):
        soup = self._soup(url)

        base = soup.head.base and soup.head.base.get('href') or url

        story = self._base_story(soup)

        if url.endswith('/reader'):
            reader_url = url
        elif soup.find('a', class_='readerToggle'):
            reader_url = soup.find('a', class_='readerToggle').get('href')
        elif soup.find('div', class_='threadmarks-reader'):
            # Technically this is the xenforo2 bit, but :shrug:
            reader_url = soup.find('div', class_='threadmarks-reader').find('a').get('href')
        else:
            reader_url = False

        if reader_url:
            idx = 0
            while reader_url:
                reader_url = self._join_url(base, reader_url)
                logger.info("Fetching chapters @ %s", reader_url)
                reader_soup = self._soup(reader_url)
                posts = self._posts_from_page(reader_soup)

                for post in posts:
                    idx = idx + 1
                    if self.options['offset'] and idx < self.options['offset']:
                        continue
                    if self.options['limit'] and idx >= self.options['limit']:
                        continue
                    title = self._threadmark_title(post)
                    logger.info("Extracting chapter \"%s\"", title)

                    story.add(Chapter(
                        title=title,
                        contents=self._clean_chapter(post, len(story) + 1),
                        date=self._post_date(post)
                    ))

                reader_url = False
                if reader_soup.find('link', rel='next'):
                    reader_url = reader_soup.find('link', rel='next').get('href')
        else:
            # TODO: Research whether reader mode is guaranteed to be enabled
            # when threadmarks are; if so, can delete this branch.
            marks = [
                mark for mark in self._chapter_list(url)
                if '/members' not in mark.get('href') and '/threadmarks' not in mark.get('href')
            ]
            marks = marks[self.options['offset']:self.options['limit']]

            for idx, mark in enumerate(marks, 1):
                href = self._join_url(base, mark.get('href'))
                title = str(mark.string).strip()
                logger.info("Fetching chapter \"%s\" @ %s", title, href)
                contents, post_date = self._chapter(href, idx)
                chapter = Chapter(title=title, contents=contents, date=post_date)
                story.add(chapter)

        story.footnotes = self.footnotes
        self.footnotes = []

        return story

    def _base_story(self, soup):
        url = soup.find('meta', property='og:url').get('content')
        title = soup.select('div.titleBar > h1')[0]
        # clean out informational bits from the title
        for tag in title.find_all(class_='prefix'):
            tag.decompose()
        tags = [tag.get_text().strip() for tag in soup.select('div.tagBlock a.tag')]
        return Section(
            title=title.get_text().strip(),
            author=soup.find('p', id='pageDescription').find('a', class_='username').get_text(),
            url=url,
            tags=tags
        )

    def _posts_from_page(self, soup, postid=False):
        if postid:
            return soup.find('li', id='post-' + postid)
        return soup.select('#messageList > li.hasThreadmark')

    def _threadmark_title(self, post):
        # Get the title, removing "<strong>Threadmark:</strong>" which precedes it
        return ''.join(post.select('div.threadmarker > span.label')[0].findAll(text=True, recursive=False)).strip()

    def _chapter_list(self, url):
        try:
            return self._chapter_list_threadmarks(url)
        except SiteException as e:
            logger.debug("Tried threadmarks (%r)", e.args)
            return self._chapter_list_index(url)

    def _chapter_list_threadmarks(self, url):
        soup = self._soup(url)

        threadmarks_link = soup.find(class_="threadmarksTrigger", href=True)
        if not threadmarks_link:
            try:
                threadmarks_link = soup.select('.threadmarkMenus a.OverlayTrigger')[0]
            except IndexError:
                pass

        if not threadmarks_link:
            raise SiteException("No threadmarks")

        href = threadmarks_link.get('href')
        base = soup.head.base.get('href')
        soup = self._soup(base + href)

        fetcher = soup.find(class_='ThreadmarkFetcher')
        while fetcher:
            # ThreadmarksPro, hiding some threadmarks. Means the API is available to do this.
            # Note: the fetched threadmarks can contain more placeholder elements to fetch. Ergo, loop.
            # Good test case: https://forums.sufficientvelocity.com/threads/ignition-mtg-multicross-planeswalker-pc.26099/threadmarks
            # e.g.: <li class="primaryContent threadmarkListItem ThreadmarkFetcher _depth0 filler" data-range-min="0" data-range-max="306" data-thread-id="26099" data-category-id="1" title="305 hidden">
            response = self.session.post(f'https://{self.domain}/index.php?threads/threadmarks/load-range', data={
                # I did try a fetch on min/data-min+data-max, but there seems
                # to be an absolute limit which the API fetch won't override
                'min': fetcher.get('data-range-min'),
                'max': fetcher.get('data-range-max'),
                'thread_id': fetcher.get('data-thread-id'),
                'category_id': fetcher.get('data-category-id'),
                '_xfResponseType': 'json',
            }).json()
            responseSoup = BeautifulSoup(response['templateHtml'], 'html5lib')
            fetcher.replace_with(responseSoup)
            fetcher = soup.find(class_='ThreadmarkFetcher')

        marks = soup.find(class_='threadmarks').select('li.primaryContent.threadmarkListItem a, li.primaryContent.threadmarkItem a')
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

        if self.options['include_index']:
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
            return self._posts_from_page(soup, postid)

        # just the first one in the thread, then
        return soup.find('li', class_='message')

    def _chapter_contents(self, post):
        return post.find('blockquote', class_='messageText')

    def _clean_chapter(self, post, chapterid):
        post = self._chapter_contents(post)
        post.name = 'div'
        # mostly, we want to remove colors because the Kindle is terrible at them
        # TODO: find a way to denote colors, because it can be relevant
        # TODO: at least invisitext, because outside of silly DC Lantern stuff, it's the most common
        for tag in post.find_all(style=True):
            if tag['style'] == 'color: transparent' and tag.text == 'TAB':
                # Some stories fake paragraph indents like this. The output
                # stylesheet will handle this just fine.
                tag.decompose()
            else:
                # There's a few things which xenforo does as styles, despite there being perfectly good tags
                # TODO: more robust CSS parsing? This is very whitespace dependent, if nothing else.
                if "font-family: 'Courier New'" in tag['style']:
                    tag.wrap(self._new_tag('code'))
                if "text-decoration: strikethrough" in tag['style']:
                    tag.wrap(self._new_tag('strike'))
                tag.unwrap()
        for tag in post.select('.quoteExpand, .bbCodeBlock-expandLink, .bbCodeBlock-shrinkLink'):
            tag.decompose()
        self._clean(post)
        self._clean_spoilers(post, chapterid)
        return post.prettify()

    def _clean_spoilers(self, post, chapterid):
        # spoilers don't work well, so turn them into epub footnotes
        for spoiler in post.find_all(class_='ToggleTriggerAnchor'):
            spoiler_title = spoiler.find(class_='SpoilerTitle')
            if self.options['skip_spoilers']:
                link = self._footnote(spoiler.find(class_='SpoilerTarget').extract(), chapterid)
                if spoiler_title:
                    link.string = spoiler_title.get_text()
            else:
                if spoiler_title:
                    link = f'[SPOILER: {spoiler_title.get_text()}]'
                else:
                    link = '[SPOILER]'
            new_spoiler = self._new_tag('div')
            new_spoiler.append(link)
            spoiler.replace_with(new_spoiler)

    def _post_date(self, post):
        maybe_date = post.find(class_='DateTime')
        if 'data-time' in maybe_date.attrs:
            return datetime.datetime.fromtimestamp(int(maybe_date['data-time']))
        if 'title' in maybe_date.attrs:
            # title="Feb 24, 2015 at 1:17 PM"
            return datetime.datetime.strptime(maybe_date['title'], "%b %d, %Y at %I:%M %p")
        raise SiteException("No date", maybe_date)


class XenForoIndex(XenForo):
    @classmethod
    def matches(cls, url):
        match = re.match(r'^(https?://%s/posts/\d+)/?.*' % cls.domain, url)
        if match:
            return match.group(1) + '/'

    def _chapter_list(self, url):
        return self._chapter_list_index(url)


@register
class QuestionableQuesting(XenForo):
    domain = 'forum.questionablequesting.com'


@register
class QuestionableQuestingIndex(QuestionableQuesting, XenForoIndex):
    _key = "QuestionableQuesting"


@register
class AlternateHistory(XenForo):
    domain = 'www.alternatehistory.com/forum'


@register
class AlternateHistoryIndex(AlternateHistory, XenForoIndex):
    _key = "AlternateHistory"
