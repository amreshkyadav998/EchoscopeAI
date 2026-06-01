"""Source interface and the raw-mention data shape every source returns."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class RawMention:
    source: str  # reddit | news | rss | mock
    url: str
    content: str
    title: str | None = None
    author: str | None = None
    published_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    upvotes: int = 0
    comment_count: int = 0


class Source(ABC):
    name: str

    @abstractmethod
    async def fetch(self, keyword: str) -> list[RawMention]:
        """Return raw mentions matching the keyword (may be empty)."""
