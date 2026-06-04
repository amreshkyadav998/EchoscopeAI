# rpc — shared gRPC contracts (echoscope_rpc)

Internal service-to-service gRPC (HLD §9/§12): protos, generated stubs, client helpers.

## Contents

- `protos/analytics.proto`, `protos/nlp.proto` — service + message definitions
  (packages `analytics.v1`, `nlp.v1`).
- `echoscope_rpc/*_pb2.py`, `*_pb2_grpc.py` — generated stubs (committed; imports are
  rewritten to package-relative).
- `echoscope_rpc/client.py` — `channel()`, `with_retry()` (backoff on UNAVAILABLE),
  `grpc_status_to_http()` (NOT_FOUND→404, UNAVAILABLE→503, …).
- `generate.py` — regenerate stubs from the protos.

## Servers & clients

| Server (port) | RPCs | Called by |
|---------------|------|-----------|
| Analytics (:50051) | GetAnalyticsSummary, GetTrends, GetCurrentMetrics | Report (PDF), Notification (alert enrichment) |
| NLP (:50052) | GetSentimentBatch, GetEntitiesForMention | Report, Analytics |

Servers run alongside FastAPI in each service's lifespan (`enable_grpc`, `grpc_port`).
Clients are best-effort (degrade gracefully if the server is down).

## Regenerate stubs

```bash
cd rpc && ../.venv/Scripts/python generate.py
```
