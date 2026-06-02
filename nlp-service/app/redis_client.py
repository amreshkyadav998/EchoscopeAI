"""Redis client + GPT-summary cache (HLD §8: nlp:summary:{mention_id})."""

from __future__ import annotations

import redis.asyncio as aioredis

_client: aioredis.Redis | None = None


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
    global _client
    if _client is None:
        init_redis(url)
    return _client


def get_redis() -> aioredis.Redis:
    if _client is None:
        raise RuntimeError("Redis client not initialised")
    return _client


async def cache_summary(mention_id: str, summary: str, ttl: int) -> None:
    await get_redis().set(f"nlp:summary:{mention_id}", summary, ex=ttl)


async def get_cached_summary(mention_id: str) -> str | None:
    return await get_redis().get(f"nlp:summary:{mention_id}")
