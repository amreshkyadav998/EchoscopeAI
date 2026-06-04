"""Consumer on analytics-updated → run the alert evaluation engine.

Uses a separate consumer group from the WS bridge so BOTH receive every event
(the bridge forwards to dashboards; this one evaluates alert rules).
"""

from __future__ import annotations

from app.evaluation import evaluate_event
from config import get_settings
from echoscope_kafka import ANALYTICS_UPDATED, BaseConsumer


class EvalConsumer(BaseConsumer):
    def __init__(self) -> None:
        settings = get_settings()
        super().__init__(
            brokers=settings.kafka_brokers,
            topic=ANALYTICS_UPDATED,
            group_id=f"{settings.consumer_group}-eval",
        )

    async def handle(self, event: dict) -> None:
        await evaluate_event(event)
