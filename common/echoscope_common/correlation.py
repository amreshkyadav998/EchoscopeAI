"""Correlation-ID context variable for distributed request tracing.

A correlation ID is a single identifier attached to a request as it flows through
the API gateway and every downstream microservice (propagated via the
``X-Correlation-ID`` header and Kafka message headers). Storing it in a
``contextvars.ContextVar`` makes it available to the logger without threading it
through every function call — and keeps it isolated per async task.
"""

from __future__ import annotations

import contextvars
import uuid

# default=None so logs before a request starts simply carry a null correlation_id
_correlation_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "correlation_id", default=None
)


def set_correlation_id(value: str | None = None) -> str:
    """Set the current correlation ID, generating a new UUID4 if none is given.

    Returns the value that was set so callers can echo it back in a response header.
    """
    cid = value or str(uuid.uuid4())
    _correlation_id.set(cid)
    return cid


def get_correlation_id() -> str | None:
    """Return the correlation ID for the current context, or ``None`` if unset."""
    return _correlation_id.get()


def clear_correlation_id() -> None:
    """Reset the correlation ID (e.g. at the end of a request lifecycle)."""
    _correlation_id.set(None)
