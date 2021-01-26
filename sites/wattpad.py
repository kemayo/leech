#!/usr/bin/python

import http.client
import logging
import datetime
import re
from . import register, Site, Section, Chapter

logger = logging.getLogger(__name__)


@register
class Wattpad(Site):
    """Wattpad"""
    @classmethod
    def matches(cls, url):
        # e.g. https://www.wattpad.com/story/208753031-summoned-to-have-tea-with-the-demon-lord-i-guess
        # chapter URLs are e.g. https://www.wattpad.com/818687865-summoned-to-have-tea-with-the-demon-lord-i-guess
        match = re.match(r'^(https?://(?:www\.)?wattpad\.com/story/\d+)?.*', url)
        if match:
            # the story-title part is unnecessary
            return match.group(1)

    def extract(self, url):
        # URL should give us the table of contents page for the story
        soup = self._soup(url)

        story = Section(
            title=soup.find('h1').string.strip(),
            author=soup.find('div', class_='author-info').strong.a.string.strip(),
            url=soup.find('link', rel='canonical')['href'],
            cover_url=soup.find('div', class_='cover').img['src']
        )

        info = soup.find('div', class_='author-info').small
        published = datetime.datetime.strptime(info['title'], 'First published: %b %d, %Y')
        info.find('span').decompose()
        updated = datetime.datetime.strptime(info.get_text().strip(), 'Updated %b %d, %Y')

        for chapter in soup.select('ul.table-of-contents a'):
            chapter_url = str(self._join_url(story.url, str(chapter['href'])))

            contents = self._chapter(chapter_url)

            story.add(Chapter(title=chapter.string.strip(), contents=contents))

        # fix up the dates
        story[-1].date = updated
        story[0].date = published

        return story

    def _chapter(self, url):
        logger.info("Extracting chapter @ %s", url)
        soup = self._soup(url)

        content = soup.find('article').find('div', class_="page").pre
        content.name = 'div'

        for ad in content.find_all(attrs={'aria_label': "Advertisement"}):
            ad.decompose()

        content.extract()
        return content.prettify()
