#!/usr/bin/python

import logging
import datetime
import re
from . import register, Site, SiteException, Section, Chapter

logger = logging.getLogger(__name__)


@register
class Stash(Site):
    @staticmethod
    def matches(url):
        # Need a stack page
        match = re.match(r'^(https?://sta\.sh/2.+)/?.*', url)
        if match:
            return match.group(1) + '/'

    def extract(self, url):
        soup = self._soup(url)
        content = soup.find(id="stash-body")
        if not content:
            return

        # metadata = content.find(id='profile_top')
        story = Section(
            title=str(soup.find(class_="stash-folder-name").h2.string),
            author=str(soup.find('span', class_="oh-stashlogo-name").string).rstrip("'s"),
            url=url
        )

        thumbs = content.select(".stash-folder-stream .thumb")
        if not thumbs:
            return
        for thumb in thumbs:
            try:
                if thumb['href'] != '#':
                    story.add(self._chapter(thumb['href']))
            except Exception:
                logger.exception("Couldn't extract chapters from thumbs")

        return story

    def _chapter(self, url):
        logger.info("Fetching chapter @ %s", url)
        soup = self._soup(url)

        content = soup.find(class_="journal-wrapper")
        if not content:
            raise SiteException("No content")

        title = str(content.find(class_="gr-top").find(class_='metadata').h2.a.string)

        text = content.find(class_="text")

        # clean up some invalid xhtml attributes
        # TODO: be more selective about this somehow
        try:
            for tag in text.find_all(True):
                tag.attrs = None
        except Exception as e:
            raise SiteException("Trouble cleaning attributes", e)

        self._clean(text)

        return Chapter(title=title, contents=text.prettify(), date=self._date(soup))

    def _date(self, soup):
        maybe_date = soup.find('div', class_="dev-metainfo-details").find('span', ts=True)
        return datetime.datetime.fromtimestamp(int(maybe_date['ts']))
