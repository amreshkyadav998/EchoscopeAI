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

## ⏭️ NEXT — Phase 3: Auth Service (`auth-service/`, ~3 days)

Issues the JWTs the gateway validates. Steps (HLD 4.2 / page 18):
1. **DB + Alembic** — async SQLAlchemy + asyncpg. Alembic migration for `users` +
   `organizations` (all constraints from schema in HLD §6).
2. **Registration** — email uniqueness, bcrypt hash (cost=12), create org + user in one
   transaction, (verification email stub for now).
3. **Login + JWT** — `bcrypt.checkpw`; access token HS256 15 min (claims `sub`/`role`/
   `org_id`); refresh token (UUID4) in Redis HASH, 7-day TTL.
4. **Refresh / Logout** — `/refresh` validates + rotates; `/logout` deletes Redis key
   (+ blacklist).
5. **RBAC** — role ENUM in DB; `require_role` dependency; role in JWT claim.

Endpoints (HLD §5.1): `POST /api/v1/auth/register|login|refresh|logout|change-password`,
`GET|PUT /api/v1/auth/me`.

> Note: DB tables for the *whole* system (8 tables) are formally Phase 4. Phase 3 only
> needs `users` + `organizations`; align column definitions with HLD §6 so Phase 4 just
> adds the rest.

## ⬜ Remaining phases (overview — see HLD page 18-20)

4. Database Schema (all 8 migrations, indexes, Faker seed data)
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
