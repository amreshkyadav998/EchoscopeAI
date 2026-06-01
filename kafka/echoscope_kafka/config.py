"""Kafka tooling config (broker address)."""

from __future__ import annotations

from functools import lru_cache

from echoscope_common import BaseAppSettings, load_settings


class Settings(BaseAppSettings):
    service_name: str = "echoscope-kafka"
    kafka_brokers: str = "kafka:9092"


@lru_cache
def get_settings() -> Settings:
    return load_settings(Settings)
