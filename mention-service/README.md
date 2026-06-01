# Mention Collection Service (:8002)

Keyword/brand tracking + the scraping pipeline. Publishes `mention-created` Kafka events.

## What it does (HLD §4.3 / Phase 6)

- **Keyword CRUD** (`/api/v1/keywords`) with org scoping + plan `max_keywords` enforcement.
- **Pluggable sources** (`app/sources/`): `mock` (keyless dev default), `reddit` (PRAW),
  `news` (NewsAPI), `rss` (feedparser). Real sources activate only when their keys/feeds
  are set in `.env`; otherwise the mock source runs so the pipeline works with zero keys.
- **Pipeline** (`app/pipeline.py`): per-keyword scrape lock (Redis SETNX), URL-hash
  **dedup** (Redis `dedup:{sha256}` 24h + DB UNIQUE backstop), insert, and publish
  `mention-created` (keyed by org_id). Uses a raw Core connection (no ORM unit-of-work).
- **Mentions API**: `GET /api/v1/mentions` (filters: keyword_id, source, from_date, page),
  `POST /api/v1/mentions/scrape` (enqueues a Celery job).
- **Scheduling** (`app/celery_app.py`): Celery Beat scrapes all active keywords every
  `SCRAPE_INTERVAL_MINUTES`.

Auth: trusts the gateway-injected `X-User-Id` / `X-Role` / `X-Org-Id` headers.

## Run (host)

```bash
cp .env.example .env          # then optionally add REDDIT_*/NEWSAPI_KEY/RSS_FEEDS
../.venv/Scripts/uvicorn main:app --port 8002
# scraping worker + scheduler (separate terminals):
../.venv/Scripts/celery -A app.celery_app.celery worker --loglevel=info --pool=solo
../.venv/Scripts/celery -A app.celery_app.celery beat   --loglevel=info
```

`manual_test.py` is an end-to-end check against the live stack.
