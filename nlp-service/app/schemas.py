"""Request/response models (HLD §5.3)."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from echoscope_common import BaseSchema


class AnalyzeRequest(BaseSchema):
    text: str = Field(min_length=1)
    language: str | None = None


class AnalyzeResponse(BaseSchema):
    sentiment: str
    confidence: float
    keywords: list[str]
    entities: list[dict[str, Any]]


class BatchRequest(BaseSchema):
    texts: list[str] = Field(min_length=1)
    callback_url: str | None = None


class JobResponse(BaseSchema):
    job_id: str
    status: str


class JobResultResponse(BaseSchema):
    status: str
    progress: int
    results: list[AnalyzeResponse]


class SummaryResponse(BaseSchema):
    summary: str | None = None
    key_points: list[str] = Field(default_factory=list)
