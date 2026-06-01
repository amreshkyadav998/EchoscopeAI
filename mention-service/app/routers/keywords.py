"""Keyword CRUD + mentions listing + scrape trigger (HLD §5.2)."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import CurrentUser, get_current_user, require_role
from app.schemas import (
    KeywordCreate,
    KeywordList,
    KeywordResponse,
    MentionList,
    MentionResponse,
    MessageResponse,
    ScrapeRequest,
    ScrapeResponse,
)
from echoscope_common import ConflictError, ForbiddenError, NotFoundError
from echoscope_db.models import Keyword, Mention, Organization

router = APIRouter(prefix="/api/v1", tags=["keywords"])


def _kw_response(kw: Keyword) -> KeywordResponse:
    return KeywordResponse(
        id=str(kw.id),
        keyword=kw.keyword,
        sources=list(kw.sources or []),
        alert_threshold=kw.alert_threshold,
        is_active=kw.is_active,
        created_at=kw.created_at,
    )


@router.post("/keywords", response_model=KeywordResponse, status_code=status.HTTP_201_CREATED)
async def create_keyword(
    payload: KeywordCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("admin", "analyst")),
) -> KeywordResponse:
    org = await db.get(Organization, user.org_id)
    if org is None:
        raise NotFoundError("Organization not found")

    current = await db.scalar(
        select(func.count(Keyword.id)).where(Keyword.org_id == user.org_id, Keyword.is_active.is_(True))
    )
    if current >= org.max_keywords:
        raise ForbiddenError(
            f"Keyword limit reached for the {org.plan.value} plan (max {org.max_keywords})"
        )

    # avoid duplicate keyword text within the same org
    exists = await db.scalar(
        select(Keyword).where(Keyword.org_id == user.org_id, Keyword.keyword == payload.keyword)
    )
    if exists is not None:
        raise ConflictError("This keyword is already tracked")

    kw = Keyword(
        org_id=user.org_id,
        keyword=payload.keyword,
        sources=payload.sources,
        alert_threshold=payload.alert_threshold,
        created_by=user.user_id,
    )
    db.add(kw)
    await db.commit()
    await db.refresh(kw)
    return _kw_response(kw)


@router.get("/keywords", response_model=KeywordList)
async def list_keywords(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> KeywordList:
    rows = list(
        (await db.scalars(select(Keyword).where(Keyword.org_id == user.org_id).order_by(Keyword.created_at.desc()))).all()
    )
    return KeywordList(keywords=[_kw_response(k) for k in rows], total=len(rows))


@router.delete("/keywords/{keyword_id}", response_model=MessageResponse)
async def delete_keyword(
    keyword_id: str,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("admin", "analyst")),
) -> MessageResponse:
    kw = await db.get(Keyword, keyword_id)
    if kw is None or str(kw.org_id) != user.org_id:
        raise NotFoundError("Keyword not found")
    await db.delete(kw)
    await db.commit()
    return MessageResponse(message="Keyword deleted")


@router.get("/mentions", response_model=MentionList)
async def list_mentions(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    keyword_id: str | None = Query(default=None),
    source: str | None = Query(default=None),
    from_date: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> MentionList:
    conditions = [Mention.org_id == user.org_id]
    if keyword_id:
        conditions.append(Mention.keyword_id == keyword_id)
    if source:
        conditions.append(Mention.source == source)
    if from_date:
        conditions.append(Mention.published_at >= from_date)

    total = await db.scalar(select(func.count(Mention.id)).where(*conditions))
    rows = list(
        (
            await db.scalars(
                select(Mention)
                .where(*conditions)
                .order_by(Mention.scraped_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
    )
    mentions = [
        MentionResponse(
            id=str(m.id),
            keyword_id=str(m.keyword_id),
            source=m.source,
            source_url=m.source_url,
            title=m.title,
            content=m.content,
            author=m.author,
            published_at=m.published_at,
            upvotes=m.upvotes,
            comment_count=m.comment_count,
        )
        for m in rows
    ]
    return MentionList(mentions=mentions, total=total or 0, page=page)


@router.post("/mentions/scrape", response_model=ScrapeResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_scrape(
    payload: ScrapeRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("admin", "analyst")),
) -> ScrapeResponse:
    # validate the keywords belong to the caller's org
    ids: list[str] = []
    if payload.keyword_ids:
        rows = list(
            (
                await db.scalars(
                    select(Keyword.id).where(
                        Keyword.id.in_(payload.keyword_ids), Keyword.org_id == user.org_id
                    )
                )
            ).all()
        )
        ids = [str(r) for r in rows]
        if not ids:
            raise NotFoundError("No matching keywords for this organization")

    from app.celery_app import scrape_keywords

    task = scrape_keywords.delay(ids)
    return ScrapeResponse(job_id=task.id, status="queued")
