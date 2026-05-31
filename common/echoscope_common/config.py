"""Configuration base class built on pydantic-settings.

Each service defines its own ``Settings`` subclass declaring the env vars it needs.
Required vars are simply declared without a default; pydantic raises a clear error
at startup if they are missing. ``load_settings`` wraps that error into a readable,
actionable message and exits — so a misconfigured container fails fast and loud.
"""

from __future__ import annotations

import sys
from typing import TypeVar

from pydantic import ValidationError as PydanticValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

T = TypeVar("T", bound="BaseAppSettings")


class BaseAppSettings(BaseSettings):
    """Common settings shared by every service.

    Subclass it and add service-specific fields::

        class Settings(BaseAppSettings):
            db_url: str                 # required — no default
            jwt_secret: str             # required
            redis_url: str = "redis://redis:6379/0"
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    service_name: str = "echoscope-service"
    environment: str = "development"
    log_level: str = "INFO"


def load_settings(settings_cls: type[T]) -> T:
    """Instantiate a settings class, failing fast with a clear message.

    On missing/invalid required env vars, prints a human-readable summary and exits
    with status 1 instead of dumping a raw pydantic traceback.
    """
    try:
        return settings_cls()
    except PydanticValidationError as exc:
        lines = ["", f"Configuration error in {settings_cls.__name__}:"]
        for err in exc.errors():
            field = ".".join(str(p) for p in err["loc"])
            lines.append(f"  - {field}: {err['msg']}")
        lines.append("")
        lines.append("Set the missing variables in your .env file or environment.")
        print("\n".join(lines), file=sys.stderr)
        raise SystemExit(1) from exc
