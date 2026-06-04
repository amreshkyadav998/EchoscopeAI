"""Celery app for async report generation (HLD §4.7).

Run the worker (from report-service/):
    ../.venv/Scripts/celery -A app.celery_app.celery worker --loglevel=info --pool=solo
"""

from __future__ import annotations

import asyncio

from celery import Celery

from config import get_settings

settings = get_settings()

celery = Celery("report-service", broker=settings.celery_broker_url, backend=settings.celery_broker_url)
celery.conf.update(task_serializer="json", result_serializer="json", accept_content=["json"], timezone="UTC")


@celery.task(name="app.celery_app.generate_report_task")
def generate_report_task(report_id: str) -> dict:
    from app.generate import generate_report

    return asyncio.run(generate_report(report_id))
