"""Manual end-to-end check for Phase 10 (alert rules + evaluation engine).

  cd notification-service && ../.venv/Scripts/python manual_test_phase10.py
"""

import asyncio
import json
import uuid
import warnings

warnings.filterwarnings("ignore")

from httpx import ASGITransport, AsyncClient
from sqlalchemy import insert, select

from app.db import engine
from app.evaluation import evaluate_event
from app.redis_client import alerts_channel, ensure_redis, get_redis
from config import get_settings
from echoscope_db.models import Alert, Organization, User
from main import app

REDIS_URL = get_settings().redis_url


async def main() -> None:
    out = []

    # setup: org + admin user
    async with engine.begin() as conn:
        org_id = (await conn.execute(insert(Organization.__table__).values(
            name=f"Notif {uuid.uuid4().hex[:8]}", slug=f"notif-{uuid.uuid4().hex[:8]}", max_keywords=5
        ).returning(Organization.__table__.c.id))).scalar_one()
        user_id = (await conn.execute(insert(User.__table__).values(
            email=f"admin-{uuid.uuid4().hex[:8]}@example.com", password_hash="x", full_name="Admin",
            role="admin", org_id=org_id,
        ).returning(User.__table__.c.id))).scalar_one()
    ORG, USER = str(org_id), str(user_id)
    H = {"X-User-Id": USER, "X-Role": "admin", "X-Org-Id": ORG}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        assert (await c.get("/health")).json()["service"] == "notification-service"
        out.append("health ok")

        # rule CRUD
        r = await c.post("/api/v1/alerts/rules", headers=H, json={
            "name": "High volume", "condition": {"type": "volume", "threshold": 10},
            "channels": ["websocket", "email"],
        })
        assert r.status_code == 201, r.text
        rule_id = r.json()["rule_id"]
        out.append(f"POST /alerts/rules -> 201 rule_id={rule_id[:8]}..")

        rules = (await c.get("/api/v1/alerts/rules", headers=H)).json()["rules"]
        assert any(rl["id"] == rule_id and rl["is_enabled"] for rl in rules)
        out.append(f"GET /alerts/rules -> {len(rules)} rule(s), enabled")

        upd = (await c.put(f"/api/v1/alerts/rules/{rule_id}", headers=H, json={"enabled": False})).json()
        assert upd["is_enabled"] is False
        await c.put(f"/api/v1/alerts/rules/{rule_id}", headers=H, json={"enabled": True})  # re-enable
        out.append("PUT /alerts/rules/{id} -> toggles enabled")

        assert (await c.post("/api/v1/alerts/rules", json={"name": "x", "condition": {}})).status_code == 401
        out.append("POST /alerts/rules without headers -> 401")

        # evaluation engine: analytics-updated metrics match the volume rule
        ensure_redis(REDIS_URL)
        pubsub = get_redis().pubsub()
        await pubsub.subscribe(alerts_channel(ORG))
        await asyncio.sleep(0.2)

        event = {"org_id": ORG, "window": "7d", "metrics": {"total_mentions": 50, "negative_pct": 0.1}}
        fired = await evaluate_event(event)
        assert fired == 1, fired
        out.append("evaluate_event -> 1 alert fired (volume rule matched)")

        # alert persisted
        async with engine.begin() as conn:
            cnt = (await conn.execute(select(Alert.__table__).where(Alert.__table__.c.org_id == org_id))).all()
        assert len(cnt) == 1
        out.append("alert persisted to DB (1 row)")

        # WS alerts channel received it
        received = None
        for _ in range(10):
            m = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1)
            if m:
                received = json.loads(m["data"])
                break
        await pubsub.unsubscribe(alerts_channel(ORG))
        await pubsub.aclose()
        assert received and received["type"] == "alert"
        out.append("alert pushed to WS alerts channel (type=alert)")

        # debounce: immediate re-evaluation fires nothing
        assert await evaluate_event(event) == 0
        out.append("evaluate_event again -> 0 (debounced 10 min)")

        # history
        hist = (await c.get("/api/v1/alerts/history", headers=H, params={"limit": 10})).json()
        assert len(hist["alerts"]) == 1 and hist["alerts"][0]["keyword"] == "all keywords"
        out.append(f"GET /alerts/history -> {len(hist['alerts'])} alert (keyset pagination)")

        # delete rule
        assert (await c.delete(f"/api/v1/alerts/rules/{rule_id}", headers=H)).status_code == 200
        assert len((await c.get("/api/v1/alerts/rules", headers=H)).json()["rules"]) == 0
        out.append("DELETE /alerts/rules/{id} -> removed (alerts cascade)")

    await engine.dispose()
    print("\n".join("PASS  " + s for s in out))
    print("\nALL PHASE 10 CHECKS PASSED")


if __name__ == "__main__":
    asyncio.run(main())
