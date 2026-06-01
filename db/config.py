"""Config for running migrations/seed against the database.

Reads DB_URL from the environment or a local db/.env file.
"""

from __future__ import annotations

from functools import lru_cache

from echoscope_common import BaseAppSettings, load_settings


class Settings(BaseAppSettings):
    service_name: str = "echoscope-db"
    db_url: str = "postgresql+asyncpg://echoscope:echoscope@postgres:5432/echoscope"


@lru_cache
def get_settings() -> Settings:
    return load_settings(Settings)
