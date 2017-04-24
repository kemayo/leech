#!/usr/bin/python

import datetime
import re
from . import register, Site, Section, Chapter


# TODO: implement a plain "Arbitrary" class, which only fetches a single
# page's content. This is mainly held up on needing to refactor `matches`
# slightly, so it can check whether arguments are present. (The noticeable
# difference would be whether a `--toc` arg was given.)

# TODO: let this be specified in some sort of JSON file, for works I'll want
# to repeatedly leech.

# Example command lines:
# ./leech.py arbitrary:https://practicalguidetoevil.wordpress.com/table-of-contents/ --author=erraticerrata --title="A Practical Guide To Evil: Book 1" --toc="#main .entry-content > ul > li > a" --content="#main .entry-content"
# ./leech.py arbitrary:https:./leech.py arbitrary:https://practicalguidetoevil.wordpress.com/table-of-contents/ --author=erraticerrata --title="A Practical Guide To Evil: Book 2" --toc="#main .entry-content > ul > ul > li > a" --content="#main .entry-content"


@register
class ArbitraryIndex(Site):
    """A way to describe an arbitrary side for a one-off fetch

    The assumption is that you will provide the URL for a table of contents, and
    separate required arguments for selectors for (a) the links to pages, and (b)
    the content on those pages.
    """
    @staticmethod
    def matches(url):
        # e.g. arbitrary:http://foo.bar/works/5683105/chapters/13092007
        match = re.match(r'^arbitrary:(https?://.+)', url)
        if match:
            return match.group(1)

    def _add_arguments(self, parser):
        parser.add_argument('--title', dest='title', required=True)
        parser.add_argument('--author', dest='author', required=True)
        parser.add_argument('--toc', dest='toc_selector', required=True)
        parser.add_argument('--content', dest='content_selector', required=True)

    def extract(self, url):
        soup = self._soup(url)

        story = Section(
            title=self.options.title,
            author=self.options.author
        )

        for chapter in soup.select(self.options.toc_selector):
            chapter_url = str(chapter.get('href'))
            story.add(Chapter(
                title=chapter.string,
                contents=self._chapter(chapter_url),
                date=datetime.datetime.now()
            ))

        return story

    def _chapter(self, url):
        print("Extracting chapter from", url)
        soup = self._soup(url)
        content = soup.select(self.options.content_selector)[0]

        # TODO: cleanup content here, via options?

        return content.prettify()
