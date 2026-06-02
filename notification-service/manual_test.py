"""Manual end-to-end check for Phase 9 (WebSockets + Redis bridge). Run against live Redis.

  cd notification-service && ../.venv/Scripts/python manual_test.py
"""

import asyncio
import json
import time
import uuid
import warnings

warnings.filterwarnings("ignore")

import jwt
import redis as redissync
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.bridge import dashboard_bridge
from app.redis_client import close_redis, dashboard_channel, ensure_redis, get_redis
from config import get_settings

SECRET = get_settings().jwt_secret
REDIS_URL = get_settings().redis_url
ORG = str(uuid.uuid4())


def token(org_id=ORG, secret=SECRET):
    return jwt.encode(
        {"sub": str(uuid.uuid4()), "role": "analyst", "org_id": org_id, "exp": int(time.time()) + 900},
        secret, algorithm="HS256",
    )


out = []


# ── Block A: Kafka->Redis bridge (async, own loop) ──
async def block_a():
    ensure_redis(REDIS_URL)
    pubsub = get_redis().pubsub()
    await pubsub.subscribe(dashboard_channel(ORG))
    await asyncio.sleep(0.2)
    # bridge.handle publishes the analytics-updated event to the org's dashboard channel
    await dashboard_bridge().handle({"org_id": ORG, "window": "7d", "metrics": {"mention_count": 42}})
    received = None
    deadline = time.time() + 5
    while time.time() < deadline:
        m = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1)
        if m:
            received = json.loads(m["data"])
            break
    await pubsub.unsubscribe(dashboard_channel(ORG))
    await pubsub.aclose()
    await close_redis()  # reset module client so TestClient re-inits on its own loop
    assert received and received["type"] == "metrics_update" and received["payload"]["metrics"]["mention_count"] == 42
    out.append("bridge: analytics-updated -> Redis ws:channel published (type=metrics_update)")


asyncio.run(block_a())


# ── Block B: WebSocket endpoints (TestClient) ──
sync_redis = redissync.Redis.from_url(REDIS_URL, decode_responses=True)

with TestClient(app=__import__("main").app) as client:
    # auth: missing token -> rejected
    try:
        with client.websocket_connect("/ws/dashboard"):
            pass
        raise AssertionError("expected rejection without token")
    except WebSocketDisconnect:
        out.append("/ws/dashboard without token -> rejected (1008)")

    # auth: invalid token -> rejected
    try:
        with client.websocket_connect("/ws/dashboard?token=not.a.jwt"):
            pass
        raise AssertionError("expected rejection with bad token")
    except WebSocketDisconnect:
        out.append("/ws/dashboard with invalid token -> rejected")

    # valid token -> connect, receive a forwarded message, ping/pong
    with client.websocket_connect(f"/ws/dashboard?token={token()}") as ws:
        sync_redis.publish(dashboard_channel(ORG), json.dumps({"type": "metrics_update", "payload": {"n": 7}}))
        data = json.loads(ws.receive_text())
        assert data["type"] == "metrics_update" and data["payload"]["n"] == 7
        out.append("/ws/dashboard valid token -> receives forwarded Redis message")
        ws.send_text(json.dumps({"type": "ping"}))
        assert json.loads(ws.receive_text())["type"] == "pong"
        out.append("/ws/dashboard ping -> pong keepalive")

    # /ws/alerts forwards from the alerts channel
    with client.websocket_connect(f"/ws/alerts?token={token()}") as ws:
        sync_redis.publish(f"ws:alerts:{ORG}", json.dumps({"type": "alert", "payload": {"keyword": "BrandX"}}))
        data = json.loads(ws.receive_text())
        assert data["type"] == "alert" and data["payload"]["keyword"] == "BrandX"
        out.append("/ws/alerts valid token -> receives forwarded alert")

    # org isolation: a different org's channel must NOT reach this client
    with client.websocket_connect(f"/ws/dashboard?token={token()}") as ws:
        sync_redis.publish(dashboard_channel(str(uuid.uuid4())), json.dumps({"type": "metrics_update", "payload": {}}))
        sync_redis.publish(dashboard_channel(ORG), json.dumps({"type": "metrics_update", "payload": {"mine": True}}))
        data = json.loads(ws.receive_text())  # should be ours, not the other org's
        assert data["payload"].get("mine") is True
        out.append("org isolation: client only receives its own org's channel")

print("\n".join("PASS  " + s for s in out))
print("\nALL PHASE 9 CHECKS PASSED")
