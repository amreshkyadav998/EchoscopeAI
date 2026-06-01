# kafka — shared Kafka utilities (echoscope_kafka)

Topics, an event producer, and a consumer base class used by all event-driven services.

## Contents

- `echoscope_kafka/topics.py` — topic specs (partition counts per HLD §7.2) + `ensure_topics()`.
  Topics: `mention-created` (6), `sentiment-processed` (6), `analytics-updated` (3),
  `alert-triggered` (3), `report-generated` (2), each with a `<name>.dlt` dead-letter topic.
- `echoscope_kafka/producer.py` — `EventProducer`: JSON serialize, auto-adds `event_id` +
  `timestamp`, idempotent acks=all, exponential retry on transient errors, graceful close.
- `echoscope_kafka/consumer.py` — `BaseConsumer` (abstract): configurable `group_id`,
  manual offset commit (only after successful handle), and dead-letter publishing after
  `max_retries` failures. Subclass and implement `handle(event)`.
- `create_topics.py` — idempotent topic creation script.

## Usage

```bash
pip install -e ./common -e ./kafka       # from repo root .venv
cd kafka && cp .env.example .env          # host KAFKA_BROKERS=127.0.0.1:29092
../.venv/Scripts/python create_topics.py  # create topics + DLTs
```

```python
from echoscope_kafka import EventProducer, BaseConsumer, MENTION_CREATED

async with EventProducer(brokers) as prod:
    await prod.publish(MENTION_CREATED, {"mention_id": "...", "org_id": "..."}, key=org_id)

class NlpConsumer(BaseConsumer):
    async def handle(self, event: dict) -> None:
        ...  # process; raise to retry, exhausted retries -> DLT
```

> Brokers: in Docker use `kafka:9092`; from the host use `127.0.0.1:29092`.
