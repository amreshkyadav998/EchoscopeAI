"""Periodic analytics publishing + spike alerting (HLD §4.5).

Every interval: for each active org, recompute metrics and publish `analytics-updated`;
if a keyword spiked (Z-score >= threshold), publish `alert-triggered`. A Redis debounce
key prevents duplicate spike alerts for the same keyword within the window.
"""

from __future__ import annotations

from sqlalchemy import select

from app.analytics import default_range, detect_spikes, load_frame, overview
from app.cache import get_redis
from app.db import engine
from config import get_settings
from echoscope_db.models import Mention
from echoscope_kafka import ALERT_TRIGGERED, ANALYTICS_UPDATED, EventProducer
from loguru import logger as log

SPIKE_DEBOUNCE_SECONDS = 600  # max 1 alert per keyword / 10 min


async def _active_org_ids() -> list[str]:
    async with engine.connect() as conn:
        rows = (await conn.execute(select(Mention.org_id).distinct())).scalars().all()
    return [str(r) for r in rows]


async def publish_analytics_updates(producer: EventProducer) -> dict[str, int]:
    """One pass: publish analytics-updated per org + alert-triggered on spikes."""
    settings = get_settings()
    from_date, to_date = default_range(7)
    orgs = await _active_org_ids()
    updated = 0
    alerts = 0
    redis = get_redis()

    for org_id in orgs:
        df = await load_frame(org_id, from_date, to_date)
        ov = overview(df, from_date, to_date)
        await producer.publish(
            ANALYTICS_UPDATED,
            {"org_id": org_id, "window": "7d", "metrics": ov},
            key=str(org_id),
        )
        updated += 1

        spikes = detect_spikes(df, threshold=settings.spike_threshold)["spikes"]
        for spike in spikes:
            debounce_key = f"alert:debounce:{org_id}:{spike['keyword']}"
            if await redis.set(debounce_key, "1", nx=True, ex=SPIKE_DEBOUNCE_SECONDS):
                await producer.publish(
                    ALERT_TRIGGERED,
                    {
                        "org_id": org_id,
                        "keyword": spike["keyword"],
                        "trigger_type": "spike",
                        "description": f"Mention spike {spike['magnitude']}x above normal "
                        f"(z-score: {spike['z_score']})",
                        "severity": "high" if spike["z_score"] >= 3 else "medium",
                        "metrics": spike,
                    },
                    key=str(org_id),
                )
                alerts += 1

    log.info("analytics published", orgs=updated, alerts=alerts)
    return {"orgs": updated, "alerts": alerts}
