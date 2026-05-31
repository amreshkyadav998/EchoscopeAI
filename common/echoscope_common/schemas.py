"""Shared Pydantic base models.

These provide consistent config and reusable response shapes for every service's
API layer.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BaseSchema(BaseModel):
    """Base for all request/response models.

    - ``from_attributes`` lets us build responses straight from ORM objects.
    - ``populate_by_name`` allows both field name and alias on input.
    - ``str_strip_whitespace`` trims incoming strings.
    """

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class TimestampedSchema(BaseSchema):
    """Mixin for entities exposing creation/update timestamps."""

    created_at: datetime
    updated_at: datetime | None = None


class ErrorResponse(BaseSchema):
    """Standard error envelope (mirrors ``AppError.to_dict``)."""

    error_code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseSchema):
    """Response for each service's ``GET /health`` endpoint."""

    status: str = "ok"
    service: str
    version: str = "0.1.0"
    checks: dict[str, Any] = Field(default_factory=dict)
