#!/usr/bin/python

import datetime
import re
from . import register, Site, Section, Chapter


@register
class ArchiveOfOurOwn(Site):
    """Archive of Our Own: it has its own epub export, but the formatting is awful"""
    @staticmethod
    def matches(url):
        # e.g. http://archiveofourown.org/works/5683105/chapters/13092007
        match = re.match(r'^(https?://archiveofourown\.org/works/\d+)/?.*', url)
        if match:
            return match.group(1) + '/'

    def extract(self, url):
        workid = re.match(r'^https?://archiveofourown\.org/works/(\d+)/?.*', url).group(1)
        return self._extract_work(workid)

    def _extract_work(self, workid):
        soup = self._soup('http://archiveofourown.org/works/{}/navigate?view_adult=true'.format(workid))

        metadata = soup.select('#main h2.heading a')
        story = Section(
            title=metadata[0].string,
            author=metadata[1].string,
            url='http://archiveofourown.org/works/{}'.format(workid)
        )

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

            story.add(Chapter(title=link.string, contents=self._chapter(chapter_url), date=updated))

        return story

    def _chapter(self, url):
        print("Extracting chapter from", url)
        soup = self._soup(url)
        content = soup.find('div', role='article')

        for landmark in content.find_all(class_='landmark'):
            landmark.decompose()

        # TODO: Maybe these should be footnotes instead?
        notes = soup.select('#chapters .end.notes')
        if notes:
            notes = notes[0]
            for landmark in notes.find_all(class_='landmark'):
                landmark.decompose()

        return content.prettify() + (notes and notes.prettify() or '')


@register
class ArchiveOfOurOwnSeries(ArchiveOfOurOwn):
    @staticmethod
    def matches(url):
        # e.g. http://archiveofourown.org/series/5683105/
        match = re.match(r'^(https?://archiveofourown\.org/series/\d+)/?.*', url)
        if match:
            return match.group(1) + '/'

    def extract(self, url):
        seriesid = re.match(r'^https?://archiveofourown\.org/series/(\d+)/?.*', url).group(1)

        soup = self._soup('http://archiveofourown.org/series/{}?view_adult=true'.format(seriesid))

        story = Section(
            title=soup.select('#main h2.heading')[0].string,
            author=soup.select('#main dl.series.meta a[rel="author"]')[0].string
        )

        for work in soup.select('#main ul.series li.work'):
            workid = work.get('id').replace('work_', '')
            substory = self._extract_work(workid)

            # TODO: improve epub-writer to be able to generate a toc.ncx with nested headings
            story.add(substory)

        return story
