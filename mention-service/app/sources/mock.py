"""Mock source — generates fake mentions so the pipeline runs with zero API keys."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from faker import Faker

from .base import RawMention, Source

fake = Faker()


class MockSource(Source):
    name = "mock"

    def __init__(self, per_keyword: int = 5) -> None:
        self.per_keyword = per_keyword

    async def fetch(self, keyword: str) -> list[RawMention]:
        now = datetime.now(timezone.utc)
        out: list[RawMention] = []
        for _ in range(self.per_keyword):
            out.append(
                RawMention(
                    source="mock",
                    url=f"https://example.com/{uuid.uuid4().hex}",
                    title=f"{keyword}: {fake.sentence(nb_words=6)}",
                    content=f"{fake.paragraph(nb_sentences=3)} (mentions {keyword})",
                    author=fake.user_name(),
                    published_at=now - timedelta(minutes=fake.random_int(0, 1440)),
                    upvotes=fake.random_int(0, 2000),
                    comment_count=fake.random_int(0, 300),
                )
            )
        return out
