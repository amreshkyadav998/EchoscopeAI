# Notification Service (:8005)

Real-time delivery + (Phase 10) alerting. Phase 9 = WebSockets + Kafka→Redis bridge.

## Phase 9 — Real-time WebSockets (HLD §4.6)

- `app/ws.py` — `/ws/dashboard` and `/ws/alerts`. JWT validated on the upgrade handshake
  via the `token` query param (`app/security.py`); client subscribes to its org's Redis
  channel and messages are forwarded live. Ping→pong keepalive. Org-isolated.
- `app/bridge.py` — Kafka→Redis bridge: `analytics-updated` → `ws:channel:{org}`
  (`metrics_update`), `alert-triggered` → `ws:alerts:{org}` (`alert`). Runs as lifespan
  background consumers (group `notification-service`).
- `app/redis_client.py` — pub/sub helpers + channel names.
- Any service instance can serve any user (shared Redis channels, no sticky sessions).

Frontend hook: `frontend/src/hooks/useWebSocket.ts` (auto-reconnect w/ backoff+jitter,
ping/pong) — the full frontend app is Phase 13.

## Phase 10 (next)
Alert-rule CRUD, evaluation engine, SendGrid email, alert history.

## Run (host)

```bash
cp .env.example .env   # set JWT_SECRET to match auth-service
../.venv/Scripts/uvicorn main:app --port 8005
```

`manual_test.py` is an end-to-end check (WS auth, forwarding, ping/pong, isolation, bridge).
