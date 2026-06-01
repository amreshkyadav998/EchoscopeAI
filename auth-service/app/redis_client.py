"""Redis-backed refresh-token store and access-token blacklist (HLD section 8).

- refresh:{token}  -> HASH {user_id, created_at}, TTL = REFRESH_EXPIRE_DAYS
- blacklist:{jti}  -> STRING "1", TTL = remaining access-token lifetime
"""

from __future__ import annotations

from datetime import datetime, timezone

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


def get_redis() -> aioredis.Redis:
    if _client is None:
        raise RuntimeError("Redis client not initialised")
    return _client


# ── refresh tokens ──
async def store_refresh_token(token: str, user_id: str, ttl_days: int) -> None:
    redis = get_redis()
    key = f"refresh:{token}"
    await redis.hset(
        key,
        mapping={"user_id": user_id, "created_at": datetime.now(timezone.utc).isoformat()},
    )
    await redis.expire(key, ttl_days * 86400)


async def get_refresh_user(token: str) -> str | None:
    return await get_redis().hget(f"refresh:{token}", "user_id")


async def delete_refresh_token(token: str) -> None:
    await get_redis().delete(f"refresh:{token}")


# ── access-token blacklist ──
async def blacklist_jti(jti: str, ttl_seconds: int) -> None:
    if ttl_seconds > 0:
        await get_redis().set(f"blacklist:{jti}", "1", ex=ttl_seconds)


async def is_blacklisted(jti: str) -> bool:
    return await get_redis().exists(f"blacklist:{jti}") == 1
