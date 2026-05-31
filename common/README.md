# echoscope_common

Shared Python utilities imported by all backend services.

## Install (from a service directory)

```bash
pip install -e ../common
```

## Modules

| Module | Exports | Purpose |
|--------|---------|---------|
| `config` | `BaseAppSettings`, `load_settings` | Pydantic-settings base class + fail-fast loader (clear errors on missing vars) |
| `correlation` | `set_correlation_id`, `get_correlation_id`, `clear_correlation_id` | `contextvars`-based correlation ID for distributed tracing |
| `logger` | `configure_logging` | loguru structured **JSON** logger to stdout, auto-injects correlation_id + service_name |
| `exceptions` | `AppError` + `NotFoundError`, `UnauthorizedError`, `ForbiddenError`, `ValidationError`, `ConflictError`, `RateLimitError` | Error hierarchy with `status_code` / `error_code` / `to_dict()` |
| `schemas` | `BaseSchema`, `TimestampedSchema`, `ErrorResponse`, `HealthResponse` | Reusable Pydantic base models |
| `ids` | `new_uuid`, `is_valid_uuid` | UUID helpers |

## Usage

```python
from echoscope_common import configure_logging, set_correlation_id, BaseAppSettings, load_settings

class Settings(BaseAppSettings):
    db_url: str          # required — fails fast at startup if unset
    jwt_secret: str

settings = load_settings(Settings)
log = configure_logging(settings.service_name, level=settings.log_level)

set_correlation_id()                 # new UUID for this request
log.info("service starting")         # -> {"timestamp":..., "service_name":..., "correlation_id":...}
```
