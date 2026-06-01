"""Auth Service entrypoint (HLD section 4.2).

Run locally:  uvicorn main:app --host 0.0.0.0 --port 8001 --reload
(DB schema is applied with: alembic upgrade head)
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.db import engine
from app.middleware import CorrelationIdMiddleware
from app.redis_client import close_redis, init_redis
from app.routers import auth
from config import get_settings
from echoscope_common import AppError, HealthResponse, configure_logging

settings = get_settings()
log = configure_logging(settings.service_name, level=settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("auth-service starting", environment=settings.environment)
    init_redis(settings.redis_url)
    yield
    await close_redis()
    await engine.dispose()
    log.info("auth-service shutting down")


app = FastAPI(title="EchoscopeAI Auth Service", version="0.1.0", lifespan=lifespan)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=exc.to_dict())


app.add_middleware(CorrelationIdMiddleware)
app.include_router(auth.router)


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health() -> HealthResponse:
    return HealthResponse(service=settings.service_name, version="0.1.0", checks={"auth": "ok"})
