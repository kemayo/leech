#!/usr/bin/python

import attr
import datetime
import json
import os.path
from . import register, Site, Section, Chapter

"""
Example JSON:
{
    "url": "https://practicalguidetoevil.wordpress.com/table-of-contents/",
    "title": "A Practical Guide To Evil: Book 1",
    "author": "erraticerrata",
    "chapter_selector": "#main .entry-content > ul > li > a",
    "content_selector": "#main .entry-content",
    "filter_selector": ".sharedaddy, .wpcnt, style"
}

TODO: implement a plain "Arbitrary" class, which only fetches a single
page's content. This is mainly held up on needing to refactor `matches`
slightly, so it can check whether arguments are present. (The noticeable
difference would be whether a `--toc` arg was given.)

"""


@attr.s
class SiteDefinition:
    url = attr.ib()
    title = attr.ib()
    author = attr.ib()
    content_selector = attr.ib()
    # If this is present, it looks for chapters linked from `url`. If not, it assumes `url` points to a chapter.
    chapter_selector = attr.ib(default=False)
    # If this is present, it's used to filter out content that matches the selector
    filter_selector = attr.ib(default=False)


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
            author=definition.author
        )

        if definition.chapter_selector:
            soup = self._soup(definition.url)
            for chapter in soup.select(definition.chapter_selector):
                chapter_url = str(chapter.get('href'))
                story.add(Chapter(
                    title=chapter.string,
                    contents=self._chapter(chapter_url, definition),
                    # TODO: better date detection
                    date=datetime.datetime.now()
                ))
        else:
            story.add(Chapter(
                title=definition.title,
                contents=self._chapter(definition.url, definition),
                # TODO: better date detection
                date=datetime.datetime.now()
            ))

        return story

    def _chapter(self, url, definition):
        # TODO: refactor so this can meaningfully handle multiple matches on content_selector.
        # Probably by changing it so that this returns a Chapter / Section.
        print("Extracting chapter from", url)
        soup = self._soup(url)
        content = soup.select(definition.content_selector)[0]

        if definition.filter_selector:
            for filtered in content.select(definition.filter_selector):
                filtered.decompose()

        return content.prettify()
