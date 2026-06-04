# Build Progress Log

Detailed running log of what has been built, decisions made, and what each next phase
entails. **Update this after every phase.** (Quick status lives in `../CLAUDE.md`.)

Source of truth for the design: `AI_Social_Listening_Platform_HLD_v2.pdf` (this folder),
15-phase roadmap on page 18.

Legend: ✅ done · 🚧 in progress · ⬜ not started

---

## ✅ Phase 1 — Foundation & Setup

- **1.1 Monorepo init** — Git repo + folder structure for all 7 services, `frontend/`,
  `common/`, `kafka/`, `monitoring/`, `nginx/`, `docs/`. Root `README.md`, `.gitignore`,
  `.gitattributes` (LF normalization). Pushed to GitHub.
- **1.2 Docker Compose** — `docker-compose.yml`: postgres:15, redis:7,
  cp-zookeeper:7.6.1, cp-kafka:7.6.1 (= Kafka 3.6). Named volumes, `echoscope-net`
  bridge, healthchecks on all four. Kafka dual-listener (`kafka:9092` internal,
  `localhost:29092` host). `.env.example` + `.env` (gitignored). All 4 verified healthy.
- **1.3 Shared `common/`** — installable `echoscope_common` package: `config`
  (`BaseAppSettings`, `load_settings`), `correlation` (contextvar), `logger` (loguru JSON),
  `exceptions` (`AppError` + subclasses), `schemas` (`BaseSchema`, `HealthResponse`, ...),
  `ids`. Smoke-tested.
- **1.4 Environment config** — per-service `.env.example` + `config.py`
  (`Settings(BaseAppSettings)`, cached `get_settings()`) + `requirements.txt` for all 7
  services, using the exact env vars/defaults from HLD section 4. Fail-fast validation
  verified.

## ✅ Phase 2 — API Gateway (`api-gateway/`)

- **2.1 FastAPI scaffold** — `main.py` (FastAPI + lifespan), `app/middleware/`
  (`correlation.py`: X-Correlation-ID + request logging; `security.py`: HSTS/X-Frame/
  X-Content-Type), `app/routers/health.py` (`GET /health`), CORS.
- **2.2 JWT auth** — `app/dependencies/auth.py`: `get_current_user` validates
  `Authorization: Bearer` HS256 JWT, extracts `user_id`/`role`/`org_id` (claims
  `sub`/`role`/`org_id`) → `request.state.user`. `require_role(*roles)` for RBAC.
  Raises `UnauthorizedError`/`ForbiddenError`.
- **2.3 Rate limiting** — `app/redis_client.py` (pool in lifespan) +
  `app/dependencies/rate_limit.py`: per-user sliding window `rate:{user_id}:{window}`
  via INCR+EXPIRE (60s); over limit → 429 + `Retry-After`.
- **2.4 Request proxying** — `app/routers/proxy.py`: catch-all `/api/v1/{path}` routes by
  prefix to the 7 services over a shared `httpx.AsyncClient`, 3× retry on transient
  errors (else 503). Strips `Authorization`; injects `X-User-Id/Role/Org-Id` +
  `X-Correlation-ID`. `main.py` adds an `AppError`→JSON exception handler.
- **Verified** end-to-end with TestClient + httpx `MockTransport`: auth failures → 401;
  all 6 route prefixes map correctly + 404 on unmapped; Authorization stripped & headers
  injected; rate limit `200,200,200,429`.

Route map (gateway prefix → service): `/api/v1/auth`→auth, `/api/v1/keywords` &
`/api/v1/mentions`→mention, `/api/v1/nlp`→nlp, `/api/v1/analytics`→analytics,
`/api/v1/alerts`→notification, `/api/v1/reports`→report.

---

## ✅ Phase 3 — Auth Service (`auth-service/`)

- **3.1 DB + Alembic** — async SQLAlchemy 2.0 + asyncpg (`app/db.py`, `app/models.py`:
  `Organization`, `User`, enums `Plan`/`Role`). Async Alembic (`alembic/env.py` +
  `versions/0001_users_organizations.py`) creates both tables + enums + indexes
  (`idx_users_email`, `idx_users_org`). Columns match HLD §6.
