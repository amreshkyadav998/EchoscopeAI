"""echoscope_common — shared utilities for all EchoscopeAI backend microservices.

Importable building blocks used across api-gateway, auth-service, mention-service,
nlp-service, analytics-service, notification-service, and report-service.
"""

from .config import BaseAppSettings, load_settings
from .correlation import (
    clear_correlation_id,
    get_correlation_id,
    set_correlation_id,
)
from .exceptions import (
    AppError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    UnauthorizedError,
    ValidationError,
)
from .ids import is_valid_uuid, new_uuid
from .logger import configure_logging
from .schemas import (
    BaseSchema,
    ErrorResponse,
    HealthResponse,
    TimestampedSchema,
)

__version__ = "0.1.0"

__all__ = [
    # config
    "BaseAppSettings",
    "load_settings",
    # correlation
    "set_correlation_id",
    "get_correlation_id",
    "clear_correlation_id",
    # exceptions
    "AppError",
    "NotFoundError",
    "UnauthorizedError",
    "ForbiddenError",
    "ValidationError",
    "ConflictError",
    "RateLimitError",
    # ids
    "new_uuid",
    "is_valid_uuid",
    # logger
    "configure_logging",
    # schemas
    "BaseSchema",
    "TimestampedSchema",
    "ErrorResponse",
    "HealthResponse",
    "__version__",
]
