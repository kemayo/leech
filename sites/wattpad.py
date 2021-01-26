#!/usr/bin/python

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
        workid = re.match(r'^https?://(?:www\.)?wattpad\.com/story/(\d+)?.*', url).group(1)
        info = self.session.get(f"https://www.wattpad.com/api/v3/stories/{workid}").json()

        story = Section(
            title=info['title'],
            author=info['user']['name'],
            url=url,
            cover_url=info['cover']
        )

        for chapter in info['parts']:
            story.add(Chapter(
                title=chapter['title'],
                contents=self._chapter(chapter['id']),
                # "2020-05-03T22:14:29Z"
                date=datetime.datetime.fromisoformat(chapter['createDate'].rstrip('Z'))  # modifyDate also?
            ))

        return story

    def _chapter(self, chapterid):
        logger.info(f"Extracting chapter @ {chapterid}")
        api = self.session.get(f"https://www.wattpad.com/apiv2/storytext?id={chapterid}")
        return '<div>' + api.text + '</div>'