- **3.2 Registration** — `POST /register`: email-uniqueness check, bcrypt hash (cost=12),
  creates org + user in one transaction, **first user = org admin**. Verification email
  is a logged stub (real SendGrid send is Phase 10).
- **3.3 Login + JWT** — `POST /login`: `bcrypt.checkpw`, issues HS256 access token (15 min,
  claims `sub`/`role`/`org_id`/`jti`) + UUID4 refresh token stored in Redis HASH (7-day TTL);
  updates `last_login_at`. `app/security.py`.
- **3.4 Refresh / Logout** — `POST /refresh` validates + **rotates** the refresh token
  (old becomes invalid); `POST /logout` deletes the refresh token and **blacklists** the
  access jti (`blacklist:{jti}` for remaining TTL). `app/redis_client.py`.
- **3.5 RBAC** — `Role` enum in DB; `require_role(*roles)` dependency (`app/deps.py`);
  role embedded as a JWT claim.
- Endpoints (HLD §5.1): `register`, `login`, `refresh`, `logout`, `change-password`,
  `GET/PUT /me`. `app/routers/auth.py`. Service runs on :8001.
- **Verified** (18 checks) end-to-end vs real Postgres + Redis: register/dup-409,
  login/wrong-pw-401, JWT claims, /me (+401 no token), PUT /me, refresh rotation
  (old→401), change-password (old pw→401), logout → access blacklisted (401) + refresh
  deleted (401), `require_role` admin OK / viewer→403.

### ⚠️ Environment gotchas discovered (important for any new session)
- **Postgres host port = 5433**, not 5432: this machine runs a native PostgreSQL 17 on
  5432. Local `.env` sets `POSTGRES_PORT=5433`; committed `.env.example` defaults stay 5432.
- **Use `127.0.0.1` (not `localhost`) from the host** for Postgres: the container publishes
  on IPv4 only and Windows resolves `localhost` to IPv6 `::1` first → connection reset.
  (Redis at `localhost:6379` is unaffected.)

### 🔧 Known follow-ups (not blocking)
- **Gateway↔Auth token handling:** the gateway (Phase 2.4) strips `Authorization` and
  injects `X-User-*`. Auth-service currently validates the bearer locally (needed for
  logout jti + self-contained testing). Reconcile later: either exempt the auth route from
  Authorization-stripping at the gateway, or have services trust `X-User-*`.
- **Middleware duplication:** `auth-service/app/middleware.py` mirrors the gateway's
  correlation/security middleware. Consider moving to `echoscope_common` and reusing.

## ✅ Phase 4 — Database Schema (central `db/` package = `echoscope_db`)

**Architectural decision:** created a central `db/` package as the single source of
truth for ALL models + migrations + seed (rather than per-service). Every service
imports models from `echoscope_db`; all migrations live in `db/alembic`.

- **4.1 All 8 tables / migrations** — `echoscope_db/models.py` defines organizations,
  users, keywords, mentions, sentiment_results, alert_rules, alerts, reports (+ enums:
  plan, role, sentiment, alert_channel, report_type, report_status). Alembic chain:
  `0001` (users+organizations — identical to Phase 3's, kept as the chain base so it's a
  no-op on the existing DB) + `0002` (the other 6 tables). `alembic upgrade head` applied
  only 0002. DB now has all 9 relations (8 tables + alembic_version).
- **4.2 Indexes** — idx_users_email/org (0001); idx_keywords_org, idx_mentions_keyword_scraped,
  idx_mentions_org_scraped, idx_mentions_published, uq_mentions_source_url, idx_sentiment_mention,
  idx_alerts_org_triggered, idx_reports_org (0002).
- **4.3 Seed data** — `db/seed.py` (Faker): TRUNCATEs then inserts 2 orgs, 5 users each
  (first = admin, password `password123`), 10 keywords/org, **500 mentions + 1:1 sentiment**,
  2 alert rules/org. Verified counts + sentiment distribution (~45/25/30) + joins.
