"""Mention Collection Service configuration (Phase 1.4 scaffold). See HLD section 4.3."""

from __future__ import annotations

from functools import lru_cache

from echoscope_common import BaseAppSettings, load_settings


class Settings(BaseAppSettings):
    service_name: str = "mention-service"

    # required
    db_url: str

    # optional
    redis_url: str = "redis://redis:6379/0"
    kafka_brokers: str = "kafka:9092"
    reddit_client_id: str | None = None
    reddit_client_secret: str | None = None
    newsapi_key: str | None = None
    # comma-separated RSS/Atom feed URLs (optional, keyless)
    rss_feeds: str = ""
    scrape_interval_minutes: int = 30
    celery_broker_url: str = "redis://redis:6379/1"
    # number of mock mentions to generate per keyword when no real source is configured
    mock_mentions_per_keyword: int = 5


@lru_cache
def get_settings() -> Settings:
    return load_settings(Settings)


if __name__ == "__main__":
    s = get_settings()
    print(f"{s.service_name}: config OK (scrape_interval_minutes={s.scrape_interval_minutes}, "
          f"kafka_brokers={s.kafka_brokers})")
