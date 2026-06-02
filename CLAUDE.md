# CLAUDE.md — Project context for Claude Code

> This file is auto-loaded at the start of every session. Read it first, then read
> `docs/PROGRESS.md` for the detailed phase-by-phase status before doing any work.

## What this project is

**EchoscopeAI** — an AI-powered social listening & reputation monitoring platform.
Event-driven microservices that scrape public sources, detect brand mentions, run AI
sentiment analysis, fire real-time alerts, and visualise analytics on a live dashboard.

The complete spec is the High-Level Design at **`docs/AI_Social_Listening_Platform_HLD_v2.pdf`**
(read it for any detail). We are building it **phase by phase** following the
15-phase roadmap on page 18 of that PDF.

## Working agreement (IMPORTANT — follow these)

1. **Build one full PHASE at a time.** Implement all sub-steps of a phase in one pass,
   narrating each, verify it works, then **pause and wait for the user's "go"** before
   the next phase. Do not pause between sub-steps within a phase.
2. **No `Co-Authored-By` trailer in commits.** All commits are authored solely by the
   user (Amresh Yadav). The user does not want "claude" appearing as a GitHub contributor.
3. **Verify every step by running it** (TestClient / scripts / `docker compose`) before
   reporting it done. Show the evidence.
4. **Commit + push after each phase** (and update `docs/PROGRESS.md` + the roadmap table
   in `README.md`).
5. Keep scope to the current phase only — don't build ahead into later phases.

## Current status (keep this line updated)

- ✅ **Phase 1 — Foundation & Setup** (monorepo, docker-compose, common pkg, per-service config)
- ✅ **Phase 2 — API Gateway** (FastAPI scaffold, JWT auth, rate limiting, proxying)
- ✅ **Phase 3 — Auth Service** (async SQLAlchemy + Alembic, register/login/refresh/logout, RBAC)
- ✅ **Phase 4 — Database Schema** (central `db/` pkg `echoscope_db`: all 8 tables, migrations, Faker seed)
- ✅ **Phase 5 — Kafka Setup** (central `kafka/` pkg `echoscope_kafka`: topics, producer, consumer base + DLT)
- ✅ **Phase 6 — Mention Collection Service** (keyword CRUD, pluggable scrapers, dedup, Celery, Kafka publish)
- ✅ **Phase 7 — NLP Service** (mention-created consumer; VADER sentiment default, optional RoBERTa/spaCy/GPT; publishes sentiment-processed)
- ⏭️ **NEXT: Phase 8 — Analytics Service** (consume sentiment-processed, aggregation, spike detection, REST APIs, competitor scoring)

See `docs/PROGRESS.md` for full detail on what was built and what each next phase entails.

## Tech stack & conventions

- **Backend:** FastAPI (Python). Local Python is **3.13**; HLD targets 3.11 — containerize
  NLP (Phase 7) on `python:3.11` for ML libs.
- **Deps:** pip + venv + `requirements.txt` per service. Shared code in `common/`
  (package `echoscope_common`, installed via `-e ../common`).
- **Infra (docker-compose):** PostgreSQL 15, Redis 7, Kafka 3.6 (Confluent) + Zookeeper.
- **Shared utilities** (`echoscope_common`): `configure_logging` (JSON logs),
  `BaseAppSettings`/`load_settings` (config), `AppError` hierarchy, `BaseSchema`/`HealthResponse`,
  correlation-ID contextvar, UUID helpers.
- **Shared DB models** (`echoscope_db`, the `db/` package): ALL 8 SQLAlchemy models +
  the single Alembic migration chain (`db/alembic`) + `db/seed.py`. Services import models
  from here (e.g. `from echoscope_db.models import User`); do NOT add per-service Alembic.
- **Shared Kafka utils** (`echoscope_kafka`, the `kafka/` package): topic specs + `ensure_topics`,
  `EventProducer` (auto event_id/timestamp, retry), `BaseConsumer` (manual commit + DLT).
  Topics already created on the broker. Use `aiokafka`. Services import from `echoscope_kafka`.
- **JWT contract:** tokens are HS256 with claims `sub` (user_id), `role`, `org_id`.
  The gateway validates these; the Auth service (Phase 3) issues them.
- **GitHub:** https://github.com/amreshkyadav998/EchoscopeAI (branch `main`).

## Environment & quick commands

```bash
# Infrastructure (run from repo root)
docker compose up -d              # start postgres, redis, kafka, zookeeper
docker compose ps                 # all should be "healthy"
docker compose down               # stop (data persists in volumes; -v to wipe)

# Python venv lives at repo root (.venv). Install a service's deps:
.venv/Scripts/python.exe -m pip install -r <service>/requirements.txt

# Run the API Gateway locally
cd api-gateway && ../.venv/Scripts/uvicorn main:app --port 8000   # /docs for OpenAPI

# Test a service's config loads
.venv/Scripts/python.exe <service>/config.py
```

Host ports: Postgres **`5433`** (native PG 17 holds 5432 on this machine), Redis `6379`,
Kafka `29092` (in-network: `kafka:9092`). From the host use **`127.0.0.1`** not `localhost`
for Postgres (container publishes IPv4-only; `localhost` may resolve to IPv6 on Windows).
Apply auth migrations: `cd auth-service && DB_URL=postgresql+asyncpg://echoscope:echoscope@127.0.0.1:5433/echoscope JWT_SECRET=dev ../.venv/Scripts/python -m alembic upgrade head`
Service ports: gateway 8000, auth 8001, mention 8002, nlp 8003, analytics 8004,
notification 8005, report 8006.

## Repo layout

`api-gateway/` `auth-service/` `mention-service/` `nlp-service/` `analytics-service/`
`notification-service/` `report-service/` `frontend/` · `common/` (shared pkg) ·
`kafka/` `monitoring/` `nginx/` · `docs/` (HLD + PROGRESS.md) · `docker-compose.yml`