- **Refactor:** auth-service now imports models from `echoscope_db` (`app/models.py` is a
  re-export shim); its local `alembic/`+`alembic.ini` were removed; requirements add
  `-e ../db`. Re-verified auth register/login/me still work.

> To reseed: `cd db && ../.venv/Scripts/python seed.py` (wipes data first).

## ✅ Phase 5 — Kafka Setup (central `kafka/` package = `echoscope_kafka`)

Event backbone. Uses **aiokafka** (async). Broker was already running from Phase 1.

- **5.1 Local broker** — done in Phase 1; in Phase 5 changed the host-advertised listener
  to `PLAINTEXT_HOST://127.0.0.1:29092` (was `localhost`) so host clients connect over IPv4.
- **5.2 Create topics** — `echoscope_kafka/topics.py` defines specs + `ensure_topics()`
  (idempotent); `kafka/create_topics.py` runs it. Created (partitions per HLD §7.2):
  mention-created(6), sentiment-processed(6), analytics-updated(3), alert-triggered(3),
  report-generated(2) — plus a `<name>.dlt` for each. Verified counts in-broker.
- **5.3 Producer utility** — `echoscope_kafka/producer.py` `EventProducer`: JSON serialize,
  auto-adds `event_id` + `timestamp`, `enable_idempotence`/`acks=all`, exponential retry on
  transient errors, graceful start/stop (async context manager).
- **5.4 Consumer base class** — `echoscope_kafka/consumer.py` `BaseConsumer` (abstract):
  configurable `group_id`, `enable_auto_commit=False` (manual commit only after a successful
  `handle`), and after `max_retries` failures publishes the message to `<topic>.dlt` and
  commits (poison-message handling). Subclass + implement `handle(event)`.
- **Verified** against the live broker: produce→consume round-trip (event_id/timestamp added,
  payload intact) and the DLT flow (always-failing handler → message lands on the `.dlt` topic).

Brokers: in Docker `kafka:9092`; from host `127.0.0.1:29092` (kafka/.env). Topics already exist.

## ✅ Phase 6 — Mention Collection Service (`mention-service/`, :8002)

- **6.1 Keyword CRUD** — `app/routers/keywords.py`: POST/GET/DELETE `/api/v1/keywords`
  with org scoping + plan `max_keywords` enforcement + duplicate-keyword guard.
- **6.2-6.4 Pluggable scrapers** — `app/sources/`: `MockSource` (keyless dev default),
  `RedditSource` (PRAW), `NewsApiSource` (httpx), `RssSource` (feedparser). `registry.py`
  activates real sources only when creds/feeds are in `.env`, else falls back to mock.
  Playwright JS-rendering deferred.
- **6.5 Dedup** — Redis `dedup:{sha256(url)}` SET NX EX 24h (`app/redis_client.py`) +
  DB UNIQUE(source_url) backstop. Per-keyword scrape lock via Redis SETNX.
- **6.6 Celery** — `app/celery_app.py`: worker + Beat schedule (`scrape_all` every
  SCRAPE_INTERVAL_MINUTES); `scrape_keywords` task; `POST /mentions/scrape` enqueues it.
- **6.7 Kafka publish** — `app/pipeline.py` publishes `mention-created` (key=org_id) after
  each insert. Pipeline uses a raw **Core connection** (no ORM Session/unit-of-work).
- Auth: trusts gateway-injected `X-User-*` headers (`app/deps.py`).
- **Verified** end-to-end (`mention-service/manual_test.py`): CRUD + plan-limit 403 +
  401 without headers; dedup; pipeline inserts mock mentions; 30 `mention-created` events
  consumed from Kafka; scrape enqueue 202; keyword delete cascades.

