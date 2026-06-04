"""Report Service configuration (Phase 1.4 scaffold). See HLD section 4.7."""

from __future__ import annotations

from functools import lru_cache

from echoscope_common import BaseAppSettings, load_settings


class Settings(BaseAppSettings):
    service_name: str = "report-service"

    # required
    db_url: str

    # optional
    redis_url: str = "redis://redis:6379/0"
    kafka_brokers: str = "kafka:9092"
    aws_bucket: str | None = None          # set to use S3; otherwise local storage
    aws_region: str = "us-east-1"
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    celery_broker_url: str = "redis://redis:6379/1"

    # local storage fallback (used when aws_bucket is unset) + pre-signed URL TTL
    reports_dir: str = "data/reports"
    presigned_ttl: int = 86400  # 24h

    # gRPC client (Phase 12) — embed live analytics summary in the PDF
    analytics_grpc_addr: str = "analytics-service:50051"


@lru_cache
def get_settings() -> Settings:
    return load_settings(Settings)


if __name__ == "__main__":
    s = get_settings()
    print(f"{s.service_name}: config OK (aws_region={s.aws_region}, "
          f"kafka_brokers={s.kafka_brokers})")
