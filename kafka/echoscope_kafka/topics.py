"""Kafka topic definitions and admin helpers (HLD section 7.2).

Partition counts follow the HLD. Replication is 1 locally (single broker); MSK uses
3 in production. Each topic gets a companion dead-letter topic ``<name>.dlt``.
"""

from __future__ import annotations

from dataclasses import dataclass

from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from loguru import logger as log


@dataclass(frozen=True)
class TopicSpec:
    name: str
    partitions: int
    replication: int = 1


# topic name constants
MENTION_CREATED = "mention-created"
SENTIMENT_PROCESSED = "sentiment-processed"
ANALYTICS_UPDATED = "analytics-updated"
ALERT_TRIGGERED = "alert-triggered"
REPORT_GENERATED = "report-generated"

TOPICS: list[TopicSpec] = [
    TopicSpec(MENTION_CREATED, partitions=6),
    TopicSpec(SENTIMENT_PROCESSED, partitions=6),
    TopicSpec(ANALYTICS_UPDATED, partitions=3),
    TopicSpec(ALERT_TRIGGERED, partitions=3),
    TopicSpec(REPORT_GENERATED, partitions=2),
]


def dlt_name(topic: str) -> str:
    """Dead-letter topic name for a given topic."""
    return f"{topic}.dlt"


async def ensure_topics(brokers: str) -> dict[str, str]:
    """Create any missing topics (and their DLTs). Idempotent.

    Returns a {topic: 'created'|'exists'} map.
    """
    admin = AIOKafkaAdminClient(bootstrap_servers=brokers)
    await admin.start()
    result: dict[str, str] = {}
    try:
        existing = set(await admin.list_topics())
        to_create: list[NewTopic] = []
        for spec in TOPICS:
            for name in (spec.name, dlt_name(spec.name)):
                if name in existing:
                    result[name] = "exists"
                else:
                    to_create.append(
                        NewTopic(name, num_partitions=spec.partitions, replication_factor=spec.replication)
                    )
                    result[name] = "created"
        if to_create:
            await admin.create_topics(to_create)
            log.info("created kafka topics", topics=[t.name for t in to_create])
    finally:
        await admin.close()
    return result
