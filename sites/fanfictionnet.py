#!/usr/bin/python

import logging
import datetime
import re
from . import register, Site, SiteException, Section, Chapter

logger = logging.getLogger(__name__)


@register
class FanFictionNet(Site):
    """FFN: it has a lot of stuff"""
    @staticmethod
    def matches(url):
        # e.g. https://www.fanfiction.net/s/4109686/3/Taking-Sights
        match = re.match(r'^https?://(?:www|m)\.fanfiction\.net/s/(\d+)/?.*', url)
        if match:
            return 'https://www.fanfiction.net/s/' + match.group(1) + '/'

    def extract(self, url):
        soup = self._soup(url)
        content = soup.find(id="content_wrapper_inner")
        if not content:
            raise SiteException("No content")

        metadata = content.find(id='profile_top')

        story = Section(
            title=str(metadata.find('b', class_="xcontrast_txt").string),
            author=str(metadata.find('a', class_="xcontrast_txt").string),
            url=url
        )

        dates = content.find_all('span', attrs={'data-xutime': True})
        published = False
        updated = False
        if len(dates) == 1:
            published = datetime.datetime.fromtimestamp(int(dates[0]['data-xutime']))
        elif len(dates) == 2:
            updated = datetime.datetime.fromtimestamp(int(dates[0]['data-xutime']))
            published = datetime.datetime.fromtimestamp(int(dates[1]['data-xutime']))

        chapter_select = content.find(id="chap_select")
        if chapter_select:
            base_url = re.search(r'(https?://[^/]+/s/\d+/?)', url)
            if not base_url:
                raise SiteException("Can't find base URL for chapters")
            base_url = base_url.group(0)

            # beautiful soup doesn't handle ffn's unclosed option tags at all well here
            options = re.findall(r'<option.+?value="?(\d+)"?[^>]*>([^<]+)', str(chapter_select))
            for option in options:
                story.add(Chapter(title=option[1], contents=self._chapter(base_url + option[0]), date=False))

            # fix up the dates
            story[-1].date = updated
            story[0].date = published
        else:
            story.add(Chapter(title=story.title, contents=self._chapter(url), date=published))

        return story

    def _chapter(self, url):
        logger.info("Fetching chapter @ %s", url)
        soup = self._soup(url)

        content = soup.find(id="content_wrapper_inner")
        if not content:
            raise SiteException("No chapter content")

        text = content.find(id="storytext")
        if not text:
            raise SiteException("No chapter content")

        # clean up some invalid xhtml attributes
        # TODO: be more selective about this somehow
        try:
            for tag in text.find_all(True):
                tag.attrs.clear()
        except Exception:
            logger.exception("Trouble cleaning attributes")

        return text.prettify()


@register
class FictionPress(FanFictionNet):
    @staticmethod
    def matches(url):
        # e.g. https://www.fictionpress.com/s/2961893/1/Mother-of-Learning
        match = re.match(r'^https?://(?:www|m)\.fictionpress\.com/s/(\d+)/?.*', url)
        if match:
            return 'https://www.fictionpress.com/s/' + match.group(1) + '/'
