"""Decide which sources are active based on configuration.

Real sources activate when their credentials/config are present. If none are
configured, we fall back to the keyless MockSource so the pipeline always runs.
"""

from __future__ import annotations

from loguru import logger as log

from .base import Source
from .mock import MockSource
from .newsapi import NewsApiSource
from .reddit import RedditSource
from .rss import RssSource


def get_enabled_sources(settings) -> list[Source]:
    sources: list[Source] = []

    if settings.reddit_client_id and settings.reddit_client_secret:
        sources.append(RedditSource(settings.reddit_client_id, settings.reddit_client_secret))
    if settings.newsapi_key:
        sources.append(NewsApiSource(settings.newsapi_key))
    feeds = [f.strip() for f in (settings.rss_feeds or "").split(",") if f.strip()]
    if feeds:
        sources.append(RssSource(feeds))

    if not sources:
        log.info("no real sources configured — using MockSource (keyless dev mode)")
        sources.append(MockSource(per_keyword=settings.mock_mentions_per_keyword))

    return sources
