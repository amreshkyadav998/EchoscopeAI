"""Redis: analytics cache-aside (5-min TTL), hourly counters, cache invalidation."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Awaitable, Callable
from typing import Any

import redis.asyncio as aioredis

from config import get_settings

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


def _key(org_id: str, endpoint: str, params: dict[str, Any]) -> str:
    digest = hashlib.sha256(json.dumps(params, sort_keys=True, default=str).encode()).hexdigest()[:16]
    return f"analytics:{org_id}:{endpoint}:{digest}"


async def cache_aside(
    org_id: str, endpoint: str, params: dict[str, Any], ttl: int, compute: Callable[[], Awaitable[Any]]
) -> Any:
    redis = ensure_redis(get_settings().redis_url)
    key = _key(org_id, endpoint, params)
    cached = await redis.get(key)
    if cached is not None:
        return json.loads(cached)
    value = await compute()
    await redis.set(key, json.dumps(value, default=str), ex=ttl)
    return value


async def invalidate_org(org_id: str) -> int:
    """Delete all cached analytics for an org (called on analytics-updated)."""
    redis = get_redis()
    deleted = 0
    async for k in redis.scan_iter(match=f"analytics:{org_id}:*"):
        await redis.delete(k)
        deleted += 1
    return deleted


async def incr_hourly_counter(org_id: str, hour_bucket: str) -> int:
    redis = get_redis()
    key = f"mention:count:{org_id}:{hour_bucket}"
    n = await redis.incr(key)
    if n == 1:
        await redis.expire(key, 48 * 3600)
    return n
