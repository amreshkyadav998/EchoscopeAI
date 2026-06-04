"""Alert-rule CRUD + alert history (HLD §5.5)."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import CurrentUser, get_current_user, require_role
from app.schemas import (
    AlertHistory,
    AlertResponse,
    AlertRuleCreate,
    AlertRuleResponse,
    AlertRuleUpdate,
    MessageResponse,
    RuleIdResponse,
    RulesList,
)
from echoscope_common import NotFoundError
from echoscope_db.models import Alert, AlertRule

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


def _rule_response(r: AlertRule) -> AlertRuleResponse:
    return AlertRuleResponse(
        id=str(r.id),
        name=r.name,
        condition=r.condition,
        channels=list(r.channels or []),
        is_enabled=r.is_enabled,
        keyword_id=str(r.keyword_id) if r.keyword_id else None,
        created_at=r.created_at,
    )


@router.get("/rules", response_model=RulesList)
async def list_rules(
    db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(get_current_user)
) -> RulesList:
    rows = list(
        (await db.scalars(select(AlertRule).where(AlertRule.org_id == user.org_id).order_by(AlertRule.created_at.desc()))).all()
    )
    return RulesList(rules=[_rule_response(r) for r in rows])


@router.post("/rules", response_model=RuleIdResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(
    payload: AlertRuleCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("admin", "analyst")),
) -> RuleIdResponse:
    rule = AlertRule(
        org_id=user.org_id,
        keyword_id=payload.keyword_id,
        name=payload.name,
        condition=payload.condition,
        channels=payload.channels,
        created_by=user.user_id,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return RuleIdResponse(rule_id=str(rule.id))


@router.put("/rules/{rule_id}", response_model=AlertRuleResponse)
async def update_rule(
    rule_id: str,
    payload: AlertRuleUpdate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("admin", "analyst")),
) -> AlertRuleResponse:
    rule = await db.get(AlertRule, rule_id)
    if rule is None or str(rule.org_id) != user.org_id:
        raise NotFoundError("Alert rule not found")
    if payload.name is not None:
        rule.name = payload.name
    if payload.condition is not None:
        rule.condition = payload.condition
    if payload.channels is not None:
        rule.channels = payload.channels
    if payload.enabled is not None:
        rule.is_enabled = payload.enabled
    await db.commit()
    await db.refresh(rule)
    return _rule_response(rule)


@router.delete("/rules/{rule_id}", response_model=MessageResponse)
async def delete_rule(
    rule_id: str,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("admin", "analyst")),
) -> MessageResponse:
    rule = await db.get(AlertRule, rule_id)
    if rule is None or str(rule.org_id) != user.org_id:
        raise NotFoundError("Alert rule not found")
    await db.delete(rule)
    await db.commit()
    return MessageResponse(message="Alert rule deleted")


@router.get("/history", response_model=AlertHistory)
async def alert_history(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    from_date: datetime | None = Query(default=None),
    to_date: datetime | None = Query(default=None),
    cursor: datetime | None = Query(default=None, description="keyset: triggered_at of last seen alert"),
    limit: int = Query(default=20, ge=1, le=100),
) -> AlertHistory:
    conditions = [Alert.org_id == user.org_id]
    if from_date:
        conditions.append(Alert.triggered_at >= from_date)
    if to_date:
        conditions.append(Alert.triggered_at <= to_date)
    if cursor:
        conditions.append(Alert.triggered_at < cursor)  # keyset pagination

    rows = list(
        (
            await db.scalars(
                select(Alert).where(*conditions).order_by(Alert.triggered_at.desc()).limit(limit + 1)
            )
        ).all()
    )
    has_more = len(rows) > limit
    rows = rows[:limit]
    alerts = [
        AlertResponse(
            id=str(a.id),
            rule_id=str(a.rule_id),
            keyword=a.keyword,
            trigger_reason=a.trigger_reason,
            mention_count=a.mention_count,
            channel=a.channel.value if hasattr(a.channel, "value") else a.channel,
            is_read=a.is_read,
            triggered_at=a.triggered_at,
        )
        for a in rows
    ]
    next_cursor = alerts[-1].triggered_at.isoformat() if (has_more and alerts) else None
    return AlertHistory(alerts=alerts, next_cursor=next_cursor)
