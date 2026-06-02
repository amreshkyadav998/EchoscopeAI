"""Kafka consumer on sentiment-processed (group: analytics-service).

On each event: bump the org's hourly mention counter and invalidate that org's
cached analytics so the next API call recomputes fresh numbers. Spike detection and
periodic analytics-updated publishing are handled by app/publisher.py.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.cache import ensure_redis, incr_hourly_counter, invalidate_org
from config import get_settings
from echoscope_kafka import SENTIMENT_PROCESSED, BaseConsumer


class AnalyticsConsumer(BaseConsumer):
    def __init__(self) -> None:
        settings = get_settings()
        super().__init__(
            brokers=settings.kafka_brokers,
            topic=SENTIMENT_PROCESSED,
            group_id=settings.consumer_group,
        )
        self._redis_url = settings.redis_url

    async def handle(self, event: dict) -> None:
        org_id = event.get("org_id")
        if not org_id:
            return
        ensure_redis(self._redis_url)
        hour = datetime.now(timezone.utc).strftime("%Y%m%d%H")
        await incr_hourly_counter(org_id, hour)
        await invalidate_org(org_id)
