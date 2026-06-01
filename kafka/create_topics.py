"""Create all Kafka topics (and their dead-letter topics). Idempotent.

Run (host):  cd kafka && ../.venv/Scripts/python create_topics.py
"""

from __future__ import annotations

import asyncio

from echoscope_kafka import ensure_topics
from echoscope_kafka.config import get_settings


async def main() -> None:
    brokers = get_settings().kafka_brokers
    result = await ensure_topics(brokers)
    for name, status in sorted(result.items()):
        print(f"  {status:8} {name}")
    print(f"\nDone ({brokers}).")


if __name__ == "__main__":
    asyncio.run(main())
