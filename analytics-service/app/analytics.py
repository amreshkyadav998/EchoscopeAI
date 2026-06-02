"""Analytics computations (HLD §4.5).

Loads a mentions+sentiment DataFrame for an org/date-range and computes the metrics
behind the 7 REST endpoints, plus Z-score spike detection and competitor scoring.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy import select

from app.db import engine
from echoscope_db.models import Keyword, Mention, SentimentResult

_GRANULARITY = {"hour": "1h", "day": "1D", "week": "1W"}


async def load_frame(
    org_id: str, from_date: datetime | None = None, to_date: datetime | None = None
) -> pd.DataFrame:
    """Load mentions joined with sentiment for an org into a DataFrame."""
    stmt = (
        select(
            Mention.id.label("mention_id"),
            Mention.keyword_id,
            Keyword.keyword.label("keyword"),
            Mention.source,
            Mention.published_at,
            SentimentResult.sentiment,
            SentimentResult.positive_score,
            SentimentResult.negative_score,
        )
        .join(Keyword, Keyword.id == Mention.keyword_id)
        .outerjoin(SentimentResult, SentimentResult.mention_id == Mention.id)
        .where(Mention.org_id == org_id)
    )
    if from_date:
        stmt = stmt.where(Mention.published_at >= from_date)
    if to_date:
        stmt = stmt.where(Mention.published_at <= to_date)

    async with engine.connect() as conn:
        rows = (await conn.execute(stmt)).mappings().all()

    df = pd.DataFrame(rows)
    if not df.empty:
        df["published_at"] = pd.to_datetime(df["published_at"], utc=True)
        # sentiment may be an Enum or string depending on driver
        df["sentiment"] = df["sentiment"].map(lambda v: getattr(v, "value", v))
    return df


def overview(df: pd.DataFrame, from_date: datetime | None, to_date: datetime | None) -> dict[str, Any]:
    total = len(df)
    pos = int((df["sentiment"] == "positive").sum()) if total else 0
    neg = int((df["sentiment"] == "negative").sum()) if total else 0
    if from_date and to_date:
        days = max((to_date - from_date).days, 1)
    elif total:
        span = (df["published_at"].max() - df["published_at"].min()).days
        days = max(span, 1)
    else:
        days = 1
    return {
        "total_mentions": total,
        "positive_pct": round(pos / total, 4) if total else 0.0,
        "negative_pct": round(neg / total, 4) if total else 0.0,
        "avg_per_day": round(total / days, 2),
    }


def trends(df: pd.DataFrame, granularity: str = "day") -> dict[str, Any]:
    freq = _GRANULARITY.get(granularity, "1D")
    if df.empty:
        return {"datapoints": []}
    g = df.set_index("published_at").groupby(pd.Grouper(freq=freq))
    points = []
    for bucket, sub in g:
        if len(sub) == 0:
            continue
        points.append(
            {
                "time": bucket.isoformat(),
                "count": int(len(sub)),
                "positive": int((sub["sentiment"] == "positive").sum()),
                "negative": int((sub["sentiment"] == "negative").sum()),
                "neutral": int((sub["sentiment"] == "neutral").sum()),
            }
        )
    return {"datapoints": points}


def sentiment_breakdown(df: pd.DataFrame) -> dict[str, Any]:
    counts = df["sentiment"].value_counts().to_dict() if not df.empty else {}
    timeline = trends(df, "day")["datapoints"]
    return {
        "positive": int(counts.get("positive", 0)),
        "negative": int(counts.get("negative", 0)),
        "neutral": int(counts.get("neutral", 0)),
        "timeline": timeline,
    }


def top_keywords(df: pd.DataFrame, limit: int = 10) -> dict[str, Any]:
    if df.empty:
        return {"keywords": []}
    out = []
    for kw, sub in df.groupby("keyword"):
        dominant = sub["sentiment"].mode()
        out.append(
            {
                "word": kw,
                "count": int(len(sub)),
                "sentiment": (dominant.iloc[0] if not dominant.empty else "neutral"),
            }
        )
    out.sort(key=lambda x: x["count"], reverse=True)
    return {"keywords": out[:limit]}


def sources(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return {"sources": []}
    out = []
    for src, sub in df.groupby("source"):
        dominant = sub["sentiment"].mode()
        out.append(
            {
                "name": src,
                "count": int(len(sub)),
                "sentiment": (dominant.iloc[0] if not dominant.empty else "neutral"),
            }
        )
    out.sort(key=lambda x: x["count"], reverse=True)
    return {"sources": out}


def detect_spikes(df: pd.DataFrame, threshold: float = 2.0) -> dict[str, Any]:
    """Z-score spike detection per keyword over hourly counts."""
    if df.empty:
        return {"spikes": []}
    spikes = []
    df = df.copy()
    df["hour"] = df["published_at"].dt.floor("h")
    for kw, sub in df.groupby("keyword"):
        hourly = sub.groupby("hour").size()
        if len(hourly) < 3:
            continue
        mean, std = hourly.mean(), hourly.std(ddof=0)
        if std == 0 or np.isnan(std):
            continue
        for hour, count in hourly.items():
            z = (count - mean) / std
            if z >= threshold:
                spikes.append(
                    {
                        "time": hour.isoformat(),
                        "keyword": kw,
                        "magnitude": round(float(count / mean), 2),
                        "z_score": round(float(z), 2),
                        "count": int(count),
                    }
                )
    spikes.sort(key=lambda x: x["z_score"], reverse=True)
    return {"spikes": spikes}


def competitors(df: pd.DataFrame, brands: list[str]) -> dict[str, Any]:
    """Composite score = 0.6*normalised_mentions + 0.4*normalised_sentiment, ranked."""
    rows = []
    for brand in brands:
        sub = df[df["keyword"].str.lower() == brand.lower()] if not df.empty else df
        count = len(sub)
        if count:
            pos = (sub["sentiment"] == "positive").mean()
            neg = (sub["sentiment"] == "negative").mean()
            sentiment_score = float(pos - neg)  # -1..1
        else:
            sentiment_score = 0.0
        rows.append({"brand": brand, "mentions": count, "sentiment_score": round(sentiment_score, 4)})

    if rows:
        max_m = max((r["mentions"] for r in rows), default=0) or 1
        for r in rows:
            m_norm = r["mentions"] / max_m
            s_norm = (r["sentiment_score"] + 1) / 2  # 0..1
            r["score"] = round(0.6 * m_norm + 0.4 * s_norm, 4)
        rows.sort(key=lambda x: x["score"], reverse=True)
    return {"comparison": rows}


def default_range(days: int = 30) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    return now - timedelta(days=days), now
