"""Async Redis client lifecycle for the gateway.

A single connection pool is opened at startup (lifespan) and closed at shutdown.
Used by the rate-limiter (and future gateway features).
"""

from __future__ import annotations

import redis.asyncio as aioredis

_client: aioredis.Redis | None = None


def init_redis(url: str) -> aioredis.Redis:
    """Create the global Redis client from a connection URL."""
    global _client
    _client = aioredis.from_url(url, encoding="utf-8", decode_responses=True)
    return _client


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def get_redis() -> aioredis.Redis:
    if _client is None:
        raise RuntimeError("Redis client not initialised (call init_redis in lifespan)")
    return _client
