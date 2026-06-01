"""Manual end-to-end check for Phase 6 (run against the live stack).

  cd mention-service && ../.venv/Scripts/python manual_test.py
(reads DB_URL/REDIS_URL/KAFKA_BROKERS from .env)
"""

import asyncio
import json
import uuid
import warnings

warnings.filterwarnings("ignore")

from aiokafka import AIOKafkaConsumer
from httpx import ASGITransport, AsyncClient

from app.db import SessionLocal
from app.pipeline import run_scrape
from app.redis_client import claim_url, ensure_redis
from config import get_settings
from echoscope_db.models import Organization, Role, User
from main import app

BROKERS = get_settings().kafka_brokers
REDIS = get_settings().redis_url


async def main() -> None:
    out = []
    async with SessionLocal() as db:
        org = Organization(name=f"TestCo {uuid.uuid4().hex[:8]}", slug=f"testco-{uuid.uuid4().hex[:8]}", max_keywords=3)
        db.add(org)
        await db.flush()
        user = User(email=f"owner-{uuid.uuid4().hex[:8]}@example.com", password_hash="x", full_name="Owner", role=Role.admin, org_id=org.id)
        db.add(user)
        await db.commit()
        await db.refresh(org)
        await db.refresh(user)
        ORG, USER = str(org.id), str(user.id)
    H = {"X-User-Id": USER, "X-Role": "admin", "X-Org-Id": ORG}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        assert (await c.get("/health")).json()["service"] == "mention-service"
        out.append("health ok")

        ids = []
        for kw in ["BrandX", "ProductY", "CompanyZ"]:
            r = await c.post("/api/v1/keywords", headers=H, json={"keyword": kw, "sources": ["mock"], "alert_threshold": 5})
            assert r.status_code == 201, r.text
            ids.append(r.json()["id"])
        out.append("create 3 keywords -> 201")
        assert (await c.post("/api/v1/keywords", headers=H, json={"keyword": "OverLimit"})).status_code == 403
        out.append("4th over max_keywords=3 -> 403")
        assert (await c.post("/api/v1/keywords", json={"keyword": "NoAuth"})).status_code == 401
        out.append("no gateway headers -> 401")
        assert (await c.get("/api/v1/keywords", headers=H)).json()["total"] == 3
        out.append("list keywords -> 3")

        ensure_redis(REDIS)
        url = f"https://example.com/{uuid.uuid4().hex}"
        assert (await claim_url(url)) is True and (await claim_url(url)) is False
        out.append("dedup: same URL True then False")

        r1 = await run_scrape(ids)
        assert r1["inserted"] == 15, r1
        out.append(f"run_scrape -> inserted=15 dups={r1['duplicates']}")
        r2 = await run_scrape(ids)
        assert r2["inserted"] == 15, r2
        out.append("run_scrape again -> +15 (fresh URLs)")

        assert (await c.get("/api/v1/mentions", headers=H, params={"page_size": 100})).json()["total"] == 30
        out.append("GET /mentions -> 30 total")
        assert (await c.get("/api/v1/mentions", headers=H, params={"source": "mock"})).json()["total"] == 30
        out.append("GET /mentions?source=mock -> 30")

        cons = AIOKafkaConsumer(
            "mention-created", bootstrap_servers=BROKERS, group_id=f"v-{uuid.uuid4()}",
            auto_offset_reset="earliest", value_deserializer=lambda b: json.loads(b.decode()),
        )
        await cons.start()
        seen = 0
        try:
            async def scan():
                nonlocal seen
                async for m in cons:
                    if m.value.get("org_id") == ORG:
                        seen += 1
                        if seen >= 30:
                            return
            await asyncio.wait_for(scan(), timeout=15)
        except asyncio.TimeoutError:
            pass
        finally:
            await cons.stop()
        assert seen == 30, f"saw {seen}"
        out.append(f"Kafka mention-created for org = {seen}")

        r = await c.post("/api/v1/mentions/scrape", headers=H, json={"keyword_ids": ids})
        assert r.status_code == 202 and r.json()["job_id"]
        out.append("POST /mentions/scrape -> 202 queued")
        assert (await c.delete(f"/api/v1/keywords/{ids[0]}", headers=H)).status_code == 200
        assert (await c.get("/api/v1/keywords", headers=H)).json()["total"] == 2
        out.append("delete keyword -> 2")

    print("\n".join("PASS  " + s for s in out))
    print("\nALL PHASE 6 CHECKS PASSED")


if __name__ == "__main__":
    asyncio.run(main())
