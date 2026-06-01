"""Event producer (HLD Phase 5 "Producer utility").

JSON-serializes payloads, stamps every message with an event_id + timestamp,
retries on transient errors with exponential backoff, and closes gracefully.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaConnectionError, KafkaError
from loguru import logger as log

from echoscope_common import new_uuid

_TRANSIENT = (KafkaConnectionError,)


class EventProducer:
    def __init__(self, brokers: str, *, max_retries: int = 3) -> None:
        self._brokers = brokers
        self._max_retries = max_retries
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._brokers,
            value_serializer=lambda v: json.dumps(v, default=str).encode(),
            key_serializer=lambda k: k.encode() if k is not None else None,
            enable_idempotence=True,
            acks="all",
        )
        await self._producer.start()
        log.info("kafka producer started", brokers=self._brokers)

    async def stop(self) -> None:
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None
            log.info("kafka producer stopped")

    async def publish(
        self, topic: str, payload: dict[str, Any], *, key: str | None = None
    ) -> dict[str, Any]:
        """Publish an event. Adds event_id + timestamp if absent. Returns the envelope."""
        if self._producer is None:
            raise RuntimeError("producer not started")

        event = dict(payload)
        event.setdefault("event_id", new_uuid())
        event.setdefault("timestamp", datetime.now(timezone.utc).isoformat())

        delay = 0.5
        last_exc: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                await self._producer.send_and_wait(topic, value=event, key=key)
                log.debug("event published", topic=topic, event_id=event["event_id"], key=key)
                return event
            except _TRANSIENT as exc:
                last_exc = exc
                log.warning(
                    "transient publish error, retrying",
                    topic=topic,
                    attempt=attempt,
                    error=str(exc),
                )
                await asyncio.sleep(delay)
                delay *= 2
            except KafkaError:
                log.exception("non-retryable publish error", topic=topic)
                raise
        raise RuntimeError(f"failed to publish to {topic} after {self._max_retries} attempts") from last_exc

    async def __aenter__(self) -> "EventProducer":
        await self.start()
        return self

    async def __aexit__(self, *exc) -> None:
        await self.stop()
