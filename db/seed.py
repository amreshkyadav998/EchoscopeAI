"""Seed the database with realistic fake data for dashboard testing (HLD Phase 4).

Generates: 2 organizations, 5 users each, 10 keywords per org, ~500 mentions with
1:1 sentiment results, and a couple of alert rules per org.

Re-runnable: TRUNCATEs all tables first. DEV USE ONLY.

Run (host):  cd db && ../.venv/Scripts/python seed.py
"""

from __future__ import annotations

import asyncio
import random
import uuid
from datetime import datetime, timedelta, timezone

from faker import Faker
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import get_settings
from echoscope_db.models import (
    AlertRule,
    Keyword,
    Mention,
    Organization,
    Report,  # noqa: F401  (kept for truncate completeness)
    Role,
    Sentiment,
    SentimentResult,
    User,
)

fake = Faker()

SOURCES = ["reddit", "news", "rss", "blog"]
SENTIMENTS = [Sentiment.positive, Sentiment.negative, Sentiment.neutral]
SENTIMENT_WEIGHTS = [0.45, 0.25, 0.30]
NUM_MENTIONS = 500

try:
    import bcrypt

    _PWHASH = bcrypt.hashpw(b"password123", bcrypt.gensalt(rounds=12)).decode()
except Exception:  # pragma: no cover
    _PWHASH = "$2b$12$seeddataplaceholderhashvaluexxxxxxxxxxxxxxxxxxxxx"


def _scores_for(sentiment: Sentiment) -> tuple[float, float, float, float]:
    """Return (confidence, pos, neg, neu) with the chosen sentiment dominant."""
    dominant = round(random.uniform(0.55, 0.97), 3)
    rest = round(1.0 - dominant, 3)
    a = round(random.uniform(0, rest), 3)
    b = round(rest - a, 3)
    if sentiment is Sentiment.positive:
        pos, neg, neu = dominant, a, b
    elif sentiment is Sentiment.negative:
        pos, neg, neu = a, dominant, b
    else:
        pos, neg, neu = a, b, dominant
    return dominant, pos, neg, neu


async def seed() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.db_url, echo=False)
    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with Session() as db:
        # wipe everything (dev only)
        await db.execute(
            text(
                "TRUNCATE reports, alerts, alert_rules, sentiment_results, mentions, "
                "keywords, users, organizations RESTART IDENTITY CASCADE"
            )
        )
        await db.commit()

        orgs: list[Organization] = []
        all_keywords: list[Keyword] = []

        for i in range(2):
            company = fake.unique.company()
            org = Organization(
                name=company,
                slug=fake.unique.slug() + f"-{i}",
                max_keywords=10,
            )
            db.add(org)
            await db.flush()  # get org.id
            orgs.append(org)

            # 5 users: first is admin, rest analyst/viewer
            admin = None
            for u in range(5):
                role = Role.admin if u == 0 else random.choice([Role.analyst, Role.viewer])
                user = User(
                    email=f"user{u}.{org.slug}@example.com",
                    password_hash=_PWHASH,
                    full_name=fake.name(),
                    role=role,
                    org_id=org.id,
                    is_verified=True,
                )
                db.add(user)
                if admin is None:
                    admin = user
            await db.flush()

            # 10 keywords
            for _ in range(10):
                kw = Keyword(
                    org_id=org.id,
                    keyword=fake.unique.word().capitalize(),
                    sources=random.sample(SOURCES, k=random.randint(1, len(SOURCES))),
                    alert_threshold=random.choice([5, 10, 20]),
                    created_by=admin.id,
                )
                db.add(kw)
                all_keywords.append(kw)
            await db.flush()

            # a couple of alert rules per org
            for _ in range(2):
                db.add(
                    AlertRule(
                        org_id=org.id,
                        keyword_id=random.choice(all_keywords[-10:]).id,
                        name=f"{fake.word().capitalize()} spike alert",
                        condition={"type": "spike", "threshold": 2.0, "window_minutes": 60},
                        channels=["email", "websocket"],
                        created_by=admin.id,
                    )
                )
        await db.commit()

        # 500 mentions + 1:1 sentiment
        now = datetime.now(timezone.utc)
        for _ in range(NUM_MENTIONS):
            kw = random.choice(all_keywords)
            published = now - timedelta(
                days=random.randint(0, 29), hours=random.randint(0, 23), minutes=random.randint(0, 59)
            )
            mention = Mention(
                org_id=kw.org_id,
                keyword_id=kw.id,
                source=random.choice(SOURCES),
                source_url=f"https://{fake.domain_name()}/{uuid.uuid4().hex}",
                title=fake.sentence(nb_words=8),
                content=fake.paragraph(nb_sentences=4),
                author=fake.user_name(),
                published_at=published,
                scraped_at=published + timedelta(minutes=random.randint(1, 120)),
                upvotes=random.randint(0, 5000),
                comment_count=random.randint(0, 800),
                language="en",
            )
            db.add(mention)
            await db.flush()

            sentiment = random.choices(SENTIMENTS, weights=SENTIMENT_WEIGHTS, k=1)[0]
            conf, pos, neg, neu = _scores_for(sentiment)
            db.add(
                SentimentResult(
                    mention_id=mention.id,
                    sentiment=sentiment,
                    confidence=conf,
                    positive_score=pos,
                    negative_score=neg,
                    neutral_score=neu,
                    keywords=[fake.word() for _ in range(3)],
                    entities=[{"text": fake.company(), "label": "ORG", "score": round(random.uniform(0.8, 0.99), 2)}],
                    summary=fake.sentence(nb_words=12),
                    model_version="cardiffnlp/twitter-roberta-base-sentiment-latest",
                )
            )
        await db.commit()

    await engine.dispose()
    print(
        f"Seeded: {len(orgs)} orgs, {len(orgs) * 5} users, {len(all_keywords)} keywords, "
        f"{NUM_MENTIONS} mentions + sentiment. (seed user password: 'password123')"
    )


if __name__ == "__main__":
    asyncio.run(seed())
