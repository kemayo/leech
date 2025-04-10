#!/usr/bin/python

import logging
import datetime
import re
import urllib.parse
import attr
from . import register, Site, SiteException, CloudflareException, Section, Chapter

logger = logging.getLogger(__name__)


@register
class FanFictionNet(Site):
    _cloudflared = attr.ib(init=False, default=False)

    """FFN: it has a lot of stuff"""
    @staticmethod
    def matches(url):
        # e.g. https://www.fanfiction.net/s/4109686/3/Taking-Sights
        match = re.match(r'^https?://(?:www|m)\.fanfiction\.net/s/(\d+)/?.*', url)
        if match:
            return 'https://www.fanfiction.net/s/' + match.group(1) + '/'

    def extract(self, url):
        soup, base = self._soup(url)

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

            suffix = re.search(r"'(/[^']+)';", chapter_select.attrs['onchange'])
            if not suffix:
                raise SiteException("Can't find URL suffix for chapters")
            suffix = suffix.group(1)

            # beautiful soup doesn't handle ffn's unclosed option tags at all well here
            options = re.findall(r'<option.+?value="?(\d+)"?[^>]*>([^<]+)', str(chapter_select))
            for option in options:
                story.add(Chapter(title=option[1], contents=self._chapter(base_url + option[0] + suffix), date=False))

            # fix up the dates
            story[-1].date = updated
            story[0].date = published
        else:
            story.add(Chapter(title=story.title, contents=self._chapter(url), date=published))

        self._finalize(story)

        return story

    def _chapter(self, url):
        logger.info("Fetching chapter @ %s", url)
        soup, base = self._soup(url)

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

        self._clean(text, base)

        return text.prettify()

    def _soup(self, url, *args, **kwargs):
        if self._cloudflared:
            fallback = f"https://archive.org/wayback/available?url={urllib.parse.quote(url)}"
            try:
                response = self.session.get(fallback)
                wayback = response.json()
                closest = wayback['archived_snapshots']['closest']['url']
                return super()._soup(closest, *args, delay=1, **kwargs)
            except Exception:
                self.session.cache.delete_url(fallback)
                raise CloudflareException("Couldn't fetch, presumably because of Cloudflare protection, and falling back to archive.org failed; if some chapters were succeeding, try again?", url, fallback)
        try:
            return super()._soup(self, url, *args, **kwargs)
        except CloudflareException:
            self._cloudflared = True
            return self._soup(url, *args, **kwargs)


@register
class FictionPress(FanFictionNet):
    @staticmethod
    def matches(url):
        # e.g. https://www.fictionpress.com/s/2961893/1/Mother-of-Learning
        match = re.match(r'^https?://(?:www|m)\.fictionpress\.com/s/(\d+)/?.*', url)
        if match:
            return 'https://www.fictionpress.com/s/' + match.group(1) + '/'
