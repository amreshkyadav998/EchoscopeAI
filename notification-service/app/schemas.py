"""Request/response models for alert rules + history (HLD §5.5)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from echoscope_common import BaseSchema


class AlertRuleCreate(BaseSchema):
    name: str = Field(min_length=1, max_length=200)
    # {type: volume|negative_pct|spike, threshold, window_minutes?, sentiment_filter?}
    condition: dict[str, Any]
    channels: list[str] = Field(default_factory=lambda: ["websocket"])
    keyword_id: str | None = None


class AlertRuleUpdate(BaseSchema):
    name: str | None = None
    condition: dict[str, Any] | None = None
    channels: list[str] | None = None
    enabled: bool | None = None


class AlertRuleResponse(BaseSchema):
    id: str
    name: str
    condition: dict[str, Any]
    channels: list[str]
    is_enabled: bool
    keyword_id: str | None = None
    created_at: datetime


class RuleIdResponse(BaseSchema):
    rule_id: str


class RulesList(BaseSchema):
    rules: list[AlertRuleResponse]


class AlertResponse(BaseSchema):
    id: str
    rule_id: str
    keyword: str
    trigger_reason: str
    mention_count: int
    channel: str
    is_read: bool
    triggered_at: datetime


class AlertHistory(BaseSchema):
    alerts: list[AlertResponse]
    next_cursor: str | None = None


class MessageResponse(BaseSchema):
    message: str
