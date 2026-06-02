"""Kafka consumer on mention-created (group: nlp-service).

Extends the shared BaseConsumer (manual commit after successful handle, DLT on
repeated failure). Holds an EventProducer to publish sentiment-processed.
"""

from __future__ import annotations

from app.processor import process_event
from config import get_settings
from echoscope_kafka import MENTION_CREATED, BaseConsumer, EventProducer


class NlpConsumer(BaseConsumer):
    def __init__(self) -> None:
        settings = get_settings()
        super().__init__(
            brokers=settings.kafka_brokers,
            topic=MENTION_CREATED,
            group_id=settings.consumer_group,
        )
        self._producer = EventProducer(settings.kafka_brokers)

    async def start(self) -> None:
        await self._producer.start()
        await super().start()

    async def stop(self) -> None:
        await super().stop()
        await self._producer.stop()

    async def handle(self, event: dict) -> None:
        await process_event(event, self._producer)
