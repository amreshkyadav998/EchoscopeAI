"""NewsAPI source (/everything endpoint). Active only if NEWSAPI_KEY is set."""

from __future__ import annotations

from datetime import datetime

import httpx
from loguru import logger as log

from .base import RawMention, Source


class NewsApiSource(Source):
    name = "news"

    def __init__(self, api_key: str, page_size: int = 10) -> None:
        self.api_key = api_key
        self.page_size = page_size

    async def fetch(self, keyword: str) -> list[RawMention]:
        out: list[RawMention] = []
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    "https://newsapi.org/v2/everything",
                    params={
                        "q": keyword,
                        "sortBy": "publishedAt",
                        "language": "en",
                        "pageSize": self.page_size,
                        "apiKey": self.api_key,
                    },
                )
                resp.raise_for_status()
                for a in resp.json().get("articles", []):
                    if not a.get("url"):
                        continue
                    out.append(
                        RawMention(
                            source="news",
                            url=a["url"],
                            title=a.get("title"),
                            content=a.get("content") or a.get("description") or "",
                            author=a.get("author"),
                            published_at=_parse(a.get("publishedAt")),
                        )
                    )
        except Exception:
            log.exception("newsapi fetch failed", keyword=keyword)
        return out


def _parse(value: str | None) -> datetime:
    from datetime import timezone

    if not value:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)