### ⚠️ Gotcha fixed (applies to all services using echoscope_db)
Deleting a parent (e.g. Keyword) made the ORM try to `UPDATE child SET fk=NULL`, which
violates NOT NULL. Fixed by adding **`passive_deletes=True`** to the one-to-many
relationships in `echoscope_db/models.py` (Organization.users/keywords, Keyword.mentions,
Mention.sentiment) so the ORM relies on the DB-level `ON DELETE CASCADE`.

## ✅ Phase 7 — NLP Service (`nlp-service/`, :8003)

Consumes `mention-created`, analyzes, writes `sentiment_results`, publishes
`sentiment-processed`. **Lightweight/offline by default; heavy models opt-in.**

- **Analyzers** (`app/analysis.py`): sentiment = VADER (default) or HuggingFace RoBERTa
  (`USE_TRANSFORMERS`); NER = regex (default) or spaCy (`USE_SPACY`); keywords =
  stopword-filtered frequency top-5; summary = extractive (default) or GPT-4o-mini
  (`OPENAI_API_KEY`). Heavy libs are lazy-loaded and not in default requirements.
- **Processor** (`app/processor.py`): `process_event()` inserts `sentiment_results` via
  Core `ON CONFLICT DO NOTHING` (idempotent 1:1), caches summary in Redis
  (`nlp:summary:{id}`), publishes `sentiment-processed` (key=mention_id).
- **Consumer** (`app/consumer.py`): `NlpConsumer(BaseConsumer)` on `mention-created`
  (group `nlp-service`), runs as an in-process background task in the lifespan.
- **REST** (`app/routers/nlp.py`, HLD §5.3): `POST /analyze`, `POST /batch` +
  `GET /jobs/{id}`, `GET /summary/{mention_id}`. Auth via X-User-* headers.
- **Verified** (`nlp-service/manual_test.py`): /analyze sentiment; 401 without headers;
  batch+jobs; process_event writes sentiment + publishes; idempotent reprocess; summary
  for long content; sentiment-processed event consumed.

## ✅ Phase 8 — Analytics Service (`analytics-service/`, :8004)

Consumes `sentiment-processed`; computes analytics over mentions+sentiment_results.

- **Computations** (`app/analytics.py`, Pandas): `load_frame()` then overview, trends
  (hour/day/week), sentiment breakdown, top keywords, sources, **Z-score spike detection**
  (per-keyword hourly counts, mean+2σ), **competitor scoring** (0.6×mentions_norm +
  0.4×sentiment_norm, ranked).
- **Cache** (`app/cache.py`): Redis cache-aside (5-min TTL), hourly counters, per-org invalidation.
- **Consumer** (`app/consumer.py`): on `sentiment-processed` bump hourly counter + invalidate cache.
- **Publisher** (`app/publisher.py`): periodic — publish `analytics-updated` per org +
  `alert-triggered` on spikes (Redis debounce 10 min). Runs as a background task.
- **REST** (`app/routers/analytics.py`, HLD §5.4): 7 endpoints (`/overview /trends /sentiment
  /keywords/top /spikes /competitors /sources`), X-User-* auth, cache-aside.
- Also added `keyword_id` to the nlp-service `sentiment-processed` payload (needed for spikes).
- **Verified** (`analytics-service/manual_test.py`) against seed data: all 7 endpoints return
  sensible values (overview 249 mentions/51% pos, 30 trend points, sentiment sums to total,
  top keywords, sources, competitor scores in [0,1], spikes), 401 w/o headers, cache key
  written, synthetic 40× spike flagged (z=4.9), publisher emits analytics-updated (consumed).

## ✅ Phase 9 — Real-Time WebSockets (`notification-service/`, :8005)

- **WS endpoints** (`app/ws.py`): `/ws/dashboard` + `/ws/alerts`. JWT validated on the
  handshake via `?token=` (`app/security.py`); subscribes to the org's Redis channel BEFORE
  accept (no missed messages) and forwards live; ping→pong keepalive; org-isolated.
- **Kafka→Redis bridge** (`app/bridge.py`): `analytics-updated` → `ws:channel:{org}`
  (`metrics_update`); `alert-triggered` → `ws:alerts:{org}` (`alert`). Two BaseConsumers
  (group `notification-service`) run as lifespan background tasks.
