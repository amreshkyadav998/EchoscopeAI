"""Base exception hierarchy shared across services.

Every domain error derives from :class:`AppError`, which carries an HTTP
``status_code`` and a machine-readable ``error_code``. In Phase 2 the API gateway
(and each FastAPI service) installs a single exception handler that turns any
``AppError`` into a consistent JSON error response via :meth:`AppError.to_dict`.
"""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base class for all application errors.

    Subclasses set ``status_code``, ``error_code``, and ``default_message``.
    """

    status_code: int = 500
    error_code: str = "internal_error"
    default_message: str = "An unexpected error occurred"

    def __init__(
        self,
        message: str | None = None,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """Serialise to the standard error response shape."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
        }


class ValidationError(AppError):
    status_code = 422
    error_code = "validation_error"
    default_message = "Validation failed"


class UnauthorizedError(AppError):
    status_code = 401
    error_code = "unauthorized"
    default_message = "Authentication required"


class ForbiddenError(AppError):
    status_code = 403
    error_code = "forbidden"
    default_message = "You do not have permission to perform this action"


class NotFoundError(AppError):
    status_code = 404
    error_code = "not_found"
    default_message = "Resource not found"


class ConflictError(AppError):
    status_code = 409
    error_code = "conflict"
    default_message = "Resource conflict"


class RateLimitError(AppError):
    status_code = 429
    error_code = "rate_limited"
    default_message = "Rate limit exceeded"
