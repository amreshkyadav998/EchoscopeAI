"""echoscope_kafka — shared Kafka topics, producer, and consumer base class."""

from .consumer import BaseConsumer
from .producer import EventProducer
from .topics import (
    ALERT_TRIGGERED,
    ANALYTICS_UPDATED,
    MENTION_CREATED,
    REPORT_GENERATED,
    SENTIMENT_PROCESSED,
    TOPICS,
    TopicSpec,
    dlt_name,
    ensure_topics,
)

__all__ = [
    "EventProducer",
    "BaseConsumer",
    "ensure_topics",
    "dlt_name",
    "TopicSpec",
    "TOPICS",
    "MENTION_CREATED",
    "SENTIMENT_PROCESSED",
    "ANALYTICS_UPDATED",
    "ALERT_TRIGGERED",
    "REPORT_GENERATED",
]
