#!/usr/bin/python

import logging
import attr
import datetime
import json
import re
import os.path
import urllib
from . import register, Site, Section, Chapter, Image

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


@attr.s
class SiteDefinition:
    url = attr.ib()
    title = attr.ib()
    author = attr.ib()
    content_selector = attr.ib()
    # If present, find something within `content` to use a chapter title; if not found, the link text to it will be used
    content_title_selector = attr.ib(default=False)
    # If present, find a specific element in the `content` to be the chapter text
    content_text_selector = attr.ib(default=False)
    # If present, it looks for chapters linked from `url`. If not, it assumes `url` points to a chapter.
    chapter_selector = attr.ib(default=False)
    # If present, use to find a link to the next content page (only used if not using chapter_selector)
    next_selector = attr.ib(default=False)
    # If present, use to filter out content that matches the selector
    filter_selector = attr.ib(default=False)
    cover_url = attr.ib(default='')

    # If present, use to also download the images and embed them into the epub.
    image_selector = attr.ib(default=False)


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
            content_url = definition.url
            while content_url and content_url not in found_content_urls:
                found_content_urls.add(content_url)
                for chapter in self._chapter(content_url, definition):
                    story.add(chapter)
                if definition.next_selector:
                    soup, base = self._soup(content_url)
                    next_link = soup.select(definition.next_selector)
                    if next_link:
                        next_link_url = str(next_link[0].get('href'))
                        if base:
                            next_link_url = self._join_url(base, next_link_url)
                        content_url = self._join_url(content_url, next_link_url)
                    else:
                        content_url = False
                else:
                    content_url = False

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

            self._clean(content)

            images = []
            if definition.image_selector:
                images = self.load_images(content, definition.image_selector)

            chapters.append(Chapter(
                title=title,
                contents=content.prettify(),
                # TODO: better date detection
                date=datetime.datetime.now(),
                images=images
            ))

        return chapters

    def load_images(self, content, selector):
        images = []
        for image in content.select(selector):
            if not image.has_attr('src'):
                continue

            image_url = image['src']
            url = urllib.parse.urlparse(image_url)
            local_path = 'chapter_images/' + url.path.strip('/')

            image_res = self.session.get(image_url)
            content_type = image_res.headers['Content-Type']
            image_data = image_res.content

            images.append(Image(
                path=local_path,
                contents=image_data,
                content_type=content_type
            ))
            # Replace 'src'.
            image['src'] = '../' + local_path
            if image.has_attr('srcset'):
                del image['srcset']

        return images
