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

## ⬜ Remaining phases (overview — see HLD page 18-20)

5. Kafka Setup (topics, producer util, consumer base class)
6. Mention Collection Service (keyword CRUD, scrapers, dedup, Celery, Kafka publish)
7. NLP Service (Kafka consumer, sentiment, NER, keywords, GPT summary)
8. Analytics Service (aggregation, spike detection, REST APIs, competitor scoring)
9. Real-Time WebSockets (WS endpoints, Redis bridge, frontend hook)
10. Notification Service (alert rules, evaluation engine, SendGrid email, history)
11. Report Service (async PDF/CSV, S3 + pre-signed URLs)
12. gRPC Communication (proto defs, servers, clients, error mapping)
13. Frontend Development (Vite+React+TS, auth/dashboard/mentions/analytics/alerts pages)
14. Monitoring & Logging (Prometheus, Grafana, Loki, health checks)
15. AWS Deployment + CI/CD (Dockerfiles, ECR, RDS/ElastiCache/MSK/S3/ALB, ECS, GH Actions)
