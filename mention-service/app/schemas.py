"""Request/response models (HLD §5.2)."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from echoscope_common import BaseSchema

ALLOWED_SOURCES = {"reddit", "news", "rss", "blog", "mock"}


class KeywordCreate(BaseSchema):
    keyword: str = Field(min_length=1, max_length=200)
    sources: list[str] = Field(default_factory=list)
    alert_threshold: int = Field(default=10, ge=1)


class KeywordResponse(BaseSchema):
    id: str
    keyword: str
    sources: list[str]
    alert_threshold: int
    is_active: bool
    created_at: datetime


class KeywordList(BaseSchema):
    keywords: list[KeywordResponse]
    total: int


class MentionResponse(BaseSchema):
    id: str
    keyword_id: str
    source: str
    source_url: str
    title: str | None = None
    content: str
    author: str | None = None
    published_at: datetime
    upvotes: int
    comment_count: int


class MentionList(BaseSchema):
    mentions: list[MentionResponse]
    total: int
    page: int


class ScrapeRequest(BaseSchema):
    keyword_ids: list[str] = Field(default_factory=list)


class ScrapeResponse(BaseSchema):
    job_id: str
    status: str


class MessageResponse(BaseSchema):
    message: str
