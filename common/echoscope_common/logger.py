"""Structured JSON logging via loguru.

Emits one JSON object per line to stdout (collected by the Docker log driver and
later shipped to Loki). Every line includes a timestamp, level, service name, and
the current correlation ID — pulled automatically from the contextvar, so callers
never have to pass it explicitly.
"""

from __future__ import annotations

import json
import sys
from typing import Any

from loguru import logger

from .correlation import get_correlation_id


def _json_sink(message: Any) -> None:
    """loguru sink that serialises each record to a single-line JSON object."""
    record = message.record
    payload: dict[str, Any] = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "service_name": record["extra"].get("service_name"),
        "correlation_id": record["extra"].get("correlation_id"),
        "message": record["message"],
        "module": record["module"],
        "function": record["function"],
        "line": record["line"],
    }

    # include any extra bound fields (logger.bind(user_id=...)) without clobbering
    for key, value in record["extra"].items():
        if key not in payload:
            payload[key] = value

    if record["exception"] is not None:
        payload["exception"] = "".join(
            __import__("traceback").format_exception(
                record["exception"].type,
                record["exception"].value,
                record["exception"].traceback,
            )
        )

    print(json.dumps(payload, default=str), file=sys.stdout, flush=True)


def configure_logging(service_name: str, level: str = "INFO") -> "logger.__class__":
    """Configure the global loguru logger for a service and return it.

    Call once at service startup::

        from echoscope_common import configure_logging
        log = configure_logging("auth-service", level="INFO")
        log.info("service starting")
    """

    def _patcher(record: dict[str, Any]) -> None:
        record["extra"]["service_name"] = service_name
        # inject the live correlation id at log time unless one was bound explicitly
        if record["extra"].get("correlation_id") is None:
            record["extra"]["correlation_id"] = get_correlation_id()

    logger.remove()
    logger.configure(patcher=_patcher)
    logger.add(_json_sink, level=level.upper(), enqueue=False)
    return logger
