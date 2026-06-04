"""gRPC client helpers: channels, retry on UNAVAILABLE, gRPC→HTTP status mapping."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

import grpc

T = TypeVar("T")

# gRPC status code -> HTTP status (HLD §12: NOT_FOUND→404, UNAVAILABLE→503, ...)
_HTTP_FOR = {
    grpc.StatusCode.OK: 200,
    grpc.StatusCode.INVALID_ARGUMENT: 400,
    grpc.StatusCode.UNAUTHENTICATED: 401,
    grpc.StatusCode.PERMISSION_DENIED: 403,
    grpc.StatusCode.NOT_FOUND: 404,
    grpc.StatusCode.ALREADY_EXISTS: 409,
    grpc.StatusCode.DEADLINE_EXCEEDED: 504,
    grpc.StatusCode.UNAVAILABLE: 503,
}


def grpc_status_to_http(code: grpc.StatusCode) -> int:
    return _HTTP_FOR.get(code, 500)


def channel(target: str) -> grpc.aio.Channel:
    """Open an async insecure channel (internal-only network)."""
    return grpc.aio.insecure_channel(target)


async def with_retry(
    call: Callable[[], Awaitable[T]], *, attempts: int = 3, base_delay: float = 0.3
) -> T:
    """Await ``call()``; retry with exponential backoff only on UNAVAILABLE."""
    last: Exception | None = None
    for i in range(attempts):
        try:
            return await call()
        except grpc.aio.AioRpcError as exc:
            last = exc
            if exc.code() == grpc.StatusCode.UNAVAILABLE and i < attempts - 1:
                await asyncio.sleep(base_delay * (2**i))
                continue
            raise
    raise last  # pragma: no cover
