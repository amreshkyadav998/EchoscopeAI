"""Redis client + WebSocket pub/sub bridge helpers (HLD §4.6 / §8).

Channels:
  ws:channel:{org_id} — dashboard updates (from analytics-updated)
  ws:alerts:{org_id}  — alert delivery (from alert-triggered)
"""

from __future__ import annotations

import json
from typing import Any

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


def dashboard_channel(org_id: str) -> str:
    return f"ws:channel:{org_id}"


def alerts_channel(org_id: str) -> str:
    return f"ws:alerts:{org_id}"


async def publish_ws(channel: str, message: dict[str, Any]) -> int:
    """Publish a JSON message to a Redis channel (delivered to all WS subscribers)."""
    return await get_redis().publish(channel, json.dumps(message, default=str))
