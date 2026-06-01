"""Reddit source via PRAW (OAuth2 client credentials). Active only if creds are set.

PRAW is synchronous, so the blocking search runs in a worker thread.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from loguru import logger as log

from .base import RawMention, Source


class RedditSource(Source):
    name = "reddit"

    def __init__(self, client_id: str, client_secret: str, limit: int = 10) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.limit = limit

    def _fetch_sync(self, keyword: str) -> list[RawMention]:
        import praw

        reddit = praw.Reddit(
            client_id=self.client_id,
            client_secret=self.client_secret,
            user_agent="echoscope-ai/0.1 (mention-collector)",
            check_for_updates=False,
        )
        reddit.read_only = True
        out: list[RawMention] = []
        for s in reddit.subreddit("all").search(keyword, sort="new", limit=self.limit):
            out.append(
                RawMention(
                    source="reddit",
                    url=f"https://reddit.com{s.permalink}",
                    title=s.title,
                    content=(s.selftext or s.title or ""),
                    author=str(s.author) if s.author else None,
                    published_at=datetime.fromtimestamp(s.created_utc, tz=timezone.utc),
                    upvotes=int(s.score or 0),
                    comment_count=int(s.num_comments or 0),
                )
            )
        return out

    async def fetch(self, keyword: str) -> list[RawMention]:
        try:
            return await asyncio.to_thread(self._fetch_sync, keyword)
        except Exception:
            log.exception("reddit fetch failed", keyword=keyword)
            return []
