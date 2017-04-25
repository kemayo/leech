#!/usr/bin/python

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


@register
class ArbitraryIndex(Site):
    """A way to describe an arbitrary side for a one-off fetch
    """
    @staticmethod
    def matches(url):
        # e.g. practical1.json
        if url.endswith('.json') and os.path.isfile(url):
            return url

    def extract(self, url):
        with open(url) as definition_file:
            definition = json.load(definition_file)

        soup = self._soup(definition['url'])

        story = Section(
            title=definition['title'],
            author=definition['author']
        )

        for chapter in soup.select(definition['chapter_selector']):
            chapter_url = str(chapter.get('href'))
            story.add(Chapter(
                title=chapter.string,
                contents=self._chapter(chapter_url, definition),
                # TODO: better date detection
                date=datetime.datetime.now()
            ))

        return story

    def _chapter(self, url, definition):
        print("Extracting chapter from", url)
        soup = self._soup(url)
        content = soup.select(definition['content_selector'])[0]

        if 'filter_selector' in definition:
            for filtered in content.select(definition['filter_selector']):
                filtered.decompose()

        return content.prettify()
