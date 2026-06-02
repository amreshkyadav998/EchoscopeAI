"""NLP REST endpoints (HLD §5.3)."""

from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis import analyze_text
from app.db import get_db
from app.deps import CurrentUser, get_current_user
from app.redis_client import ensure_redis, get_cached_summary
from app.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    BatchRequest,
    JobResponse,
    JobResultResponse,
    SummaryResponse,
)
from config import get_settings
from echoscope_common import NotFoundError
from echoscope_db.models import Mention, SentimentResult

router = APIRouter(prefix="/api/v1/nlp", tags=["nlp"])

JOB_TTL = 3600


def _to_analyze_response(text: str) -> AnalyzeResponse:
    r = analyze_text(text, get_settings())
    return AnalyzeResponse(
        sentiment=r.sentiment, confidence=r.confidence, keywords=r.keywords, entities=r.entities
    )


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(payload: AnalyzeRequest, _: CurrentUser = Depends(get_current_user)) -> AnalyzeResponse:
    return _to_analyze_response(payload.text)


@router.post("/batch", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def batch(payload: BatchRequest, _: CurrentUser = Depends(get_current_user)) -> JobResponse:
    settings = get_settings()
    results = [_to_analyze_response(t).model_dump() for t in payload.texts]
    job = JobResultResponse(status="done", progress=len(results), results=results)
    job_id = str(uuid.uuid4())
    ensure_redis(settings.redis_url)
    from app.redis_client import get_redis

    await get_redis().set(f"nlp:job:{job_id}", job.model_dump_json(), ex=JOB_TTL)
    return JobResponse(job_id=job_id, status="done")


@router.get("/jobs/{job_id}", response_model=JobResultResponse)
async def get_job(job_id: str, _: CurrentUser = Depends(get_current_user)) -> JobResultResponse:
    ensure_redis(get_settings().redis_url)
    from app.redis_client import get_redis

    raw = await get_redis().get(f"nlp:job:{job_id}")
    if raw is None:
        raise NotFoundError("Job not found")
    return JobResultResponse(**json.loads(raw))


@router.get("/summary/{mention_id}", response_model=SummaryResponse)
async def get_summary(
    mention_id: str,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
) -> SummaryResponse:
    ensure_redis(get_settings().redis_url)
    cached = await get_cached_summary(mention_id)
    if cached:
        return SummaryResponse(summary=cached, key_points=[])

    row = await db.scalar(select(SentimentResult).where(SentimentResult.mention_id == mention_id))
    if row is None:
        # distinguish "no such mention" from "not analyzed yet"
        if await db.scalar(select(Mention.id).where(Mention.id == mention_id)) is None:
            raise NotFoundError("Mention not found")
        return SummaryResponse(summary=None, key_points=[])
    return SummaryResponse(summary=row.summary, key_points=[])
