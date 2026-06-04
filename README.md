# EchoscopeAI — AI-Powered Social Listening & Reputation Monitoring Platform

A production-grade, event-driven microservices platform that continuously monitors public
internet sources, detects brand/product/company mentions, performs AI-based sentiment
analysis, triggers real-time alerts, and visualises analytics via live dashboards.

> Built from the High-Level Design in `docs/AI_Social_Listening_Platform_HLD_v2.pdf`.

## Architecture at a glance

Clients → Nginx → **API Gateway** → 7 microservices, communicating asynchronously over
**Apache Kafka** and synchronously over **gRPC**. **Redis** handles caching, sessions, rate
limiting, and WebSocket pub/sub. **PostgreSQL** is the system of record. All services run as
**Docker** containers.

## Repository layout

| Path | Service / Purpose | Port |
|------|-------------------|------|
| `frontend/` | React + TypeScript dashboard | — |
| `api-gateway/` | Single entry point: JWT, rate limiting, routing | 8000 |
| `auth-service/` | Registration, login, JWT, RBAC | 8001 |
| `mention-service/` | Keyword tracking + scraping pipeline | 8002 |
| `nlp-service/` | Sentiment, NER, summarisation | 8003 |
| `analytics-service/` | Aggregation, trends, spike detection | 8004 |
| `notification-service/` | WebSockets, alerts, email | 8005 |
| `report-service/` | PDF/CSV report generation | 8006 |
| `common/` | Shared utilities (logger, config, exceptions, models) | — |
| `kafka/` | Kafka topic definitions & helper scripts | — |
| `monitoring/` | Prometheus, Grafana, Loki config | — |
| `nginx/` | Reverse-proxy config | — |
| `docs/` | Design documents | — |
| `docker-compose.yml` | Local development stack | — |

## Technology stack

FastAPI (Python 3.11+) · React + TypeScript · Apache Kafka · Redis 7 · PostgreSQL 15 ·
gRPC · Docker · Prometheus + Grafana.

## Development roadmap (15 phases)

| Phase | Focus | Status |
|-------|-------|--------|
| **1** | **Foundation & Setup** | ✅ done |
| **2** | **API Gateway** | ✅ done |
| **3** | **Auth Service** | ✅ done |
| **4** | **Database Schema** | ✅ done |
| **5** | **Kafka Setup** | ✅ done |
| **6** | **Mention Collection Service** | ✅ done |
| **7** | **NLP Service** | ✅ done |
| **8** | **Analytics Service** | ✅ done |
| **9** | **Real-Time WebSockets** | ✅ done |
| **10** | **Notification Service** | ✅ done |
| **11** | **Report Service** | ✅ done |
| 12 | gRPC Communication | ⬜ |
| 13 | Frontend Development | ⬜ |
| 14 | Monitoring & Logging | ⬜ |
| 15 | AWS Deployment + CI/CD | ⬜ |

## Getting started (local)

```bash
# Bring up infrastructure (Postgres, Redis, Kafka, Zookeeper)
docker compose up -d

# Check everything is healthy
docker compose ps
```

> Service containers and application code are added incrementally per phase.
