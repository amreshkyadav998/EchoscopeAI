"""API Gateway entrypoint (HLD section 4.1).

Single entry point for all client traffic. This Phase 2.1 scaffold wires up the
FastAPI app, lifespan, middleware (correlation logging, security headers, CORS),
and the health router. JWT auth, rate limiting, and request proxying are added in
Phases 2.2-2.4.

Run locally:  uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.middleware import (
    CORRELATION_HEADER,
    CorrelationIdMiddleware,
    SecurityHeadersMiddleware,
)
from app.routers import health
from config import get_settings
from echoscope_common import configure_logging

settings = get_settings()
log = configure_logging(settings.service_name, level=settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Phase 2.3 will open a Redis pool here; Phase 2.4 a shared httpx client.
    log.info("api-gateway starting", environment=settings.environment)
    yield
    log.info("api-gateway shutting down")


app = FastAPI(
    title="EchoscopeAI API Gateway",
    version="0.1.0",
    lifespan=lifespan,
)

# Middleware runs in reverse order of registration on the request path, so the
# correlation middleware (registered last) runs first and is active for all logs.
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
