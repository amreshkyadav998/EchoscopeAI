# db — central database schema (echoscope_db)

Single source of truth for the platform's PostgreSQL schema: **all 8 tables**, the
Alembic migration chain, and the Faker seed script. Every service imports its models
from the `echoscope_db` package.

## Contents

- `echoscope_db/models.py` — SQLAlchemy models: organizations, users, keywords,
  mentions, sentiment_results, alert_rules, alerts, reports (+ enums).
- `alembic/` — migration chain (`0001` users+organizations, `0002` the other 6 tables
  + indexes).
- `seed.py` — generates fake data for dashboard testing (TRUNCATEs first; dev only).
- `config.py` / `.env.example` — `DB_URL` resolution.

## Usage (from the repo root `.venv`)

```bash
pip install -e ./common -e ./db          # install package + deps (alembic, faker)
cd db
cp .env.example .env                      # host DB_URL (127.0.0.1:5433)

../.venv/Scripts/python -m alembic upgrade head   # apply migrations
../.venv/Scripts/python seed.py                   # seed fake data
```

Seeded login: any `user*.<org-slug>@example.com` with password `password123`.

## Creating a new migration later

```bash
cd db && ../.venv/Scripts/python -m alembic revision -m "add X"   # then edit the file
```
Use the central chain here — do not add per-service Alembic setups.
