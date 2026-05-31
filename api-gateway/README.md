# API Gateway (:8000)

Single entry point for all client HTTP + WebSocket traffic. Handles JWT validation, Redis
sliding-window rate limiting, request routing to downstream services (httpx), CORS/security
headers, and X-Correlation-ID generation.

_Implemented in Phase 2._
