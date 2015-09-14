#!/usr/bin/python

import re
from . import register, Site, SiteException


@register
class FanFictionNet(Site):
    """FFN: it has a lot of stuff"""
    @staticmethod
    def matches(url):
        # e.g. https://www.fanfiction.net/s/4109686/3/Taking-Sights
        return re.match(r'^https?://www\.fanfiction\.net/s/\d+/?.*', url)

    def extract(self, url):
        soup = self._soup(url)
        content = soup.find(id="content_wrapper_inner")
        if not content:
            raise SiteException("No content")

        story = {}
        chapters = []

        metadata = content.find(id='profile_top')
        story['title'] = str(metadata.find('b', class_="xcontrast_txt").string)
        story['author'] = str(metadata.find('a', class_="xcontrast_txt").string)

        chapter_select = content.find(id="chap_select")
        if chapter_select:
            base_url = re.search(r'(https?://[^/]+/s/\d+/?)', url)
            if not base_url:
                raise SiteException("Can't find base URL for chapters")
            base_url = base_url.group(0)

            # beautiful soup doesn't handle ffn's unclosed option tags at all well here
            options = re.findall(r'<option.+?value="?(\d+)"?[^>]*>([^<]+)', str(chapter_select))
            for option in options:
                chapters.append((option[1], self._chapter(base_url + option[0])))
        else:
            chapters.append((story['title'], self._extract_chapter(url)))

        story['chapters'] = chapters

        return story

    def _chapter(self, url):
        print("Extracting chapter from", url)
        soup = self._soup(url)

        content = soup.find(id="content_wrapper_inner")
        if not content:
            raise SiteException("No chapter content")

        text = content.find(id="storytext")

        # clean up some invalid xhtml attributes
        # TODO: be more selective about this somehow
        try:
            for tag in text.find_all(True):
                tag.attrs = None
        except Exception as e:
            print("Trouble cleaning attributes", e)

        return text.prettify()
