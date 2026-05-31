"""Auth Service configuration (Phase 1.4 scaffold). See HLD section 4.2."""

from __future__ import annotations

from functools import lru_cache

from echoscope_common import BaseAppSettings, load_settings


class Settings(BaseAppSettings):
    service_name: str = "auth-service"

    # required
    db_url: str
    jwt_secret: str

    # optional
    jwt_expire_minutes: int = 15
    refresh_expire_days: int = 7
    redis_url: str = "redis://redis:6379/0"
    smtp_host: str | None = None
    oauth_google_client_id: str | None = None
    oauth_google_client_secret: str | None = None


@lru_cache
def get_settings() -> Settings:
    return load_settings(Settings)


if __name__ == "__main__":
    s = get_settings()
    print(f"{s.service_name}: config OK (jwt_expire_minutes={s.jwt_expire_minutes}, "
          f"refresh_expire_days={s.refresh_expire_days})")
