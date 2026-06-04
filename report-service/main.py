"""Report Service entrypoint (HLD §4.7).

Serves the report REST API. Generation runs in a Celery worker (app/celery_app.py);
POST /reports returns 202 + report_id and enqueues the job.

Run locally:
    uvicorn main:app --host 0.0.0.0 --port 8006 --reload
    ../.venv/Scripts/celery -A app.celery_app.celery worker --loglevel=info --pool=solo
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.db import engine
from app.middleware import CorrelationIdMiddleware
from app.routers import reports
from config import get_settings
from echoscope_common import AppError, HealthResponse, configure_logging

settings = get_settings()
log = configure_logging(settings.service_name, level=settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("report-service starting", environment=settings.environment)
    yield
    await engine.dispose()
    log.info("report-service shutting down")


app = FastAPI(title="EchoscopeAI Report Service", version="0.1.0", lifespan=lifespan)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=exc.to_dict())


app.add_middleware(CorrelationIdMiddleware)
app.include_router(reports.router)


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health() -> HealthResponse:
    return HealthResponse(service=settings.service_name, version="0.1.0", checks={"report": "ok"})
