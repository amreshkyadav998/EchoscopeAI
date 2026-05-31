"""Per-user sliding-window rate limiting (HLD section 4.1, Phase 2.3).

Uses Redis INCR + EXPIRE on a per-(user_id, 60s window) key. When the count
exceeds ``RATE_LIMIT_MAX`` the request is rejected with 429 + a Retry-After header
(set by the AppError handler from ``details['retry_after']``).
"""

from __future__ import annotations

import time

from fastapi import Depends

from app.dependencies.auth import CurrentUser, get_current_user
from app.redis_client import get_redis
from config import get_settings
from echoscope_common import RateLimitError

WINDOW_SECONDS = 60


async def rate_limit(user: CurrentUser = Depends(get_current_user)) -> None:
    settings = get_settings()
    redis = get_redis()

    window = int(time.time()) // WINDOW_SECONDS
    key = f"rate:{user.user_id}:{window}"

    count = await redis.incr(key)
    if count == 1:
        # first hit in this window — set the window's TTL
        await redis.expire(key, WINDOW_SECONDS)

    if count > settings.rate_limit_max:
        ttl = await redis.ttl(key)
        retry_after = ttl if ttl and ttl > 0 else WINDOW_SECONDS
        raise RateLimitError(
            f"Rate limit of {settings.rate_limit_max} requests/min exceeded",
            details={"retry_after": retry_after},
        )
