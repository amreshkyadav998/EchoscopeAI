"""Process a mention-created event → analyze → persist → publish sentiment-processed."""

from __future__ import annotations

from loguru import logger as log
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.analysis import analyze_text
from app.db import engine
from app.redis_client import cache_summary, ensure_redis
from config import get_settings
from echoscope_db.models import SentimentResult
from echoscope_kafka import SENTIMENT_PROCESSED, EventProducer

_sr = SentimentResult.__table__


async def process_event(event: dict, producer: EventProducer) -> bool:
    """Analyze one mention and persist + publish results. Returns False if skipped."""
    settings = get_settings()
    mention_id = event.get("mention_id")
    if not mention_id:
        log.warning("event missing mention_id; skipping")
        return False

    content = event.get("content") or event.get("title") or ""
    result = analyze_text(content, settings, with_summary=True)

    async with engine.begin() as conn:
        # 1:1 with mentions; ON CONFLICT DO NOTHING makes reprocessing idempotent
        stmt = (
            pg_insert(_sr)
            .values(
                mention_id=mention_id,
                sentiment=result.sentiment,
                confidence=result.confidence,
                positive_score=result.positive_score,
                negative_score=result.negative_score,
                neutral_score=result.neutral_score,
                keywords=result.keywords,
                entities=result.entities,
                summary=result.summary,
                model_version=result.model_version,
            )
            .on_conflict_do_nothing(index_elements=["mention_id"])
            .returning(_sr.c.id)
        )
        inserted_id = (await conn.execute(stmt)).scalar_one_or_none()

    if inserted_id is None:
        log.info("sentiment already exists; skipping", mention_id=mention_id)
        return False

    if result.summary:
        try:
            ensure_redis(settings.redis_url)
            await cache_summary(mention_id, result.summary, settings.summary_cache_ttl)
        except Exception:
            log.exception("failed to cache summary")

    await producer.publish(
        SENTIMENT_PROCESSED,
        {
            "mention_id": mention_id,
            "org_id": event.get("org_id"),
            "sentiment": result.sentiment,
            "confidence": result.confidence,
            "positive_score": result.positive_score,
            "negative_score": result.negative_score,
            "neutral_score": result.neutral_score,
            "keywords": result.keywords,
            "entities": result.entities,
        },
        key=str(mention_id),
    )
    log.info("mention analyzed", mention_id=mention_id, sentiment=result.sentiment)
    return True
