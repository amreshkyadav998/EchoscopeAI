"""Reverse-proxy router (HLD section 4.1, Phase 2.4).

Routes ``/api/v1/*`` requests to the correct downstream service over httpx with a
timeout and 3x retry on transient errors. The raw ``Authorization`` header is NOT
forwarded; instead the validated user context is injected as ``X-User-*`` headers,
and the correlation ID is propagated.
"""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Request, Response

from app.dependencies.auth import CurrentUser, get_current_user
from app.dependencies.rate_limit import rate_limit
from config import get_settings
from echoscope_common import AppError, NotFoundError, get_correlation_id

router = APIRouter(prefix="/api/v1")

# Longest-prefix-first mapping of public path -> service key in settings.service_urls
ROUTE_MAP: list[tuple[str, str]] = [
    ("/api/v1/auth", "auth"),
    ("/api/v1/keywords", "mention"),
    ("/api/v1/mentions", "mention"),
    ("/api/v1/nlp", "nlp"),
    ("/api/v1/analytics", "analytics"),
    ("/api/v1/alerts", "notification"),
    ("/api/v1/reports", "report"),
]

# Public routes — no JWT required (chicken-and-egg: you have no token yet)
_PUBLIC_PATHS = {
    "/api/v1/auth/register",
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
}


def _is_public(path: str) -> bool:
    return path.rstrip("/") in _PUBLIC_PATHS


# Request headers we never forward upstream (hop-by-hop + auth stripped on purpose)
_EXCLUDED_REQUEST_HEADERS = {
    "host",
    "content-length",
    "authorization",
    "connection",
    "keep-alive",
    "transfer-encoding",
}
# Response headers we strip before returning to the client
_EXCLUDED_RESPONSE_HEADERS = {"content-length", "transfer-encoding", "connection"}

_MAX_ATTEMPTS = 3
_TRANSIENT = (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout, httpx.PoolTimeout)


class ServiceUnavailableError(AppError):
    status_code = 503
    error_code = "service_unavailable"
    default_message = "Downstream service is unavailable"


def resolve_service(path: str) -> str:
    """Return the service key for a request path, or raise 404 if unmapped."""
    for prefix, service in ROUTE_MAP:
        if path == prefix or path.startswith(prefix + "/"):
            return service
    raise NotFoundError(f"No route configured for path: {path}")


def _build_forward_headers(request: Request, user: CurrentUser | None) -> dict[str, str]:
    # Use lowercase keys throughout so injected headers cleanly overwrite any
    # copied ones (HTTP header names are case-insensitive; mixing cases in a dict
    # would create duplicates that httpx joins with commas).
    headers = {
        k.lower(): v
        for k, v in request.headers.items()
        if k.lower() not in _EXCLUDED_REQUEST_HEADERS
    }
    if user is not None:
        headers["x-user-id"] = user.user_id
        headers["x-role"] = user.role
        headers["x-org-id"] = user.org_id
    cid = get_correlation_id()
    if cid:
        headers["x-correlation-id"] = cid
    return headers


async def _send_with_retry(client: httpx.AsyncClient, req: httpx.Request) -> httpx.Response:
    last_exc: Exception | None = None
    for _ in range(_MAX_ATTEMPTS):
        try:
            return await client.send(req)
        except _TRANSIENT as exc:
            last_exc = exc
    raise ServiceUnavailableError(
        "Downstream service did not respond after retries"
    ) from last_exc


@router.api_route(
    "/{full_path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
)
async def proxy(full_path: str, request: Request) -> Response:
    # Public auth routes (register/login/refresh) bypass JWT + rate limiting.
    user: CurrentUser | None = None
    if not _is_public(request.url.path):
        user = await get_current_user(request)  # raises 401 if missing/invalid
        await rate_limit(user=user)             # raises 429 if over limit

    service = resolve_service(request.url.path)
    base_url = get_settings().service_urls[service]

    target = base_url.rstrip("/") + request.url.path
    if request.url.query:
        target += "?" + request.url.query

    body = await request.body()
    client: httpx.AsyncClient = request.app.state.http_client
    upstream_req = client.build_request(
        method=request.method,
        url=target,
        headers=_build_forward_headers(request, user),
        content=body,
    )
    upstream_resp = await _send_with_retry(client, upstream_req)

    resp_headers = {
        k: v
        for k, v in upstream_resp.headers.items()
        if k.lower() not in _EXCLUDED_RESPONSE_HEADERS
    }
    return Response(
        content=upstream_resp.content,
        status_code=upstream_resp.status_code,
        headers=resp_headers,
        media_type=upstream_resp.headers.get("content-type"),
    )
