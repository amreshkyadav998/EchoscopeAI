"""Kafka → Redis pub/sub bridge (HLD §4.6).

Consumes analytics-updated / alert-triggered and republishes each to the org's WS
Redis channel, so connected dashboards/alert streams receive them in real time.
"""

from __future__ import annotations

from app.redis_client import alerts_channel, dashboard_channel, ensure_redis, publish_ws
from config import get_settings
from echoscope_kafka import ALERT_TRIGGERED, ANALYTICS_UPDATED, BaseConsumer


class _BridgeConsumer(BaseConsumer):
    def __init__(self, topic: str, channel_fn, msg_type: str) -> None:
        settings = get_settings()
        super().__init__(brokers=settings.kafka_brokers, topic=topic, group_id=settings.consumer_group)
        self._channel_fn = channel_fn
        self._msg_type = msg_type
        self._redis_url = settings.redis_url

    async def handle(self, event: dict) -> None:
        org_id = event.get("org_id")
        if not org_id:
            return
        ensure_redis(self._redis_url)
        await publish_ws(self._channel_fn(org_id), {"type": self._msg_type, "payload": event})


def dashboard_bridge() -> _BridgeConsumer:
    return _BridgeConsumer(ANALYTICS_UPDATED, dashboard_channel, "metrics_update")


def alerts_bridge() -> _BridgeConsumer:
    return _BridgeConsumer(ALERT_TRIGGERED, alerts_channel, "alert")
