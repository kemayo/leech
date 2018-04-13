#!/usr/bin/python

import logging
import itertools
import datetime
import re
from . import register, Site, Section, Chapter

logger = logging.getLogger(__name__)


@register
class FictionLive(Site):
    """fiction.live: it's... mostly smut, I think? Terrible smut. But, hey, I had a rec to follow."""
    @staticmethod
    def matches(url):
        # e.g. https://fiction.live/stories/Descendant-of-a-Demon-Lord/SBBA49fQavNQMWxFT
        match = re.match(r'^(https?://fiction\.live/stories/[^\/]+/[0-9a-zA-Z]+)/?.*', url)
        if match:
            return match.group(1)

    def extract(self, url):
        workid = re.match(r'^https?://fiction\.live/stories/[^\/]+/([0-9a-zA-Z]+)/?.*', url).group(1)

        response = self.session.get('https://fiction.live/api/node/{}'.format(workid)).json()

        story = Section(
            title=response['t'],
            author=response['u'][0]['n'],
            # Could normalize the URL here from the returns, but I'd have to
            # go look up how they handle special characters in titles...
            url=url
        )
        # There's a summary (or similar) in `d` and `b`, if I want to use that later.

        # TODO: extract these #special ones and send them off to an endnotes section?
        chapters = ({'ct': 0},) + tuple(c for c in response['bm'] if not c['title'].startswith('#special')) + ({'ct': 9999999999999999},)

        for prevc, currc, nextc in contextiterate(chapters):
            # `id`, `title`, `ct`, `isFirst`
            # https://fiction.live/api/anonkun/chapters/SBBA49fQavNQMWxFT/0/1448245168594
            # https://fiction.live/api/anonkun/chapters/SBBA49fQavNQMWxFT/1449266444062/1449615394752
            # https://fiction.live/api/anonkun/chapters/SBBA49fQavNQMWxFT/1502823848216/9999999999999998
            # i.e. format is [current timestamp] / [next timestamp - 1]
            chapter_url = 'https://fiction.live/api/anonkun/chapters/{}/{}/{}'.format(workid, currc['ct'], nextc['ct'] - 1)
            logger.info("Extracting chapter \"%s\" @ %s", currc['title'], chapter_url)
            data = self.session.get(chapter_url).json()
            html = []

            updated = currc['ct']
            for segment in (d for d in data if not d.get('t', '').startswith('#special')):
                updated = max(updated, segment['ct'])
                # TODO: work out if this is actually enough types handled
                # There's at least also a reader post type, which mostly seems to be used for die rolls.
                if segment['nt'] == 'chapter':
                    html.extend(('<div>', segment['b'].replace('<br>', '<br/>'), '</div>'))
                elif segment['nt'] == 'choice':
                    votes = {}
                    for vote in segment['votes']:
                        votechoices = segment['votes'][vote]
                        if type(votechoices) == int:
                            votechoices = (votechoices,)
                        for choice in votechoices:
                            choice = segment['choices'][int(choice)]
                            votes[choice] = votes.get(choice, 0) + 1
                    choices = [(votes[v], v) for v in votes]
                    choices.sort(reverse=True)
                    html.append('<hr/><ul>')
                    for votecount, choice in choices:
                        html.append('<li>{}: {}</li>'.format(choice, votecount))
                    html.append('</ul><hr/>')

            story.add(Chapter(
                title=currc['title'],
                contents='\n'.join(html),
                date=datetime.datetime.fromtimestamp(updated / 1000.0)
            ))

        return story


# Stolen from the itertools docs
def contextiterate(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b, c = itertools.tee(iterable, 3)
    next(b, None)
    next(c, None)
    next(c, None)
    return zip(a, b, c)
