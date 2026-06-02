"""Correlation + security middleware (mirrors gateway/auth/mention pattern)."""

from __future__ import annotations

import time

from loguru import logger as log
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from echoscope_common import clear_correlation_id, set_correlation_id

CORRELATION_HEADER = "X-Correlation-ID"

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Referrer-Policy": "no-referrer",
}


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        cid = set_correlation_id(request.headers.get(CORRELATION_HEADER))
        start = time.perf_counter()
        log.info("request received", method=request.method, path=request.url.path)
        try:
            response = await call_next(request)
        except Exception:
            log.exception("unhandled error during request")
            clear_correlation_id()
            raise
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        log.info(
            "request completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        response.headers[CORRELATION_HEADER] = cid
        for header, value in _SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        clear_correlation_id()
        return response
