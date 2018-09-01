#!/usr/bin/python

import http.client
import logging
import datetime
import re
import urllib
from . import register, Site, Section, Chapter

logger = logging.getLogger(__name__)


@register
class RoyalRoad(Site):
    domain = r'royalroad'

    """Royal Road: a place where people write novels, mostly seeming to be light-novel in tone."""
    @classmethod
    def matches(cls, url):
        # e.g. https://royalroad.com/fiction/6752/lament-of-the-fallen
        match = re.match(r'^(https?://(?:www\.)?%s\.com/fiction/\d+)/?.*' % cls.domain, url)
        if match:
            return match.group(1) + '/'

    def extract(self, url):
        workid = re.match(r'^https?://(?:www\.)?%s\.com/fiction/(\d+)/?.*' % self.domain, url).group(1)
        soup = self._soup('https://www.{}.com/fiction/{}'.format(self.domain, workid))
        # should have gotten redirected, for a valid title

        original_maxheaders = http.client._MAXHEADERS
        http.client._MAXHEADERS = 1000

        story = Section(
            title=soup.find('h1', property='name').string.strip(),
            author=soup.find('meta', property='books:author').get('content').strip(),
            url=soup.find('meta', property='og:url').get('content').strip(),
            cover_url=soup.find('img', class_='thumbnail')['src']
        )

        for chapter in soup.select('#chapters tbody tr[data-url]'):
            chapter_url = str(urllib.parse.urljoin(story.url, str(chapter.get('data-url'))))

            contents, updated = self._chapter(chapter_url)

            story.add(Chapter(title=chapter.find('a', href=True).string.strip(), contents=contents, date=updated))

        http.client._MAXHEADERS = original_maxheaders

        return story

    def _chapter(self, url):
        logger.info("Extracting chapter @ %s", url)
        soup = self._soup(url)
        content = soup.find('div', class_='chapter-content')

        # TODO: this could be more robust, and I don't know if there's post-chapter notes anywhere as well.
        author_note = soup.find('div', class_='author-note-portlet')

        updated = datetime.datetime.fromtimestamp(
            int(soup.find(class_="profile-info").find('time').get('unixtime'))
        )

        return (author_note and (author_note.prettify() + '<hr/>') or '') + content.prettify(), updated


@register
class RoyalRoadL(RoyalRoad):
    domain = 'royalroadl'
