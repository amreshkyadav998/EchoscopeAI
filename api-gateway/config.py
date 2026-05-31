"""API Gateway configuration (Phase 1.4 scaffold).

Required vars have no default and cause a clear startup failure if unset.
See HLD section 4.1 for the env-var contract.
"""

from __future__ import annotations

from functools import lru_cache

from echoscope_common import BaseAppSettings, load_settings


class Settings(BaseAppSettings):
    service_name: str = "api-gateway"

    # required
    jwt_secret: str

    # optional (defaults target the docker-compose network)
    redis_url: str = "redis://redis:6379/0"
    # JSON map of downstream service -> base URL, e.g. {"auth": "http://auth-service:8001"}
    service_urls: dict[str, str] = {
        "auth": "http://auth-service:8001",
        "mention": "http://mention-service:8002",
        "nlp": "http://nlp-service:8003",
        "analytics": "http://analytics-service:8004",
        "notification": "http://notification-service:8005",
        "report": "http://report-service:8006",
    }
    rate_limit_max: int = 100


@lru_cache
def get_settings() -> Settings:
    """Return the cached, validated settings (fails fast if required vars missing)."""
    return load_settings(Settings)


if __name__ == "__main__":
    s = get_settings()
    print(f"{s.service_name}: config OK (rate_limit_max={s.rate_limit_max}, "
          f"{len(s.service_urls)} downstream services)")
