"""Notification Service entrypoint (HLD §4.6).

Serves WebSockets (/ws/dashboard, /ws/alerts) + alert-rule REST APIs, and runs:
  - Kafka→Redis bridges (analytics-updated → dashboard, alert-triggered → alerts)
  - the alert evaluation engine (analytics-updated → match rules → alert + email + WS)

Run locally:  uvicorn main:app --host 0.0.0.0 --port 8005 --reload
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.bridge import alerts_bridge, dashboard_bridge
from app.db import engine
from app.eval_consumer import EvalConsumer
from app.redis_client import close_redis, init_redis
from app.routers import alerts
from app.ws import router as ws_router
from config import get_settings
from echoscope_common import AppError, HealthResponse, configure_logging

settings = get_settings()
log = configure_logging(settings.service_name, level=settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("notification-service starting", environment=settings.environment)
    init_redis(settings.redis_url)

    consumers = []
    tasks: list[asyncio.Task] = []
    if settings.enable_consumer:
        # WS bridges + the alert evaluation engine (separate consumer groups)
        for make in (dashboard_bridge, alerts_bridge, EvalConsumer):
            consumer = make()
            await consumer.start()
            consumers.append(consumer)
            tasks.append(asyncio.create_task(consumer.run()))
        log.info("consumers started (bridges + evaluation engine)", group=settings.consumer_group)

    try:
        yield
    finally:
        for consumer in consumers:
            await consumer.stop()
        for task in tasks:
            task.cancel()
        await close_redis()
        await engine.dispose()
        log.info("notification-service shutting down")


app = FastAPI(title="EchoscopeAI Notification Service", version="0.1.0", lifespan=lifespan)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=exc.to_dict())


app.include_router(ws_router)
app.include_router(alerts.router)


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health() -> HealthResponse:
    return HealthResponse(service=settings.service_name, version="0.1.0", checks={"notification": "ok"})