- **Frontend hook**: `frontend/src/hooks/useWebSocket.ts` — auto-reconnect (exp backoff
  1→30s + ±20% jitter), ping/pong, onMessage dispatch. (Full app = Phase 13.)
- Config: added `jwt_secret` (must match auth-service); `websockets` dep.
- **Verified** (`notification-service/manual_test.py`): bridge → Redis publish; WS rejects
  missing/invalid token; valid token receives forwarded messages; ping→pong; /ws/alerts
  delivery; **org isolation**.

> Workflow note: Phase 9+ built on per-phase branches (stacked) for PR-merge into main.

## ✅ Phase 10 — Notification Service: alerting (`notification-service/`, :8005)

- **Rule CRUD + history** (`app/routers/alerts.py`, HLD §5.5): `GET/POST/PUT/DELETE
  /api/v1/alerts/rules`; `GET /api/v1/alerts/history` with keyset pagination on
  `triggered_at` (`cursor` param, `next_cursor` in response).
- **Evaluation engine** (`app/evaluation.py`): on `analytics-updated`, evaluate enabled
  org rules (condition types `volume` / `negative_pct` / `spike`), **debounce** via Redis
  (`alert:debounce:{rule_id}`, 10 min), persist an `alerts` row (Core insert), push to
  `ws:alerts:{org}`, and email org admins. `app/eval_consumer.py` consumes on group
  `notification-service-eval` (separate from the WS bridge group so both receive events).
- **Email** (`app/email.py`): Jinja2 HTML; SendGrid HTTP API if `SENDGRID_API_KEY`, else
  logs a stub (runs key-free).
- Config: `db.py`, `deps.py` (X-User-* auth). Deps add jinja2/httpx/asyncpg.
- **Verified** (`manual_test_phase10.py`): rule CRUD + 401, evaluation fires 1 alert on
  match, alert persisted, pushed to WS alerts channel, **debounced** on re-eval, history
  returns it, delete cascades.

## ✅ Phase 11 — Report Service (`report-service/`, :8006)

Async PDF/CSV generation via Celery; S3-or-local storage; `report-generated` event.

- **Generation** (`app/generate.py`): `generate_report(report_id)` loads mentions+sentiment
  (Pandas, filtered by `{from_date,to_date,keywords}`), builds the file, stores it, updates
  the `reports` row (status/s3_key/size/expires_at/completed_at), publishes `report-generated`.
  - **PDF** = fpdf2 (cover, KPIs, Matplotlib trend chart, top keywords). WeasyPrint deferred
    (needs GTK on Windows). **CSV** = Pandas join.
- **Storage** (`app/storage.py`): boto3 S3 + 24h pre-signed URL when `AWS_BUCKET` set, else
  local files under `data/reports/` served by `/reports/{id}/download`.
- **Async API** (`app/routers/reports.py`, HLD §5.6): `POST /reports` → 202 + queued (Celery
  `generate_report_task`); `GET /reports`, `GET /reports/{id}`, `/download`, `DELETE`,
  `POST /reports/schedule` (stub — recurring Beat is a follow-up). `app/celery_app.py`.
- **Verified** (`manual_test.py`): 401; csv queue→generate→download (header row); pdf
  generate→download (valid %PDF + chart, ~16 KB); list; schedule 202; delete→404;
  report-generated event consumed.
- Gotcha: fpdf2's default font is Latin-1 — avoid non-ASCII (used "-" not "—" in the title).

## ⬜ Remaining phases (overview — see HLD page 18-20)

12. gRPC Communication (proto defs, servers, clients, error mapping)
13. Frontend Development (Vite+React+TS, auth/dashboard/mentions/analytics/alerts pages)
14. Monitoring & Logging (Prometheus, Grafana, Loki, health checks)
15. AWS Deployment + CI/CD (Dockerfiles, ECR, RDS/ElastiCache/MSK/S3/ALB, ECS, GH Actions)
