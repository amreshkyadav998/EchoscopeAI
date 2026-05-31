# Mention Collection Service (:8002)

Keyword/brand tracking config + the scraping pipeline (Reddit/PRAW, NewsAPI, RSS/blogs via
Playwright). URL-hash deduplication, distributed scrape locks, Celery Beat scheduling.
Publishes `mention-created` Kafka events.

_Implemented in Phase 6._
