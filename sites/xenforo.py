#!/usr/bin/python

import datetime
import re
import logging
import requests_cache
from bs4 import BeautifulSoup

from . import register, Site, SiteException, SiteSpecificOption, Section, Chapter
import mintotp

logger = logging.getLogger(__name__)


class XenForo(Site):
    """XenForo is forum software that powers a number of fiction-related forums."""

    domain = False
    index_urls = False

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
        match = re.match(r'^(https?://%s/(?:index\.php\?)?threads/[^/]*\d+/(?:\d+/)?reader)/?.*' % cls.domain, url)
        if match:
            return match.group(1)
        match = re.match(r'^(https?://%s/(?:index\.php\?)?threads/[^/]*\d+)/?.*' % cls.domain, url)
        if match:
            return match.group(1) + '/'

    def siteurl(self, path):
        if self.index_urls:
            return f'https://{self.domain}/index.php?{path}'
        return f'https://{self.domain}/{path}'

    def login(self, login_details):
        with requests_cache.disabled():
            login = self.session.get(self.siteurl('login/'))
            soup = BeautifulSoup(login.text, 'html5lib')
            post, action, method = self._form_data(soup.find(class_='p-body-content'))
            post['login'] = login_details[0]
            post['password'] = login_details[1]
            # I feel the session *should* handle this cookies bit for me. But
            # it doesn't. And I don't know why.
            result = self.session.post(
                self._join_url(login.url, action),
                data=post, cookies=login.cookies
            )
            if not result.ok:
                return logger.error("Failed to log in as %s", login_details[0])
            soup = BeautifulSoup(result.text, 'html5lib')
            if twofactor := soup.find('form', action="/login/two-step"):
                if len(login_details) < 3:
                    return logger.error("Failed to log in as %s; login requires 2FA secret", login_details[0])
                post, action, method = self._form_data(twofactor)
                post['code'] = mintotp.totp(login_details[2])
                result = self.session.post(
                    self._join_url(login.url, action),
                    data=post, cookies=login.cookies
                )
                if not result.ok:
                    return logger.error("Failed to log in as %s; 2FA failed", login_details[0])
            logger.info("Logged in as %s", login_details[0])

    def extract(self, url):
        soup, base = self._soup(url)

        story = self._base_story(soup)

        threadmark_categories = {}
        # Note to self: in the source this is data-categoryId, but the parser
        # in bs4 lowercases tags and attributes...
        for cat in soup.find_all('a', attrs={'data-categoryid': True}):
            threadmark_categories[int(cat['data-categoryid'])] = cat['title']

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
            match = re.search(r'\d+/(\d+)/reader', reader_url)
            if match:
                cat = int(match.group(1))
                if cat != 1 and cat in threadmark_categories:
                    story.title = f'{story.title} ({threadmark_categories[cat]})'
            idx = 0
            while reader_url:
                reader_url = self._join_url(base, reader_url)
                logger.info("Fetching chapters @ %s", reader_url)
                reader_soup, reader_base = self._soup(reader_url)
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
                        contents=self._clean_chapter(post, len(story) + 1, base),
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
        soup, base = self._soup(url)

        threadmarks_link = soup.find(class_="threadmarksTrigger", href=True)
        if not threadmarks_link:
            try:
                threadmarks_link = soup.select('.threadmarkMenus a.OverlayTrigger')[0]
            except IndexError:
                pass

        if not threadmarks_link:
            raise SiteException("No threadmarks")

        href = threadmarks_link.get('href')
        soup, base = self._soup(self._join_url(base, href))

        fetcher = soup.find(class_='ThreadmarkFetcher')
        while fetcher:
            # ThreadmarksPro, hiding some threadmarks. Means the API is available to do this.
            # Note: the fetched threadmarks can contain more placeholder elements to fetch. Ergo, loop.
            # Good test case: https://forums.sufficientvelocity.com/threads/ignition-mtg-multicross-planeswalker-pc.26099/threadmarks
            # e.g.: <li class="primaryContent threadmarkListItem ThreadmarkFetcher _depth0 filler" data-range-min="0" data-range-max="306" data-thread-id="26099" data-category-id="1" title="305 hidden">
            response = self.session.post(self.siteurl('threads/threadmarks/load-range'), data={
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
        post, base = self._post_from_url(url)

        return self._clean_chapter(post, chapterid, base), self._post_date(post)

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
            url = self.siteurl(f'posts/{postid}/')
        soup, base = self._soup(url, 'html5lib')

        if postid:
            return self._posts_from_page(soup, postid), base

        # just the first one in the thread, then
        return soup.find('li', class_='message'), base

    def _chapter_contents(self, post):
        return post.find('blockquote', class_='messageText')

    def _clean_chapter(self, post, chapterid, base):
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
                if "margin-left" in tag['style']:
                    continue
                del tag['style']
        for tag in post.select('.quoteExpand, .bbCodeBlock-expandLink, .bbCodeBlock-shrinkLink'):
            tag.decompose()
        self._clean(post, base)
        self._clean_spoilers(post, chapterid)
        return post.prettify()

    def _clean_spoilers(self, post, chapterid):
        # spoilers don't work well, so turn them into epub footnotes
        for spoiler in post.find_all(class_='ToggleTriggerAnchor'):
            spoilerTarget = spoiler.find(class_='SpoilerTarget')

            # This is a bit of a hack, but it works
            # This downloads the spoiler image
            img_exist = list(spoilerTarget.find_all('img'))
            if len(img_exist) > 0:
                for i in img_exist:
                    # For some weird reason, the images are duplicated, so this should skip some
                    if img_exist.index(i) % 2 == 0:
                        i.decompose()
                    else:
                        if not i.has_attr('src'):
                            i['src'] = i['data-url']
                        if i['src'].startswith('proxy.php'):
                            i['src'] = f"{self.domain}/{i['src']}"
                spoiler.replace_with(spoiler.find(class_='SpoilerTarget'))
            else:
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
                new_spoiler = self._new_tag('div', class_="leech-spoiler")
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
