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
    """Royal Road: a place where people write novels, mostly seeming to be light-novel in tone."""
    @staticmethod
    def matches(url):
        # e.g. https://royalroadl.com/fiction/6752/lament-of-the-fallen
        match = re.match(r'^(https?://royalroadl\.com/fiction/\d+)/?.*', url)
        if match:
            return match.group(1) + '/'

    def extract(self, url):
        workid = re.match(r'^https?://royalroadl\.com/fiction/(\d+)/?.*', url).group(1)
        soup = self._soup('https://royalroadl.com/fiction/{}'.format(workid))
        # should have gotten redirected, for a valid title

        original_maxheaders = http.client._MAXHEADERS
        http.client._MAXHEADERS = 1000

        story = Section(
            title=soup.find('h1', property='name').string.strip(),
            author=soup.find('meta', property='books:author').get('content').strip(),
            url=soup.find('meta', property='og:url').get('content').strip()
        )

        for chapter in soup.select('#chapters tbody tr[data-url]'):
            chapter_url = str(urllib.parse.urljoin(story.url, str(chapter.get('data-url'))))

            updated = datetime.datetime.fromtimestamp(
                int(chapter.find('time').get('unixtime')),
            )

            story.add(Chapter(title=chapter.find('a', href=True).string.strip(), contents=self._chapter(chapter_url), date=updated))

        http.client._MAXHEADERS = original_maxheaders

        return story

    def _chapter(self, url):
        logger.info("Extracting chapter @ %s", url)
        soup = self._soup(url)
        content = soup.find('div', class_='chapter-content')

        # TODO: this could be more robust, and I don't know if there's post-chapter notes anywhere as well.
        author_note = soup.find('div', class_='author-note-portlet')

        return (author_note and (author_note.prettify() + '<hr/>') or '') + content.prettify()
