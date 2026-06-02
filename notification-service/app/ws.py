"""WebSocket endpoints /ws/dashboard and /ws/alerts (HLD §4.6).

JWT is validated on the HTTP upgrade handshake via the `token` query param. Each
client subscribes to its org's Redis channel; any service instance can serve any
user because delivery rides the shared Redis channel (no sticky sessions).
"""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, WebSocket
from loguru import logger as log
from starlette.websockets import WebSocketDisconnect, WebSocketState

from app.redis_client import alerts_channel, dashboard_channel, ensure_redis
from app.security import org_from_token
from config import get_settings

router = APIRouter(tags=["websockets"])


async def _forward(pubsub, websocket: WebSocket) -> None:
    """Relay Redis pub/sub messages to the WebSocket client."""
    async for message in pubsub.listen():
        if message.get("type") == "message":
            await websocket.send_text(message["data"])


async def _serve(websocket: WebSocket, channel_fn) -> None:
    settings = get_settings()
    org_id = org_from_token(websocket.query_params.get("token"))
    if not org_id:
        await websocket.close(code=1008)  # policy violation (auth)
        return

    redis = ensure_redis(settings.redis_url)
    channel = channel_fn(org_id)
    pubsub = redis.pubsub()
    await pubsub.subscribe(channel)  # subscribe BEFORE accept so no early messages are missed

    await websocket.accept()
    forward_task = asyncio.create_task(_forward(pubsub, websocket))
    log.info("ws connected", channel=channel)
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except ValueError:
                continue
            if msg.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        pass
    finally:
        forward_task.cancel()
        try:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()
        except Exception:
            pass
        if websocket.client_state != WebSocketState.DISCONNECTED:
            await websocket.close()
        log.info("ws disconnected", channel=channel)


@router.websocket("/ws/dashboard")
async def ws_dashboard(websocket: WebSocket) -> None:
    await _serve(websocket, dashboard_channel)


@router.websocket("/ws/alerts")
async def ws_alerts(websocket: WebSocket) -> None:
    await _serve(websocket, alerts_channel)
