#!/usr/bin/python

import datetime
import logging

from . import register, Section, SiteException
from .xenforo import XenForo, XenForoIndex

logger = logging.getLogger(__name__)


class XenForo2(XenForo):
    def _base_story(self, soup):
        url = soup.find('meta', property='og:url').get('content')
        title = soup.select('h1.p-title-value')[0]
        # clean out informational bits from the title
        for tag in title.select('.labelLink,.label-append'):
            tag.decompose()
        tags = [tag.get_text().strip() for tag in soup.select('.tagList a.tagItem')]
        return Section(
            title=title.get_text().strip(),
            author=soup.find('div', class_='p-description').find('a', class_='username').get_text(),
            url=url,
            tags=tags
        )

    def _posts_from_page(self, soup, postid=False):
        if postid:
            return soup.find('article', id='js-post-' + postid)
        return soup.select('article.message--post')

    def _threadmark_title(self, post):
        # Get the title, removing "<strong>Threadmark:</strong>" which precedes it
        return post.find('span', class_='threadmarkLabel').get_text()

    def _chapter_contents(self, post):
        return post.find('div', class_='message-userContent')

    def _clean_spoilers(self, post, chapterid):
        # spoilers don't work well, so turn them into epub footnotes
        for spoiler in post.find_all(class_='bbCodeSpoiler'):
            spoiler_title = spoiler.find(class_='bbCodeSpoiler-button-title')
            if self.options['skip_spoilers']:
                link = self._footnote(spoiler.find(class_='bbCodeBlock-content').extract(), chapterid)
                if spoiler_title:
                    link.string = spoiler_title.get_text()
            else:
                if spoiler_title:
                    link = f'[SPOILER: {spoiler_title.get_text()}]'
                else:
                    link = '[SPOILER]'
            new_spoiler = self._new_tag('div', class_="leech-spoiler")
            new_spoiler.append(link)
            spoiler.replace_with(new_spoiler)

    def _post_date(self, post):
        if post.find('time'):
            return datetime.datetime.fromtimestamp(int(post.find('time').get('data-time')))
        raise SiteException("No date")


@register
class SpaceBattles(XenForo2):
    domain = 'forums.spacebattles.com'


@register
class SpaceBattlesIndex(SpaceBattles, XenForoIndex):
    _key = "SpaceBattles"


@register
class SufficientVelocity(XenForo2):
    domain = 'forums.sufficientvelocity.com'


@register
class TheSietch(XenForo2):
    domain = 'www.the-sietch.com'
    index_urls = True


@register
class QuestionableQuesting(XenForo2):
    domain = 'forum.questionablequesting.com'


@register
class QuestionableQuestingIndex(QuestionableQuesting, XenForoIndex):
    _key = "QuestionableQuesting"
