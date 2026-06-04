"""Manual end-to-end check for Phase 11 (Report Service). Run against the live stack.

  cd report-service && ../.venv/Scripts/python manual_test.py
"""

import asyncio
import json
import uuid
import warnings
from datetime import datetime, timedelta, timezone

warnings.filterwarnings("ignore")

from httpx import ASGITransport, AsyncClient
from sqlalchemy import insert, select

from app.db import engine
from app.generate import generate_report
from config import get_settings
from echoscope_db.models import Keyword, Mention, Organization, Report, SentimentResult, User
from echoscope_kafka import REPORT_GENERATED
from main import app

BROKERS = get_settings().kafka_brokers


async def _seed_org() -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    async with engine.begin() as conn:
        org_id = (await conn.execute(insert(Organization.__table__).values(
            name=f"Rpt {uuid.uuid4().hex[:8]}", slug=f"rpt-{uuid.uuid4().hex[:8]}", max_keywords=5
        ).returning(Organization.__table__.c.id))).scalar_one()
        user_id = (await conn.execute(insert(User.__table__).values(
            email=f"u-{uuid.uuid4().hex[:8]}@x.com", password_hash="x", full_name="U", role="admin", org_id=org_id
        ).returning(User.__table__.c.id))).scalar_one()
        kw_id = (await conn.execute(insert(Keyword.__table__).values(
            org_id=org_id, keyword="BrandX", sources=["mock"], created_by=user_id
        ).returning(Keyword.__table__.c.id))).scalar_one()
        for i in range(8):
            m_id = (await conn.execute(insert(Mention.__table__).values(
                org_id=org_id, keyword_id=kw_id, source="mock",
                source_url=f"https://example.com/{uuid.uuid4().hex}", content=f"mention {i}",
                published_at=now - timedelta(days=i % 4),
            ).returning(Mention.__table__.c.id))).scalar_one()
            await conn.execute(insert(SentimentResult.__table__).values(
                mention_id=m_id, sentiment=("positive" if i % 2 else "negative"),
                confidence=0.9, positive_score=0.8, negative_score=0.1, neutral_score=0.1,
                model_version="vader-3.3",
            ))
    return str(org_id), str(user_id)


async def main() -> None:
    out = []
    ORG, USER = await _seed_org()
    H = {"X-User-Id": USER, "X-Role": "admin", "X-Org-Id": ORG}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        assert (await c.get("/health")).json()["service"] == "report-service"
        out.append("health ok")

        assert (await c.post("/api/v1/reports", json={"type": "csv"})).status_code == 401
        out.append("POST /reports without headers -> 401")

        # CSV report: queue -> generate -> download
        r = await c.post("/api/v1/reports", headers=H, json={"type": "csv", "filters": {}})
        assert r.status_code == 202 and r.json()["status"] == "queued"
        csv_id = r.json()["report_id"]
        out.append(f"POST /reports (csv) -> 202 queued ({csv_id[:8]}..)")

        res = await generate_report(csv_id)  # what the Celery worker runs
        assert res["rows"] == 8
        out.append(f"generate_report (csv) -> done, rows={res['rows']}, {res['size']} bytes")

        got = (await c.get(f"/api/v1/reports/{csv_id}", headers=H)).json()
        assert got["status"] == "done" and got["download_url"] and got["file_size_bytes"] > 0
        out.append(f"GET /reports/{{id}} -> done, download_url set, size={got['file_size_bytes']}")

        dl = await c.get(f"/api/v1/reports/{csv_id}/download", headers=H)
        assert dl.status_code == 200 and b"mention_id" in dl.content
        out.append("GET /reports/{id}/download -> CSV streamed (has header row)")

        # PDF report
        r = await c.post("/api/v1/reports", headers=H, json={"type": "pdf", "filters": {}})
        pdf_id = r.json()["report_id"]
        await generate_report(pdf_id)
        dl = await c.get(f"/api/v1/reports/{pdf_id}/download", headers=H)
        assert dl.status_code == 200 and dl.content[:4] == b"%PDF"
        out.append(f"PDF report -> generated + downloaded (valid %PDF, {len(dl.content)} bytes)")

        lst = (await c.get("/api/v1/reports", headers=H)).json()
        assert lst["total"] >= 2
        out.append(f"GET /reports -> total={lst['total']}")

        sch = await c.post("/api/v1/reports/schedule", headers=H, json={"cron": "daily", "format": "pdf", "filters": {}})
        assert sch.status_code == 202 and sch.json()["schedule_id"]
        out.append("POST /reports/schedule -> 202 schedule_id")

        assert (await c.delete(f"/api/v1/reports/{csv_id}", headers=H)).status_code == 200
        assert (await c.get(f"/api/v1/reports/{csv_id}", headers=H)).status_code == 404
        out.append("DELETE /reports/{id} -> removed (404 after)")

    # report-generated Kafka event for the PDF report
    from aiokafka import AIOKafkaConsumer

    cons = AIOKafkaConsumer(REPORT_GENERATED, bootstrap_servers=BROKERS, group_id=f"v-{uuid.uuid4()}",
                            auto_offset_reset="earliest", value_deserializer=lambda b: json.loads(b.decode()))
    await cons.start()
    found = False
    try:
        async def scan():
            nonlocal found
            async for m in cons:
                if m.value.get("report_id") == pdf_id:
                    found = True
                    return
        await asyncio.wait_for(scan(), timeout=15)
    except asyncio.TimeoutError:
        pass
    finally:
        await cons.stop()
    assert found
    out.append("Kafka report-generated event received")

    await engine.dispose()
    print("\n".join("PASS  " + s for s in out))
    print("\nALL PHASE 11 CHECKS PASSED")


if __name__ == "__main__":
    asyncio.run(main())
