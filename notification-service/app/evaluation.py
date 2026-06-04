"""Alert evaluation engine (HLD §4.6).

On an analytics-updated event: evaluate every enabled rule for the org against the
event metrics. On a match (debounced to max 1 alert/rule/10 min): persist an `alerts`
row, email the org admins, and push to the org's WS alerts channel.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from loguru import logger as log
from sqlalchemy import insert, select

from app.db import engine
from app.email import render_alert_html, send_alert_email
from app.redis_client import alerts_channel, ensure_redis, get_redis, publish_ws
from config import get_settings
from echoscope_db.models import Alert, AlertRule, Keyword, User

_alerts = Alert.__table__
_rules = AlertRule.__table__

DEBOUNCE_SECONDS = 600  # max 1 alert per rule / 10 min


def _matches(condition: dict[str, Any], metrics: dict[str, Any]) -> bool:
    ctype = condition.get("type")
    threshold = condition.get("threshold")
    if ctype == "volume":
        return float(metrics.get("total_mentions", metrics.get("mention_count", 0))) >= float(threshold or 0)
    if ctype == "negative_pct":
        return float(metrics.get("negative_pct", 0)) >= float(threshold or 0)
    if ctype == "spike":
        return bool(metrics.get("spike_detected"))
    return False


async def _debounce_ok(rule_id: str) -> bool:
    redis = get_redis()
    return bool(await redis.set(f"alert:debounce:{rule_id}", "1", nx=True, ex=DEBOUNCE_SECONDS))


async def evaluate_event(event: dict) -> int:
    """Evaluate analytics-updated against enabled org rules. Returns alerts fired."""
    settings = get_settings()
    ensure_redis(settings.redis_url)
    org_id = event.get("org_id")
    if not org_id:
        return 0
    metrics = event.get("metrics", {}) or {}
    fired = 0

    async with engine.begin() as conn:
        rules = (
            await conn.execute(
                select(_rules).where(_rules.c.org_id == org_id, _rules.c.is_enabled.is_(True))
            )
        ).mappings().all()

        if not rules:
            return 0

        # org admin recipient emails (for the 'email' channel)
        admin_emails = (
            await conn.execute(
                select(User.email).where(User.org_id == org_id, User.role == "admin")
            )
        ).scalars().all()

        for rule in rules:
            if not _matches(rule["condition"], metrics):
                continue
            if not await _debounce_ok(str(rule["id"])):
                continue

            keyword = "all keywords"
            if rule["keyword_id"]:
                kw = (
                    await conn.execute(select(Keyword.keyword).where(Keyword.id == rule["keyword_id"]))
                ).scalar_one_or_none()
                keyword = kw or keyword

            channels = list(rule["channels"] or [])
            channel = "email" if "email" in channels else "websocket"
            mention_count = int(metrics.get("total_mentions", metrics.get("mention_count", 0)))
            reason = f"Rule '{rule['name']}' matched ({rule['condition'].get('type')})"
            triggered_at = datetime.now(timezone.utc)

            alert_id = (
                await conn.execute(
                    insert(_alerts)
                    .values(
                        org_id=org_id,
                        rule_id=rule["id"],
                        keyword=keyword,
                        trigger_reason=reason,
                        mention_count=mention_count,
                        channel=channel,
                        triggered_at=triggered_at,
                    )
                    .returning(_alerts.c.id)
                )
            ).scalar_one()

            payload = {
                "alert_id": str(alert_id),
                "rule_id": str(rule["id"]),
                "keyword": keyword,
                "trigger_reason": reason,
                "mention_count": mention_count,
                "triggered_at": triggered_at.isoformat(),
            }
            # enrich with live analytics over gRPC (best-effort)
            from app.grpc_client import get_current_metrics

            live = await get_current_metrics(org_id)
            if live:
                payload["live_metrics"] = live
            if "websocket" in channels:
                await publish_ws(alerts_channel(org_id), {"type": "alert", "payload": payload})
            if "email" in channels and admin_emails:
                html = render_alert_html(
                    keyword=keyword, trigger_reason=reason, mention_count=mention_count,
                    rule_name=rule["name"], triggered_at=triggered_at.isoformat(),
                )
                await send_alert_email(list(admin_emails), f"Alert: {keyword}", html)
            fired += 1

    if fired:
        log.info("alerts fired", org_id=org_id, count=fired)
    return fired
