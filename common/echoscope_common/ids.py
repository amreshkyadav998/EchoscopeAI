"""UUID helper utilities.

All primary keys in the platform are UUIDs (see the DB schema), so generation and
validation are needed in many places.
"""

from __future__ import annotations

import uuid


def new_uuid() -> str:
    """Generate a new random UUID4 as a string."""
    return str(uuid.uuid4())


def is_valid_uuid(value: object) -> bool:
    """Return True if ``value`` is parseable as a UUID, False otherwise."""
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, TypeError, AttributeError):
        return False
