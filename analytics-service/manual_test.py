"""Manual end-to-end check for Phase 8 (run against the live stack, uses seed data).

  cd analytics-service && ../.venv/Scripts/python manual_test.py
"""

import asyncio
import json
import uuid
import warnings
from datetime import datetime, timedelta, timezone

warnings.filterwarnings("ignore")

import pandas as pd
from aiokafka import AIOKafkaConsumer
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app import analytics as A
from app.cache import ensure_redis, get_redis
from app.db import engine
from app.publisher import publish_analytics_updates
from config import get_settings
from echoscope_db.models import Keyword, Mention
from echoscope_kafka import ANALYTICS_UPDATED, EventProducer
from main import app

BROKERS = get_settings().kafka_brokers


async def main() -> None:
    out = []

    # pick the org with the most mentions (seed data) + two of its keywords
    async with engine.connect() as conn:
        org_id = (
            await conn.execute(
                select(Mention.org_id).group_by(Mention.org_id).order_by(func.count().desc()).limit(1)
            )
        ).scalar_one()
        org_id = str(org_id)
        brands = (
            await conn.execute(select(Keyword.keyword).where(Keyword.org_id == org_id).limit(2))
        ).scalars().all()

    H = {"X-User-Id": str(uuid.uuid4()), "X-Role": "analyst", "X-Org-Id": org_id}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        assert (await c.get("/health")).json()["service"] == "analytics-service"
        out.append("health ok")

        ov = (await c.get("/api/v1/analytics/overview", headers=H)).json()
        assert ov["total_mentions"] > 0
        out.append(f"overview -> total={ov['total_mentions']}, pos%={ov['positive_pct']}, avg/day={ov['avg_per_day']}")

        tr = (await c.get("/api/v1/analytics/trends", headers=H, params={"granularity": "day"})).json()
        assert len(tr["datapoints"]) > 0
        out.append(f"trends(day) -> {len(tr['datapoints'])} datapoints")

        se = (await c.get("/api/v1/analytics/sentiment", headers=H)).json()
        assert se["positive"] + se["negative"] + se["neutral"] == ov["total_mentions"]
        out.append(f"sentiment -> pos={se['positive']} neg={se['negative']} neu={se['neutral']} (sums to total)")

        kw = (await c.get("/api/v1/analytics/keywords/top", headers=H, params={"limit": 5})).json()
        assert 1 <= len(kw["keywords"]) <= 5
        out.append(f"keywords/top -> {[k['word'] for k in kw['keywords']]}")

        sr = (await c.get("/api/v1/analytics/sources", headers=H)).json()
        assert len(sr["sources"]) > 0
        out.append(f"sources -> {[(s['name'], s['count']) for s in sr['sources']]}")

        comp = (await c.get("/api/v1/analytics/competitors", headers=H, params={"brands": brands})).json()
        assert len(comp["comparison"]) == len(brands)
        assert all(0.0 <= r["score"] <= 1.0 for r in comp["comparison"])
        out.append(f"competitors -> ranked {[(r['brand'], r['score']) for r in comp['comparison']]}")

        sp = (await c.get("/api/v1/analytics/spikes", headers=H)).json()
        assert "spikes" in sp
        out.append(f"spikes -> {len(sp['spikes'])} detected (threshold z>=2.0)")

        assert (await c.get("/api/v1/analytics/overview")).status_code == 401
        out.append("no gateway headers -> 401")

        # cache-aside: a cache key should now exist for this org
        ensure_redis(get_settings().redis_url)
        keys = [k async for k in get_redis().scan_iter(match=f"analytics:{org_id}:overview:*")]
        assert keys, "expected an overview cache key"
        out.append("cache-aside: overview result cached in Redis")

    # spike detection unit test (synthetic spike)
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = [{"keyword": "Surge", "published_at": base + timedelta(hours=h), "sentiment": "neutral",
             "positive_score": 0.1, "negative_score": 0.1, "source": "mock"} for h in range(24)]
    rows += [{"keyword": "Surge", "published_at": base + timedelta(hours=25), "sentiment": "positive",
              "positive_score": 0.9, "negative_score": 0.0, "source": "mock"} for _ in range(40)]
    spikes = A.detect_spikes(pd.DataFrame(rows), threshold=2.0)["spikes"]
    assert any(s["keyword"] == "Surge" for s in spikes), spikes
    out.append(f"detect_spikes: synthetic 40x spike flagged (z={spikes[0]['z_score']})")

    # publisher: one pass publishes analytics-updated per org
    producer = EventProducer(BROKERS)
    await producer.start()
    try:
        res = await publish_analytics_updates(producer)
        assert res["orgs"] > 0
        out.append(f"publish_analytics_updates -> {res['orgs']} orgs, {res['alerts']} alerts")
    finally:
        await producer.stop()

    cons = AIOKafkaConsumer(ANALYTICS_UPDATED, bootstrap_servers=BROKERS, group_id=f"v-{uuid.uuid4()}",
                            auto_offset_reset="earliest", value_deserializer=lambda b: json.loads(b.decode()))
    await cons.start()
    found = False
    try:
        async def scan():
            nonlocal found
            async for m in cons:
                if m.value.get("org_id") == org_id and "metrics" in m.value:
                    found = True
                    return
        await asyncio.wait_for(scan(), timeout=15)
    except asyncio.TimeoutError:
        pass
    finally:
        await cons.stop()
    assert found, "analytics-updated event not received"
    out.append("Kafka analytics-updated event received for org")

    print("\n".join("PASS  " + s for s in out))
    print("\nALL PHASE 8 CHECKS PASSED")


if __name__ == "__main__":
    asyncio.run(main())
