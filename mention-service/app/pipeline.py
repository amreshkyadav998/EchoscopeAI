"""Scraping pipeline (HLD §4.3 / Phase 6).

For each active keyword: acquire a distributed lock, fetch from each enabled source,
deduplicate by URL hash (Redis) with the DB UNIQUE constraint as a backstop, insert
the mention, and publish a `mention-created` Kafka event keyed by org_id.

Writes go through a raw Core connection (no ORM Session / unit-of-work), so directly
setting foreign keys can't be second-guessed by relationship synchronization.

Usable both from the API (inline) and from a Celery worker (via asyncio.run).
"""

from __future__ import annotations

from loguru import logger as log
from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError

from app.db import engine
from app.redis_client import acquire_scrape_lock, claim_url, ensure_redis, release_scrape_lock
from app.sources import get_enabled_sources
from config import get_settings
from echoscope_db.models import Keyword, Mention
from echoscope_kafka import MENTION_CREATED, EventProducer

_kw = Keyword.__table__
_m = Mention.__table__


async def run_scrape(keyword_ids: list[str] | None = None) -> dict[str, int]:
    """Scrape the given keywords (or all active keywords) and return counts."""
    settings = get_settings()
    ensure_redis(settings.redis_url)
    sources = get_enabled_sources(settings)
    inserted = 0
    duplicates = 0
    keyword_count = 0

    producer = EventProducer(settings.kafka_brokers)
    await producer.start()
    try:
        async with engine.begin() as conn:
            stmt = select(_kw.c.id, _kw.c.org_id, _kw.c.keyword).where(_kw.c.is_active.is_(True))
            if keyword_ids:
                stmt = stmt.where(_kw.c.id.in_(keyword_ids))
            keywords = (await conn.execute(stmt)).all()
            keyword_count = len(keywords)

            for kw_id, kw_org_id, kw_text in keywords:
                if not await acquire_scrape_lock(str(kw_id)):
                    log.info("scrape skipped (locked)", keyword=kw_text)
                    continue
                try:
                    for source in sources:
                        for raw in await source.fetch(kw_text):
                            if not await claim_url(raw.url):
                                duplicates += 1
                                continue
                            try:
                                async with conn.begin_nested():
                                    result = await conn.execute(
                                        insert(_m)
                                        .values(
                                            org_id=kw_org_id,
                                            keyword_id=kw_id,
                                            source=raw.source,
                                            source_url=raw.url,
                                            title=raw.title,
                                            content=raw.content,
                                            author=raw.author,
                                            published_at=raw.published_at,
                                            upvotes=raw.upvotes,
                                            comment_count=raw.comment_count,
                                        )
                                        .returning(_m.c.id)
                                    )
                                    mention_id = result.scalar_one()
                            except IntegrityError:
                                duplicates += 1
                                continue
                            await producer.publish(
                                MENTION_CREATED,
                                {
                                    "mention_id": str(mention_id),
                                    "org_id": str(kw_org_id),
                                    "keyword_id": str(kw_id),
                                    "source": raw.source,
                                    "content": raw.content,
                                    "source_url": raw.url,
                                    "published_at": raw.published_at.isoformat(),
                                },
                                key=str(kw_org_id),
                            )
                            inserted += 1
                finally:
                    await release_scrape_lock(str(kw_id))
    finally:
        await producer.stop()

    log.info("scrape complete", inserted=inserted, duplicates=duplicates, keywords=keyword_count)
    return {"inserted": inserted, "duplicates": duplicates, "keywords": keyword_count}
