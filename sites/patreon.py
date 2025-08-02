#!/usr/bin/python

import logging
import datetime
import re
from . import register, Site, Section, Chapter

logger = logging.getLogger(__name__)


@register
class Patreon(Site):
    @staticmethod
    def matches(url):
        # e.g. https://www.patreon.com/RavensDagger
        # e.g. https://www.patreon.com/c/RavensDagger/posts?filters[tag]=Save+Scumming
        if match := re.match(r'^(https?://(?:www\.)?patreon\.com/c/([^/]+))/?.*', url):
            return match.group(0)
        if match := re.match(r'^(https?://(?:www\.)?patreon\.com/([^/]+))/?.*', url):
            return match.group(0)

    def extract(self, url):
        response = self.session.get(url)
        # this is fragile:
        # "pageBootstrap":{"campaign":{"data":{"id":"2259814"
        campaign = re.search(r'"pageBootstrap":\{"campaign":\{"data":\{"id":"(\d+)"', response.text).group(1)
        author = re.search(r'"pageBootstrap":.+"name":"([^"]+)', response.text).group(1)
        title = author

        params = {
            # "json-api-version": "1.0",
            # "sort": "-published_at",
            "filter[campaign_id]": campaign,
        }

        tag_filter = None
        if match := re.search(r'filters\[tag\]=([^&]+)', url):
            params["filter[tag]"] = match.group(1)
            tag_filter = match.group(1).replace('+', ' ')
            title = tag_filter

        story = Section(
            title=title,
            author=author,
            url=url,
            # cover_url=
        )

        tags = set()

        while params:
            # print("params", params)
            response = self.session.get('https://www.patreon.com/api/posts', params=params).json()
            # print(response.keys())

            for post in response["data"]:
                # print(f"post {post["id"]}, {post["type"]}, {post["attributes"]["title"]}")
                # "url"
                # "created_at": "2025-08-01T10:11:10.000+00:00"
                # "published_at": "2025-08-01T10:12:33.000+00:00"
                # "content"
                # "is_paid"
                # "current_user_can_view"
                if "content" in post["attributes"]:
                    logger.info("Extracting chapter: %s", post["attributes"]["title"])
                    content = post["attributes"]["content"]
                elif "teaser_text" in post["attributes"]:
                    logger.warning("Extracting teaser chapter: %s", post["attributes"]["title"])
                    content = f'<p>{post["attributes"]["teaser_text"]}</p><p>[<a href="{post["attributes"]["url"]}">On Patreon</a>]</p>'
                else:
                    logger.warning("Skipped chapter, no content: %s", post["attributes"]["title"])
                    continue
                story.add(Chapter(
                    title=post["attributes"]["title"],
                    contents=content,
                    date=datetime.datetime.fromisoformat(post["attributes"]["published_at"]),
                    # url=post["attributes"]["url"]
                ))

                for tag in post.get("relationships", {}).get("user_defined_tags", {}).get("data", []):
                    tags.add(tag["id"].replace("user_defined;", ""))

            cursor = response.get("meta", {}).get("pagination", {}).get("cursors", {}).get("next")
            if cursor:
                params["page[cursor]"] = cursor
            else:
                params = False

        story.tags = [tag for tag in tags if tag != tag_filter]

        self._finalize(story)

        return story
