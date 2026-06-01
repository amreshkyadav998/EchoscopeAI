"""Celery app + Beat schedule for periodic scraping (HLD §4.3).

The scraping pipeline is async; Celery tasks bridge to it via asyncio.run.

Run the worker + beat (separate terminals, from mention-service/):
    ../.venv/Scripts/celery -A app.celery_app.celery worker --loglevel=info --pool=solo
    ../.venv/Scripts/celery -A app.celery_app.celery beat   --loglevel=info
"""

from __future__ import annotations

import asyncio

from celery import Celery

from config import get_settings

settings = get_settings()

celery = Celery("mention-service", broker=settings.celery_broker_url, backend=settings.celery_broker_url)
celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    beat_schedule={
        "scrape-all-active-keywords": {
            "task": "app.celery_app.scrape_all",
            "schedule": float(settings.scrape_interval_minutes * 60),
        }
    },
)


@celery.task(name="app.celery_app.scrape_all")
def scrape_all() -> dict:
    from app.pipeline import run_scrape

    return asyncio.run(run_scrape(None))


@celery.task(name="app.celery_app.scrape_keywords")
def scrape_keywords(keyword_ids: list[str]) -> dict:
    from app.pipeline import run_scrape

    return asyncio.run(run_scrape(keyword_ids))
