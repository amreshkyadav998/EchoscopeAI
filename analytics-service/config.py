"""Analytics Service configuration (Phase 1.4 scaffold). See HLD section 4.5."""

from __future__ import annotations

from functools import lru_cache

from echoscope_common import BaseAppSettings, load_settings


class Settings(BaseAppSettings):
    service_name: str = "analytics-service"

    # required
    db_url: str

    # optional
    kafka_brokers: str = "kafka:9092"
    redis_url: str = "redis://redis:6379/0"
    spike_threshold: float = 2.0
    trend_window_hours: int = 24
    cache_ttl: int = 300


@lru_cache
def get_settings() -> Settings:
    return load_settings(Settings)


if __name__ == "__main__":
    s = get_settings()
    print(f"{s.service_name}: config OK (spike_threshold={s.spike_threshold}, "
          f"trend_window_hours={s.trend_window_hours})")
