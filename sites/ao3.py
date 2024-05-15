#!/usr/bin/python

import logging
import datetime
import re
import requests_cache
from bs4 import BeautifulSoup
from . import register, Site, Section, Chapter, SiteException

logger = logging.getLogger(__name__)


@register
class ArchiveOfOurOwn(Site):
    """Archive of Our Own: it has its own epub export, but the formatting is awful"""
    @staticmethod
    def matches(url):
        # e.g. http://archiveofourown.org/works/5683105/chapters/13092007
        match = re.match(r'^(https?://(?:www\.)?archiveofourown\.org/works/\d+)/?.*', url)
        if match:
            return match.group(1) + '/'

    def login(self, login_details):
        with requests_cache.disabled():
            login = self.session.get('https://archiveofourown.org/users/login')
            soup = BeautifulSoup(login.text, 'html5lib')
            post, action, method = self._form_data(soup.find(id='new_user'))
            post['user[login]'] = login_details[0]
            post['user[password]'] = login_details[1]
            # I feel the session *should* handle this cookies bit for me. But
            # it doesn't. And I don't know why.
            result = self.session.post(
                self._join_url(login.url, action),
                data=post, cookies=login.cookies
            )
            if result.ok:
                logger.info("Logged in as %s", login_details[0])
            else:
                logger.error("Failed to log in as %s", login_details[0])

    def extract(self, url):
        workid = re.match(r'^https?://(?:www\.)?archiveofourown\.org/works/(\d+)/?.*', url).group(1)
        return self._extract_work(workid)

    def _extract_work(self, workid):
        # Fetch the full work
        url = f'http://archiveofourown.org/works/{workid}?view_adult=true&view_full_work=true'
        logger.info("Extracting full work @ %s", url)
        soup = self._soup(url)

        if not soup.find(id='workskin'):
            raise SiteException("Can't find the story text; you may need to log in or flush the cache")

        story = Section(
            title=soup.select('#workskin > .preface .title')[0].text.strip(),
            author=soup.select('#workskin .preface .byline a')[0].text.strip(),
            summary=soup.select('#workskin .preface .summary blockquote')[0].prettify(),
            url=f'http://archiveofourown.org/works/{workid}',
            tags=[tag.get_text().strip() for tag in soup.select('.work.meta .tags a.tag')]
        )

        # Fetch the chapter list as well because it contains info that's not in the full work
        nav_soup = self._soup(f'https://archiveofourown.org/works/{workid}/navigate')
        chapters = soup.select('#chapters > div')
        if len(chapters) == 1:
            # in a single-chapter story the #chapters div is actually the chapter
            chapters = [soup.find(id='chapters').parent]

        for index, chapter in enumerate(nav_soup.select('#main ol[role="navigation"] li')):
            link = chapter.find('a')
            logger.info("Extracting chapter %s", link.string)

            updated = datetime.datetime.strptime(
                chapter.find('span', class_='datetime').string,
                "(%Y-%m-%d)"
            )

            chapter_soup = chapters[index]
            if not chapter_soup:
                logger.warning("Couldn't find chapter %s in full work", index + 1)
                continue

            story.add(Chapter(
                title=link.string,
                # the `or soup` fallback covers single-chapter works
                contents=self._chapter(chapter_soup),
                date=updated
            ))

        return story

    def _chapter(self, soup):
        content = soup.find('div', role='article')

        for landmark in content.find_all(class_='landmark'):
            landmark.decompose()

        # TODO: Maybe these should be footnotes instead?
        notes = soup.select('#chapters .end.notes')
        if notes:
            notes = notes[0]
            for landmark in notes.find_all(class_='landmark'):
                landmark.decompose()

        self._clean(content)

        return content.prettify() + (notes and notes.prettify() or '')


@register
class ArchiveOfOurOwnSeries(ArchiveOfOurOwn):
    _key = "ArchiveOfOurOwn"

    @staticmethod
    def matches(url):
        # e.g. http://archiveofourown.org/series/5683105/
        match = re.match(r'^(https?://archiveofourown\.org/series/\d+)/?.*', url)
        if match:
            return match.group(1) + '/'

    def extract(self, url):
        seriesid = re.match(r'^https?://archiveofourown\.org/series/(\d+)/?.*', url).group(1)

        soup = self._soup(f'http://archiveofourown.org/series/{seriesid}?view_adult=true')

        story = Section(
            title=soup.select('#main h2.heading')[0].text.strip(),
            author=soup.select('#main dl.series.meta a[rel="author"]')[0].string,
            url=f'http://archiveofourown.org/series/{seriesid}'
        )

        for work in soup.select('#main ul.series li.work'):
            workid = work.get('id').replace('work_', '')
            substory = self._extract_work(workid)

            # TODO: improve epub-writer to be able to generate a toc.ncx with nested headings
            story.add(substory)

        return story
