"""Report generation (HLD §4.7): load data → build PDF/CSV → store → publish event.

PDF uses fpdf2 (pure-Python, no native deps) + a Matplotlib trend chart. CSV is a
Pandas join of mentions + sentiment_results. WeasyPrint (HLD's choice) needs GTK on
Windows, so fpdf2 is the default engine.
"""

from __future__ import annotations

import io
from datetime import datetime, timedelta, timezone

import matplotlib
import pandas as pd
from loguru import logger as log
from sqlalchemy import select, update

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from app.db import engine  # noqa: E402
from app.storage import store_report  # noqa: E402
from config import get_settings  # noqa: E402
from echoscope_db.models import Keyword, Mention, Report, SentimentResult  # noqa: E402
from echoscope_kafka import REPORT_GENERATED, EventProducer  # noqa: E402


async def _load_df(org_id: str, filters: dict) -> pd.DataFrame:
    stmt = (
        select(
            Mention.id.label("mention_id"),
            Keyword.keyword.label("keyword"),
            Mention.source,
            Mention.title,
            Mention.author,
            Mention.published_at,
            SentimentResult.sentiment,
        )
        .join(Keyword, Keyword.id == Mention.keyword_id)
        .outerjoin(SentimentResult, SentimentResult.mention_id == Mention.id)
        .where(Mention.org_id == org_id)
    )
    def _dt(v):
        return datetime.fromisoformat(v) if isinstance(v, str) else v

    if filters.get("from_date"):
        stmt = stmt.where(Mention.published_at >= _dt(filters["from_date"]))
    if filters.get("to_date"):
        stmt = stmt.where(Mention.published_at <= _dt(filters["to_date"]))
    if filters.get("keywords"):
        stmt = stmt.where(Keyword.keyword.in_(filters["keywords"]))

    async with engine.connect() as conn:
        rows = (await conn.execute(stmt)).mappings().all()
    df = pd.DataFrame(rows)
    if not df.empty:
        df["published_at"] = pd.to_datetime(df["published_at"], utc=True)
        df["sentiment"] = df["sentiment"].map(lambda v: getattr(v, "value", v))
    return df


def build_csv(df: pd.DataFrame) -> bytes:
    if df.empty:
        df = pd.DataFrame(columns=["mention_id", "keyword", "source", "title", "author", "published_at", "sentiment"])
    return df.to_csv(index=False).encode("utf-8")


def _trend_png(df: pd.DataFrame) -> bytes | None:
    if df.empty:
        return None
    daily = df.set_index("published_at").resample("1D").size()
    fig, ax = plt.subplots(figsize=(7, 2.6))
    ax.plot(daily.index, daily.values, color="#2563eb", marker="o", ms=3)
    ax.set_title("Mentions per day")
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def build_pdf(df: pd.DataFrame, meta: dict) -> bytes:
    from fpdf import FPDF

    total = len(df)
    pos = int((df["sentiment"] == "positive").sum()) if total else 0
    neg = int((df["sentiment"] == "negative").sum()) if total else 0
    top = (
        df["keyword"].value_counts().head(5).items() if total else []
    )

    pdf = FPDF()
    pdf.add_page()
    # cover
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 12, "EchoscopeAI - Mentions Report", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(110, 110, 110)
    pdf.cell(0, 8, f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Organization: {meta.get('org_id', '')}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # KPI summary
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 9, "Summary", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pct = lambda n: f"{round(100 * n / total, 1)}%" if total else "0%"
    for label, value in [
        ("Total mentions", str(total)),
        ("Positive", f"{pos} ({pct(pos)})"),
        ("Negative", f"{neg} ({pct(neg)})"),
    ]:
        pdf.cell(60, 8, label, border=0)
        pdf.cell(0, 8, value, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # trend chart
    png = _trend_png(df)
    if png:
        pdf.image(io.BytesIO(png), w=180)
        pdf.ln(2)

    # top keywords
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 9, "Top keywords", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    if total:
        for word, count in top:
            pdf.cell(60, 8, str(word), border=0)
            pdf.cell(0, 8, str(count), new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.cell(0, 8, "No data for the selected filters.", new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())


async def generate_report(report_id: str) -> dict:
    """Generate one report end-to-end: build, store, persist, publish."""
    settings = get_settings()

    async with engine.begin() as conn:
        row = (await conn.execute(select(Report.__table__).where(Report.__table__.c.id == report_id))).mappings().first()
        if row is None:
            raise ValueError(f"report {report_id} not found")
        await conn.execute(update(Report.__table__).where(Report.__table__.c.id == report_id).values(status="processing"))

    org_id = str(row["org_id"])
    rtype = row["type"].value if hasattr(row["type"], "value") else row["type"]
    filters = row["filters"] or {}

    df = await _load_df(org_id, filters)
    if rtype == "csv":
        data, ext = build_csv(df), "csv"
    else:
        data, ext = build_pdf(df, {"org_id": org_id}), "pdf"

    stored = store_report(org_id, report_id, ext, data)
    completed_at = datetime.now(timezone.utc)
    expires_at = completed_at + timedelta(seconds=settings.presigned_ttl)

    async with engine.begin() as conn:
        await conn.execute(
            update(Report.__table__)
            .where(Report.__table__.c.id == report_id)
            .values(
                status="done",
                s3_key=stored.key,
                file_size_bytes=stored.size,
                expires_at=expires_at,
                completed_at=completed_at,
            )
        )

    producer = EventProducer(settings.kafka_brokers)
    await producer.start()
    try:
        await producer.publish(
            REPORT_GENERATED,
            {
                "report_id": report_id,
                "org_id": org_id,
                "created_by": str(row["created_by"]),
                "type": rtype,
                "s3_key": stored.key,
                "file_size_bytes": stored.size,
                "generated_at": completed_at.isoformat(),
            },
            key=org_id,
        )
    finally:
        await producer.stop()

    log.info("report generated", report_id=report_id, type=rtype, size=stored.size)
    return {"report_id": report_id, "type": rtype, "size": stored.size, "rows": len(df)}
