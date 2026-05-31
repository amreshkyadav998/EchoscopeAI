"""Correlation-ID + request-logging middleware.

For every request: read an inbound ``X-Correlation-ID`` (or mint a new one), store
it in the contextvar so all logs in this request carry it, log request start/end
with latency, and echo the ID back on the response. See HLD section 4.1.
"""

from __future__ import annotations

import time

from loguru import logger as log
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from echoscope_common import clear_correlation_id, set_correlation_id

CORRELATION_HEADER = "X-Correlation-ID"


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
        clear_correlation_id()
        return response
