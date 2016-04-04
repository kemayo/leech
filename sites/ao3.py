#!/usr/bin/python

import datetime
import re
from . import register, Site, SiteException


@register
class ArchiveOfOurOwn(Site):
    """Archive of Our Own: it has its own epub export, but the formatting is awful"""
    @staticmethod
    def matches(url):
        # e.g. http://archiveofourown.org/works/5683105/chapters/13092007
        return re.match(r'^https?://archiveofourown\.org/works/\d+/?.*', url)

    def extract(self, url):
        workid = re.match(r'^https?://archiveofourown\.org/works/(\d+)/?.*', url).group(1)

        soup = self._soup('http://archiveofourown.org/works/{}/navigate?view_adult=true'.format(workid))

        metadata = soup.select('#main h2.heading a')
        story = {
            'title': metadata[0].string,
            'author': metadata[1].string,
        }

        chapters = []
        for chapter in soup.select('#main ol[role="navigation"] li'):
            link = chapter.find('a')
            chapter_url = str(link.get('href'))
            if chapter_url.startswith('/works/'):
                chapter_url = 'http://archiveofourown.org' + chapter_url
            chapter_url += '?view_adult=true'

            updated = datetime.datetime.strptime(
                chapter.find('span', class_='datetime').string,
                "(%Y-%m-%d)"
            )

            chapters.append((link.string, self._chapter(chapter_url), updated))

        if not chapters:
            raise SiteException("No content")

        story['chapters'] = chapters

        return story

    def _chapter(self, url):
        print("Extracting chapter from", url)
        soup = self._soup(url)
        content = soup.find('div', role='article')

        for landmark in content.find_all(class_='landmark'):
            landmark.decompose()

        return content.prettify()
