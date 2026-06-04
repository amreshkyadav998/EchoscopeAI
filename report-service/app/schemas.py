"""Request/response models (HLD §5.6)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from echoscope_common import BaseSchema


class ReportCreate(BaseSchema):
    type: str = Field(pattern="^(pdf|csv)$")
    filters: dict[str, Any] = Field(default_factory=dict)  # {from_date, to_date, keywords[]}


class ReportQueued(BaseSchema):
    report_id: str
    status: str


class ReportResponse(BaseSchema):
    id: str
    type: str
    status: str
    download_url: str | None = None
    expires_at: datetime | None = None
    file_size_bytes: int | None = None
    created_at: datetime
    completed_at: datetime | None = None


class ReportList(BaseSchema):
    reports: list[ReportResponse]
    total: int


class ScheduleCreate(BaseSchema):
    cron: str = Field(pattern="^(daily|weekly)$")
    format: str = Field(pattern="^(pdf|csv)$")
    filters: dict[str, Any] = Field(default_factory=dict)


class ScheduleResponse(BaseSchema):
    schedule_id: str


class MessageResponse(BaseSchema):
    message: str
