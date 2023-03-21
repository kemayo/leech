from dataclasses import dataclass
from typing import Optional
import logging
import attr
import datetime
import json
import re
import os.path
from . import register, Site
from _leech.chapter import Chapter
from _leech.story import Story

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


@dataclass
class SiteDefinition:
    url: str
    title: str
    author: str
    content_selector: str
    # If present, find something within `content` to use a chapter title; if not found, the link text to it will be used
    content_title_selector: Optional[str] = None
    # If present, find a specific element in the `content` to be the chapter text
    content_text_selector: Optional[str] = None
    # If present, it looks for chapters linked from `url`. If not, it assumes `url` points to a chapter.
    chapter_selector: Optional[str] = None
    # If present, use to find a link to the next content page (only used if not using chapter_selector)
    next_selector: Optional[str] = None
    # If present, use to filter out content that matches the selector
    filter_selector: Optional[str] = None
    cover_url: Optional[str] = None


@register
class Arbitrary(Site):
    """A way to describe an arbitrary side for a one-off fetch"""

    @staticmethod
    def matches(url):
        # e.g. practical1.json
        if url.endswith(".json") and os.path.isfile(url):
            return url

    @classmethod
    def create(cls, url, options):
        cached_site = cls.load_from_cache(url)
        if cached_site:
            return cached_site

        with open(url) as definition_file:
            definition = SiteDefinition(**json.load(definition_file))

        story = Story(
            url=url,
            title=definition.title,
            author=definition.author,
            cover_url=definition.cover_url,
        )

        return cls(story=story, options=options)

    def extract(self, session):
        url = self.story.url

        with open(url) as definition_file:
            definition = SiteDefinition(**json.load(definition_file))

        if definition.chapter_selector:
            soup = self._soup(session, definition.url)
            base = soup.head.base and soup.head.base.get("href") or False
            for chapter_link in soup.select(definition.chapter_selector):
                chapter_url = str(chapter_link.get("href"))
                if base:
                    chapter_url = self._join_url(base, chapter_url)
                chapter_url = self._join_url(definition.url, chapter_url)
                for chapter in self._chapter(
                    session,
                    chapter_url,
                    definition,
                    title=chapter_link.string,
                ):
                    self.story.add_chapter(chapter)
        elif definition.next_selector:
            # set of already processed urls. Stored to detect loops.
            found_content_urls = self.context.setdefault("found_content_urls", {})
            content_url: Optional[str] = self.context.setdefault(
                "content_url", definition.url
            )
            while content_url:
                if content_url not in found_content_urls:
                    for chapter in self._chapter(session, content_url, definition):
                        self.story.add_chapter(chapter)

                found_content_urls[content_url] = True

                soup = self._soup(session, content_url)
                base = soup.head.base and soup.head.base.get("href") or False
                next_link = soup.select(definition.next_selector)
                if not next_link:
                    break

                next_link_url = str(next_link[0].get("href"))
                if base:
                    next_link_url = self._join_url(base, next_link_url)

                content_url = self._join_url(content_url, next_link_url)
                self.context["content_url"] = content_url
        else:
            raise NotImplementedError()

        return self.story

    def _chapter(self, session, url: str, definition: SiteDefinition, title: str = ""):
        logger.info("Extracting chapter @ %s", url)
        soup = self._soup(session, url)

        if not soup.select(definition.content_selector):
            return

        # clean up a few things which will definitely break epubs:
        # TODO: expand this greatly, or make it configurable
        for namespaced in soup.find_all(re.compile(r"[a-z]+:[a-z]+")):
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
            content.name = "div"

            self._clean(content)

            yield Chapter(
                title=title,
                content=content.prettify(),
                # TODO: better date detection
                date=datetime.datetime.now().strftime("%Y-%m-%d"),
                number=self.chapter_count,
                url=url,
            )
            self.chapter_count += 1
