"""Analytics Service entrypoint (HLD §4.5).

Serves the 7 analytics REST endpoints, runs the sentiment-processed consumer, and a
periodic task that publishes analytics-updated (+ alert-triggered on spikes).

Run locally:  uvicorn main:app --host 0.0.0.0 --port 8004 --reload
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from loguru import logger as _log

from app.cache import close_redis, init_redis
from app.consumer import AnalyticsConsumer
from app.db import engine
from app.middleware import CorrelationIdMiddleware
from app.publisher import publish_analytics_updates
from app.routers import analytics
from config import get_settings
from echoscope_common import AppError, HealthResponse, configure_logging
from echoscope_kafka import EventProducer

settings = get_settings()
log = configure_logging(settings.service_name, level=settings.log_level)


async def _periodic_publisher(producer: EventProducer):
    while True:
        await asyncio.sleep(settings.analytics_interval_seconds)
        try:
            await publish_analytics_updates(producer)
        except Exception:
            _log.exception("periodic analytics publish failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("analytics-service starting", environment=settings.environment)
    init_redis(settings.redis_url)

    consumer = producer = None
    tasks: list[asyncio.Task] = []
    if settings.enable_consumer:
        consumer = AnalyticsConsumer()
        await consumer.start()
        tasks.append(asyncio.create_task(consumer.run()))
        producer = EventProducer(settings.kafka_brokers)
        await producer.start()
        tasks.append(asyncio.create_task(_periodic_publisher(producer)))
        log.info("consumer + periodic publisher started", group=settings.consumer_group)

    try:
        yield
    finally:
        if consumer is not None:
            await consumer.stop()
        for task in tasks:
            task.cancel()
        if producer is not None:
            await producer.stop()
        await close_redis()
        await engine.dispose()
        log.info("analytics-service shutting down")


app = FastAPI(title="EchoscopeAI Analytics Service", version="0.1.0", lifespan=lifespan)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=exc.to_dict())


app.add_middleware(CorrelationIdMiddleware)
app.include_router(analytics.router)


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health() -> HealthResponse:
    return HealthResponse(service=settings.service_name, version="0.1.0", checks={"analytics": "ok"})
