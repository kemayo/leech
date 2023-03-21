from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from _leech.chapter import Chapter


@dataclass
class Story:
    title: str
    author: str
    url: str

    chapters: List[Chapter] = field(default_factory=list)

    cover_url: Optional[str] = None
    summary: Optional[str] = None
    footnotes: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    @classmethod
    def from_json(cls, json: dict) -> Story:
        return cls(
            title=json["title"],
            author=json["author"],
            url=json["url"],
            chapters=[Chapter.from_json(c) for c in json["chapters"]],
            cover_url=json["cover_url"],
            summary=json["summary"],
            footnotes=json["footnotes"],
            tags=json["tags"],
        )

    def add_chapter(self, chapter: Chapter):
        self.chapters.append(chapter)

    def dates(self) -> List[str]:
        return [chapter.date for chapter in self.chapters if chapter.date]

    @property
    def metadata(self):
        dates = self.dates()
        metadata = {
            "title": self.title,
            "author": self.author,
            "unique_id": self.url,
            "started": min(dates),
            "updated": max(dates),
            "extra": "",
        }

        extra_metadata = {}
        if self.summary:
            extra_metadata["Summary"] = self.summary
        if self.tags:
            extra_metadata["Tags"] = ", ".join(self.tags)

        if extra_metadata:
            metadata["extra"] = "\n        ".join(
                f"<dt>{k}</dt><dd>{v}</dd>" for k, v in extra_metadata.items()
            )
        return metadata
