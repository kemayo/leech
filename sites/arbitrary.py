#!/usr/bin/python

import logging
from attrs import define
import datetime
import json
import re
import os.path
from . import register, Site, Section, Chapter, SiteException

logger = logging.getLogger(__name__)

"""
Example JSON:
{
    "url": "https://practicalguidetoevil.wordpress.com/table-of-contents/",
    "title": "A Practical Guide To Evil: Book 1",
    "author": "erraticerrata",
    "chapter_selector": "#main .entry-content > ul > li > a",
    "content_selector": "#main .entry-content",
    "filter_selector": ".sharedaddy, .wpcnt, style",
    "cover_url": "https://gitlab.com/Mikescher2/A-Practical-Guide-To-Evil-Lyx/raw/master/APGTE_1/APGTE_front.png"
}
"""


@define
class SiteDefinition:
    url: str
    title: str
    author: str
    content_selector: str
    # If present, find something within `content` to use a chapter title; if not found, the link text to it will be used
    content_title_selector: str = False
    # If present, find a specific element in the `content` to be the chapter text
    content_text_selector: str = False
    # If present, it looks for chapters linked from `url`. If not, it assumes `url` points to a chapter.
    chapter_selector: str = False
    # If present, use to find a link to the next content page (only used if not using chapter_selector)
    next_selector: str = False
    # If present, use to filter out content that matches the selector
    filter_selector: str = False
    cover_url: str = ''


@register
class Arbitrary(Site):
    """A way to describe an arbitrary side for a one-off fetch
    """
    @staticmethod
    def matches(url):
        # e.g. practical1.json
        if url.endswith('.json') and os.path.isfile(url):
            return url

    def extract(self, url):
        with open(url) as definition_file:
            definition = SiteDefinition(**json.load(definition_file))

        story = Section(
            title=definition.title,
            author=definition.author,
            url=url,
            cover_url=definition.cover_url
        )

        if definition.chapter_selector:
            soup, base = self._soup(definition.url)
            for chapter_link in soup.select(definition.chapter_selector):
                chapter_url = str(chapter_link.get('href'))
                if base:
                    chapter_url = self._join_url(base, chapter_url)
                chapter_url = self._join_url(definition.url, chapter_url)
                for chapter in self._chapter(chapter_url, definition, title=chapter_link.string):
                    story.add(chapter)
        else:
            # set of already processed urls. Stored to detect loops.
            found_content_urls = set()
            content_urls = [definition.url]

            def process_content_url(content_url):
                if content_url in found_content_urls:
                    return None
                found_content_urls.add(content_url)
                for chapter in self._chapter(content_url, definition):
                    story.add(chapter)
                return content_url

            while content_urls:
                for temp_url in content_urls:
                    # stop inner loop once a new link is found
                    if content_url := process_content_url(temp_url):
                        break
                # reset url list
                content_urls = []
                if content_url and definition.next_selector:
                    soup, base = self._soup(content_url)
                    next_link = soup.select(definition.next_selector)
                    if next_link:
                        for next_link_item in next_link:
                            next_link_url = str(next_link_item.get('href'))
                            if base:
                                next_link_url = self._join_url(base, next_link_url)
                            content_urls.append(self._join_url(content_url, next_link_url))

        if not story:
            raise SiteException("No story content found; check the content selectors")

        self._finalize(story)

        return story

    def _chapter(self, url, definition, title=False):
        logger.info("Extracting chapter @ %s", url)
        soup, base = self._soup(url)

        chapters = []

        if not soup.select(definition.content_selector):
            return chapters

        # clean up a few things which will definitely break epubs:
        # TODO: expand this greatly, or make it configurable
        for namespaced in soup.find_all(re.compile(r'[a-z]+:[a-z]+')):
            # Namespaced elements are going to cause validation errors
            namespaced.decompose()

        for content in soup.select(definition.content_selector):
            if definition.filter_selector:
                for filtered in content.select(definition.filter_selector):
                    filtered.decompose()

            if definition.content_title_selector:
                title_element = content.select(definition.content_title_selector)
                if title_element:
                    title = title_element[0].get_text().strip()

            if definition.content_text_selector:
                # TODO: multiple text elements?
                content = content.select(definition.content_text_selector)[0]

            # TODO: consider `'\n'.join(map(str, content.contents))`
            content.name = 'div'

            self._clean(content, base)

            chapters.append(Chapter(
                title=title,
                contents=content.prettify(),
                # TODO: better date detection
                date=datetime.datetime.now()
            ))

        return chapters
