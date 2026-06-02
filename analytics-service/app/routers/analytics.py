"""Analytics REST endpoints (HLD §5.4) — 7 endpoints with Redis cache-aside (5-min TTL)."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query

from app import analytics as A
from app.cache import cache_aside
from app.deps import CurrentUser, get_current_user
from config import get_settings

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


def _range(from_date: datetime | None, to_date: datetime | None):
    if from_date and to_date:
        return from_date, to_date
    default_from, default_to = A.default_range(30)
    return (from_date or default_from), (to_date or default_to)


@router.get("/overview")
async def overview(
    user: CurrentUser = Depends(get_current_user),
    from_date: datetime | None = Query(default=None),
    to_date: datetime | None = Query(default=None),
):
    settings = get_settings()
    f, t = _range(from_date, to_date)

    async def compute():
        df = await A.load_frame(user.org_id, f, t)
        return A.overview(df, f, t)

    return await cache_aside(user.org_id, "overview", {"f": f, "t": t}, settings.cache_ttl, compute)


@router.get("/trends")
async def trends(
    user: CurrentUser = Depends(get_current_user),
    keyword: str | None = Query(default=None),
    granularity: str = Query(default="day"),
    from_date: datetime | None = Query(default=None),
    to_date: datetime | None = Query(default=None),
):
    settings = get_settings()
    f, t = _range(from_date, to_date)

    async def compute():
        df = await A.load_frame(user.org_id, f, t)
        if keyword and not df.empty:
            df = df[df["keyword"] == keyword]
        return A.trends(df, granularity)

    return await cache_aside(
        user.org_id, "trends", {"keyword": keyword, "g": granularity, "f": f, "t": t},
        settings.cache_ttl, compute,
    )


@router.get("/sentiment")
async def sentiment(
    user: CurrentUser = Depends(get_current_user),
    keyword: str | None = Query(default=None),
    from_date: datetime | None = Query(default=None),
    to_date: datetime | None = Query(default=None),
):
    settings = get_settings()
    f, t = _range(from_date, to_date)

    async def compute():
        df = await A.load_frame(user.org_id, f, t)
        if keyword and not df.empty:
            df = df[df["keyword"] == keyword]
        return A.sentiment_breakdown(df)

    return await cache_aside(
        user.org_id, "sentiment", {"keyword": keyword, "f": f, "t": t}, settings.cache_ttl, compute
    )


@router.get("/keywords/top")
async def keywords_top(
    user: CurrentUser = Depends(get_current_user),
    limit: int = Query(default=10, ge=1, le=100),
    from_date: datetime | None = Query(default=None),
    to_date: datetime | None = Query(default=None),
):
    settings = get_settings()
    f, t = _range(from_date, to_date)

    async def compute():
        df = await A.load_frame(user.org_id, f, t)
        return A.top_keywords(df, limit)

    return await cache_aside(
        user.org_id, "keywords_top", {"limit": limit, "f": f, "t": t}, settings.cache_ttl, compute
    )


@router.get("/spikes")
async def spikes(
    user: CurrentUser = Depends(get_current_user),
    from_date: datetime | None = Query(default=None),
    to_date: datetime | None = Query(default=None),
):
    settings = get_settings()
    f, t = _range(from_date, to_date)

    async def compute():
        df = await A.load_frame(user.org_id, f, t)
        return A.detect_spikes(df, threshold=settings.spike_threshold)

    return await cache_aside(user.org_id, "spikes", {"f": f, "t": t}, settings.cache_ttl, compute)


@router.get("/competitors")
async def competitors(
    user: CurrentUser = Depends(get_current_user),
    brands: list[str] = Query(default_factory=list),
    metric: str = Query(default="composite"),
    from_date: datetime | None = Query(default=None),
    to_date: datetime | None = Query(default=None),
):
    settings = get_settings()
    f, t = _range(from_date, to_date)

    async def compute():
        df = await A.load_frame(user.org_id, f, t)
        return A.competitors(df, brands)

    return await cache_aside(
        user.org_id, "competitors", {"brands": brands, "metric": metric, "f": f, "t": t},
        settings.cache_ttl, compute,
    )


@router.get("/sources")
async def sources(
    user: CurrentUser = Depends(get_current_user),
    from_date: datetime | None = Query(default=None),
    to_date: datetime | None = Query(default=None),
):
    settings = get_settings()
    f, t = _range(from_date, to_date)

    async def compute():
        df = await A.load_frame(user.org_id, f, t)
        return A.sources(df)

    return await cache_aside(user.org_id, "sources", {"f": f, "t": t}, settings.cache_ttl, compute)
