"""Manual end-to-end check for Phase 7 (run against the live stack).

  cd nlp-service && ../.venv/Scripts/python manual_test.py
"""

import asyncio
import json
import uuid
import warnings

warnings.filterwarnings("ignore")

from aiokafka import AIOKafkaConsumer
from httpx import ASGITransport, AsyncClient
from sqlalchemy import insert, select

from app.db import engine
from app.processor import process_event
from config import get_settings
from echoscope_db.models import Keyword, Mention, Organization, SentimentResult, User
from echoscope_kafka import SENTIMENT_PROCESSED, EventProducer
from main import app

BROKERS = get_settings().kafka_brokers
LONG = ("This product is absolutely fantastic and I love it. " * 12)  # >500 chars, positive


async def main() -> None:
    out = []
    H = {"X-User-Id": str(uuid.uuid4()), "X-Role": "analyst", "X-Org-Id": str(uuid.uuid4())}

    # ── REST /analyze ──
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        assert (await c.get("/health")).json()["service"] == "nlp-service"
        out.append("health ok")

        pos = (await c.post("/api/v1/nlp/analyze", headers=H, json={"text": "I love this, it's amazing and wonderful!"})).json()
        neg = (await c.post("/api/v1/nlp/analyze", headers=H, json={"text": "This is terrible, awful and I hate it."})).json()
        neu = (await c.post("/api/v1/nlp/analyze", headers=H, json={"text": "The meeting is scheduled for 3pm on Tuesday."})).json()
        assert pos["sentiment"] == "positive", pos
        assert neg["sentiment"] == "negative", neg
        assert neu["sentiment"] == "neutral", neu
        out.append(f"/analyze sentiment: positive/negative/neutral OK (kw sample={pos['keywords'][:3]})")

        assert (await c.post("/api/v1/nlp/analyze", json={"text": "x"})).status_code == 401
        out.append("/analyze without gateway headers -> 401")

        b = await c.post("/api/v1/nlp/batch", headers=H, json={"texts": ["great job", "this sucks", "ok fine"]})
        assert b.status_code == 202
        job_id = b.json()["job_id"]
        jr = (await c.get(f"/api/v1/nlp/jobs/{job_id}", headers=H)).json()
        assert jr["progress"] == 3 and len(jr["results"]) == 3
        out.append(f"/batch + /jobs: 3 texts analyzed (status={jr['status']})")

        # ── consume pipeline: mention-created event -> process_event -> sentiment-processed ──
        async with engine.begin() as conn:
            org_id = (await conn.execute(insert(Organization.__table__).values(name=f"Nlp {uuid.uuid4().hex[:8]}", slug=f"nlp-{uuid.uuid4().hex[:8]}", max_keywords=5).returning(Organization.__table__.c.id))).scalar_one()
            user_id = (await conn.execute(insert(User.__table__).values(email=f"u-{uuid.uuid4().hex[:8]}@x.com", password_hash="x", full_name="U", role="admin", org_id=org_id).returning(User.__table__.c.id))).scalar_one()
            kw_id = (await conn.execute(insert(Keyword.__table__).values(org_id=org_id, keyword="NlpKw", sources=["mock"], created_by=user_id).returning(Keyword.__table__.c.id))).scalar_one()
            mention_id = (await conn.execute(insert(Mention.__table__).values(org_id=org_id, keyword_id=kw_id, source="mock", source_url=f"https://example.com/{uuid.uuid4().hex}", content=LONG, published_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc)).returning(Mention.__table__.c.id))).scalar_one()
        mention_id = str(mention_id)

        producer = EventProducer(BROKERS)
        await producer.start()
        try:
            event = {"event_id": str(uuid.uuid4()), "mention_id": mention_id, "org_id": str(org_id), "content": LONG}
            assert await process_event(event, producer) is True
            out.append("process_event -> sentiment_results written + sentiment-processed published")
            # idempotent
            assert await process_event(event, producer) is False
            out.append("process_event again -> skipped (1:1 idempotent)")
        finally:
            await producer.stop()

        # sentiment_results row exists with a summary (content >500 chars)
        async with engine.begin() as conn:
            row = (await conn.execute(select(SentimentResult.__table__).where(SentimentResult.__table__.c.mention_id == mention_id))).first()
        assert row is not None and row.sentiment == "positive" and row.summary
        out.append(f"sentiment_results: sentiment={row.sentiment}, model={row.model_version}, summary set")

        # GET /summary
        s = (await c.get(f"/api/v1/nlp/summary/{mention_id}", headers=H)).json()
        assert s["summary"]
        out.append("GET /nlp/summary/{id} -> summary returned")

    # sentiment-processed event for our mention
    cons = AIOKafkaConsumer(SENTIMENT_PROCESSED, bootstrap_servers=BROKERS, group_id=f"v-{uuid.uuid4()}",
                            auto_offset_reset="earliest", value_deserializer=lambda b: json.loads(b.decode()))
    await cons.start()
    seen = None
    try:
        async def scan():
            nonlocal seen
            async for m in cons:
                if m.value.get("mention_id") == mention_id:
                    seen = m.value
                    return
        await asyncio.wait_for(scan(), timeout=15)
    except asyncio.TimeoutError:
        pass
    finally:
        await cons.stop()
    assert seen and seen["sentiment"] == "positive", seen
    out.append("Kafka sentiment-processed event received (sentiment=positive)")

    print("\n".join("PASS  " + s for s in out))
    print("\nALL PHASE 7 CHECKS PASSED")


if __name__ == "__main__":
    asyncio.run(main())
