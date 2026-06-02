"""Notification Service configuration (Phase 1.4 scaffold). See HLD section 4.6."""

from __future__ import annotations

from functools import lru_cache

from echoscope_common import BaseAppSettings, load_settings


class Settings(BaseAppSettings):
    service_name: str = "notification-service"

    # required
    db_url: str

    # required (JWT validation on WebSocket handshake — must match auth-service secret)
    jwt_secret: str

    # optional
    kafka_brokers: str = "kafka:9092"
    redis_url: str = "redis://redis:6379/0"
    sendgrid_api_key: str | None = None
    ws_heartbeat_interval: int = 30
    email_from_address: str | None = None

    # kafka -> redis pub/sub bridge
    consumer_group: str = "notification-service"
    enable_consumer: bool = True


@lru_cache
def get_settings() -> Settings:
    return load_settings(Settings)


if __name__ == "__main__":
    s = get_settings()
    print(f"{s.service_name}: config OK (ws_heartbeat_interval={s.ws_heartbeat_interval})")
