"""Consumer base class (HLD Phase 5 "Consumer base class").

Abstract base with a configurable group_id, manual offset commit (commit only after
the message is handled successfully), and dead-letter-topic publishing after repeated
failures so a poison message can't block the partition.

Subclass and implement ``handle(event)``::

    class NlpConsumer(BaseConsumer):
        async def handle(self, event: dict) -> None:
            ...  # process the mention-created event
"""

from __future__ import annotations

import asyncio
import json
from abc import ABC, abstractmethod
from typing import Any

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from loguru import logger as log

from .topics import dlt_name


class BaseConsumer(ABC):
    def __init__(
        self,
        *,
        brokers: str,
        topic: str,
        group_id: str,
        max_retries: int = 3,
        auto_offset_reset: str = "earliest",
    ) -> None:
        self.brokers = brokers
        self.topic = topic
        self.group_id = group_id
        self.max_retries = max_retries
        self.auto_offset_reset = auto_offset_reset
        self._consumer: AIOKafkaConsumer | None = None
        self._dlt_producer: AIOKafkaProducer | None = None
        self._stopping = False

    async def start(self) -> None:
        self._consumer = AIOKafkaConsumer(
            self.topic,
            bootstrap_servers=self.brokers,
            group_id=self.group_id,
            enable_auto_commit=False,  # manual commit after successful handle
            auto_offset_reset=self.auto_offset_reset,
            value_deserializer=lambda b: json.loads(b.decode()),
        )
        self._dlt_producer = AIOKafkaProducer(
            bootstrap_servers=self.brokers,
            value_serializer=lambda v: json.dumps(v, default=str).encode(),
        )
        await self._consumer.start()
        await self._dlt_producer.start()
        log.info("consumer started", topic=self.topic, group_id=self.group_id)

    async def stop(self) -> None:
        self._stopping = True
        if self._consumer is not None:
            await self._consumer.stop()
        if self._dlt_producer is not None:
            await self._dlt_producer.stop()
        log.info("consumer stopped", topic=self.topic, group_id=self.group_id)

    @abstractmethod
    async def handle(self, event: dict[str, Any]) -> None:
        """Process a single event. Raise to trigger retry/DLT."""

    async def _process(self, msg) -> None:
        delay = 0.5
        for attempt in range(1, self.max_retries + 1):
            try:
                await self.handle(msg.value)
                await self._consumer.commit()
                return
            except Exception:
                log.exception(
                    "handler error",
                    topic=self.topic,
                    attempt=attempt,
                    partition=msg.partition,
                    offset=msg.offset,
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(delay)
                    delay *= 2

        # retries exhausted → dead-letter and move on
        await self._dlt_producer.send_and_wait(
            dlt_name(self.topic),
            value={
                "original_topic": self.topic,
                "partition": msg.partition,
                "offset": msg.offset,
                "payload": msg.value,
            },
            key=msg.key,
        )
        await self._consumer.commit()
        log.error("message sent to DLT", topic=self.topic, offset=msg.offset)

    async def run(self) -> None:
        """Consume until stop() is called."""
        if self._consumer is None:
            raise RuntimeError("consumer not started")
        async for msg in self._consumer:
            if self._stopping:
                break
            await self._process(msg)
