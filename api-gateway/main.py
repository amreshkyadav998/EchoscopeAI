"""API Gateway entrypoint (HLD section 4.1).

Single entry point for all client traffic: correlation logging, security headers,
CORS, JWT validation, per-user rate limiting, and reverse-proxying to the 7
downstream services.

Run locally:  uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.middleware import (
    CORRELATION_HEADER,
    CorrelationIdMiddleware,
    SecurityHeadersMiddleware,
)
from app.redis_client import close_redis, init_redis
from app.routers import health, proxy
from config import get_settings
from echoscope_common import AppError, configure_logging

settings = get_settings()
log = configure_logging(settings.service_name, level=settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("api-gateway starting", environment=settings.environment)
    app.state.http_client = httpx.AsyncClient(timeout=httpx.Timeout(10.0))
    init_redis(settings.redis_url)
    yield
    await app.state.http_client.aclose()
    await close_redis()
    log.info("api-gateway shutting down")


app = FastAPI(
    title="EchoscopeAI API Gateway",
    version="0.1.0",
    lifespan=lifespan,
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Turn any AppError into a consistent JSON error response."""
    headers: dict[str, str] = {}
    if exc.error_code == "rate_limited" and "retry_after" in exc.details:
        headers["Retry-After"] = str(exc.details["retry_after"])
    return JSONResponse(status_code=exc.status_code, content=exc.to_dict(), headers=headers)


# Middleware runs in reverse order of registration, so the correlation middleware
# (registered last) runs first and is active for all logs.
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tightened per environment in a later phase
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[CORRELATION_HEADER],
)
app.add_middleware(CorrelationIdMiddleware)

app.include_router(health.router)
app.include_router(proxy.router)
