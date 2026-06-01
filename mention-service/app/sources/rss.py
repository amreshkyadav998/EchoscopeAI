"""RSS/blog source via feedparser. Active only if RSS_FEEDS is configured (keyless).

feedparser is synchronous, so parsing runs in a worker thread.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from loguru import logger as log

from .base import RawMention, Source


class RssSource(Source):
    name = "rss"

    def __init__(self, feeds: list[str], per_feed: int = 20) -> None:
        self.feeds = feeds
        self.per_feed = per_feed

    def _fetch_sync(self, keyword: str) -> list[RawMention]:
        import feedparser

        kw = keyword.lower()
        out: list[RawMention] = []
        for feed_url in self.feeds:
            parsed = feedparser.parse(feed_url)
            for entry in parsed.entries[: self.per_feed]:
                title = entry.get("title", "")
                summary = entry.get("summary", "")
                if kw not in f"{title} {summary}".lower():
                    continue
                link = entry.get("link")
                if not link:
                    continue
                out.append(
                    RawMention(
                        source="rss",
                        url=link,
                        title=title,
                        content=summary or title,
                        author=entry.get("author"),
                        published_at=_entry_time(entry),
                    )
                )
        return out

    async def fetch(self, keyword: str) -> list[RawMention]:
        try:
            return await asyncio.to_thread(self._fetch_sync, keyword)
        except Exception:
            log.exception("rss fetch failed", keyword=keyword)
            return []


def _entry_time(entry) -> datetime:
    import time

    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        return datetime.fromtimestamp(time.mktime(parsed), tz=timezone.utc)
    return datetime.now(timezone.utc)
