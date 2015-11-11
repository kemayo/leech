#!/usr/bin/python

import datetime
import re
from . import register, Site, SiteException


@register
class Stash(Site):
    @staticmethod
    def matches(url):
        # Need a stack page
        return re.match(r'^https?://sta\.sh/2.+/?.*', url)

    def extract(self, url):
        soup = self._soup(url)
        content = soup.find(id="stash-body")
        if not content:
            return

        story = {}
        chapters = []

        # metadata = content.find(id='profile_top')
        story['title'] = str(soup.find(class_="stash-folder-name").h2.string)
        story['author'] = str(soup.find('span', class_="oh-stashlogo-name").string).rstrip("'s")

        thumbs = content.select(".stash-folder-stream .thumb")
        if not thumbs:
            return
        for thumb in thumbs:
            try:
                if thumb['href'] is not '#':
                    chapters.append(self._chapter(thumb['href']))
            except Exception as e:
                print(e)

        story['chapters'] = chapters

        return story

    def _chapter(self, url):
        print("Extracting chapter from", url)
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

        return (title, text.prettify(), self._date(soup))

    def _date(self, soup):
        maybe_date = soup.find('div', class_="dev-metainfo-details").find('span', ts=True)
        return datetime.datetime.fromtimestamp(int(maybe_date['ts']))
