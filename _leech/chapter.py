from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import unicodedata


@dataclass
class Chapter:
    number: int
    title: str

    date: Optional[str] = None
    content: str = ""

    url: Optional[str] = None

    @classmethod
    def from_json(cls, json: dict) -> Chapter:
        return cls(
            number=json["number"],
            title=json["title"],
            date=json["date"],
            content=json["content"],
            url=json["url"],
        )

    def get_title(self, normalize=False) -> str:
        if normalize:
            return unicodedata.normalize("NFKC", self.title)
        return self.title

    def get_content(self, normalize=False) -> str:
        if normalize:
            return unicodedata.normalize("NFKC", self.content)
        return self.content
