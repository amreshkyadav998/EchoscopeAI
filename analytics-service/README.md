# Analytics Service (:8004)

Consumes `sentiment-processed`, computes analytics over `mentions`+`sentiment_results`
(Pandas), and publishes `analytics-updated` / `alert-triggered`. (gRPC server: Phase 12.)

## Pieces

- `app/analytics.py` — `load_frame()` + Pandas computations: overview, trends
  (hour/day/week), sentiment breakdown, top keywords, sources, **Z-score spike detection**,
  **competitor scoring** (0.6×mentions_norm + 0.4×sentiment_norm).
- `app/cache.py` — Redis **cache-aside** (5-min TTL, key = `analytics:{org}:{endpoint}:{hash}`),
  hourly mention counters, per-org cache invalidation.
- `app/consumer.py` — `AnalyticsConsumer` on `sentiment-processed`: bumps the hourly
  counter and invalidates the org's analytics cache.
- `app/publisher.py` — periodic pass: publishes `analytics-updated` per org and
  `alert-triggered` on spikes (Redis debounce: 1 alert/keyword/10 min).
- `app/routers/analytics.py` — 7 endpoints (HLD §5.4): `/overview /trends /sentiment
  /keywords/top /spikes /competitors /sources`. Auth via X-User-* headers; org from `X-Org-Id`.

The consumer + periodic publisher run as background tasks in the lifespan.

## Run (host)

```bash
cp .env.example .env
../.venv/Scripts/uvicorn main:app --port 8004
```

`manual_test.py` is an end-to-end check (uses the seeded org's data).
