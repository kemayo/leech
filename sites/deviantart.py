#!/usr/bin/python

import logging
import re

from . import register, Section
from .stash import Stash

logger = logging.getLogger(__name__)


@register
class DeviantArt(Stash):
    @staticmethod
    def matches(url):
        # Need a collection page
        match = re.match(r'^https?://[^.]+\.deviantart\.com/(?:gallery|favourites)/\d+/?', url)
        if match:
            return match.group(0) + '/'

    def extract(self, url):
        soup = self._soup(url)
        content = soup.find(id="output")
        if not content:
            return

        if "gallery" in url:
            author = str(content.select('h1 a.u')[0].string)
        else:
            authors = set(str(author.string) for author in content.select('.stream .details a.u'))
            author = ', '.join(authors)

        story = Section(
            title=str(content.find(class_="folder-title").string),
            author=author,
            url=url
        )

        thumbs = content.select(".stream a.thumb")
        if not thumbs:
            return
        for thumb in thumbs:
            try:
                if thumb['href'] is not '#':
                    story.add(self._chapter(thumb['href']))
            except Exception as e:
                logger.exception("Couldn't extract chapters from thumbs")

        return story
