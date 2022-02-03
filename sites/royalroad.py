#!/usr/bin/python

import http.client
import logging
import datetime
import re
from . import register, Site, Section, Chapter, SiteSpecificOption

logger = logging.getLogger(__name__)


@register
class RoyalRoad(Site):
    domain = r'royalroad'

    @staticmethod
    def get_site_specific_option_defs():
        return Site.get_site_specific_option_defs() + [
            SiteSpecificOption(
                'skip_spoilers',
                '--skip-spoilers/--include-spoilers',
                default=True,
                help="If true, do not transcribe any tags that are marked as a spoiler."
            ),
        ]

    """Royal Road: a place where people write novels, mostly seeming to be light-novel in tone."""
    @classmethod
    def matches(cls, url):
        # e.g. https://royalroad.com/fiction/6752/lament-of-the-fallen
        match = re.match(r'^(https?://(?:www\.)?%s\.com/fiction/\d+)/?.*' % cls.domain, url)
        if match:
            return match.group(1) + '/'

    def extract(self, url):
        workid = re.match(r'^https?://(?:www\.)?%s\.com/fiction/(\d+)/?.*' % self.domain, url).group(1)
        soup = self._soup(f'https://www.{self.domain}.com/fiction/{workid}')
        # should have gotten redirected, for a valid title

        original_maxheaders = http.client._MAXHEADERS
        http.client._MAXHEADERS = 1000

        story = Section(
            title=soup.find('h1', property='name').string.strip(),
            author=soup.find('meta', property='books:author').get('content').strip(),
            url=soup.find('meta', property='og:url').get('content').strip(),
            cover_url=soup.find('img', class_='thumbnail')['src'],
            summary=str(soup.find('div', property='description')).strip(),
            tags=[tag.get_text().strip() for tag in soup.select('span.tags a.fiction-tag')]
        )

        for chapter in soup.select('#chapters tbody tr[data-url]'):
            chapter_url = str(self._join_url(story.url, str(chapter.get('data-url'))))

            contents, updated = self._chapter(chapter_url, len(story) + 1)

            story.add(Chapter(title=chapter.find('a', href=True).string.strip(), contents=contents, date=updated))

        http.client._MAXHEADERS = original_maxheaders

        story.footnotes = self.footnotes
        self.footnotes = []

        return story

    def _chapter(self, url, chapterid):
        logger.info("Extracting chapter @ %s", url)
        soup = self._soup(url)
        content = soup.find('div', class_='chapter-content')

        self._clean(content)
        self._clean_spoilers(content, chapterid)

        content = content.prettify()

        author_note = soup.find_all('div', class_='author-note-portlet')

        if len(author_note) == 1:
            # Find the parent of chapter-content and check if the author's note is the first child div
            if 'author-note-portlet' in soup.find('div', class_='chapter-content').parent.find('div')['class']:
                content = author_note[0].prettify() + '<hr/>' + content
            else:  # The author note must be after the chapter content
                content = content + '<hr/>' + author_note[0].prettify()
        elif len(author_note) == 2:
            content = author_note[0].prettify() + '<hr/>' + content + '<hr/>' + author_note[1].prettify()

        updated = datetime.datetime.fromtimestamp(
            int(soup.find(class_="profile-info").find('time').get('unixtime'))
        )

        return content, updated

    def _clean_spoilers(self, content, chapterid):
        # Spoilers to footnotes
        for spoiler in content.find_all(class_=('spoiler-new')):
            spoiler_title = spoiler.get('data-caption')
            if self.options['skip_spoilers']:
                link = self._footnote(spoiler, chapterid)
                if spoiler_title:
                    link.string = spoiler_title
            else:
                link = spoiler_title and f'[SPOILER: {spoiler_title}]' or '[SPOILER]'
            new_spoiler = self._new_tag('div')
            new_spoiler.append(link)
            spoiler.replace_with(new_spoiler)


@register
class RoyalRoadL(RoyalRoad):
    domain = 'royalroadl'
