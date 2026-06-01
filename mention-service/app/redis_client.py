"""Redis: URL-hash deduplication and per-keyword distributed scrape lock (HLD §8)."""

from __future__ import annotations

import hashlib

import redis.asyncio as aioredis

_client: aioredis.Redis | None = None

DEDUP_TTL_SECONDS = 24 * 3600
SCRAPE_LOCK_TTL_SECONDS = 600  # 10 min


def init_redis(url: str) -> aioredis.Redis:
    global _client
    _client = aioredis.from_url(url, encoding="utf-8", decode_responses=True)
    return _client


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def ensure_redis(url: str) -> aioredis.Redis:
    """Initialise the client if needed (used by the Celery worker / pipeline process)."""
    global _client
    if _client is None:
        init_redis(url)
    return _client


def get_redis() -> aioredis.Redis:
    if _client is None:
        raise RuntimeError("Redis client not initialised")
    return _client


async def claim_url(source_url: str) -> bool:
    """Reserve a URL for ingestion. Returns True if NEW, False if already seen (duplicate).

    Uses SET NX EX on dedup:{sha256(url)} with a 24h TTL.
    """
    digest = hashlib.sha256(source_url.encode()).hexdigest()
    was_set = await get_redis().set(f"dedup:{digest}", "1", nx=True, ex=DEDUP_TTL_SECONDS)
    return bool(was_set)


async def acquire_scrape_lock(keyword_id: str) -> bool:
    """Acquire a per-keyword scrape lock (prevents parallel duplicate jobs)."""
    was_set = await get_redis().set(
        f"scrape:lock:{keyword_id}", "1", nx=True, ex=SCRAPE_LOCK_TTL_SECONDS
    )
    return bool(was_set)


async def release_scrape_lock(keyword_id: str) -> None:
    await get_redis().delete(f"scrape:lock:{keyword_id}")
