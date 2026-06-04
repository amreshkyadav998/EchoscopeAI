# Report Service (:8006)

Async PDF/CSV report generation via Celery, stored in S3 (or locally), with the
`report-generated` event (HLD §4.7 / §5.6).

## Pieces

- `app/generate.py` — `generate_report(report_id)`: load mentions+sentiment (Pandas,
  filtered), build the file, store, update the row, publish `report-generated`.
  - **PDF** via **fpdf2** (pure-Python; cover, KPIs, Matplotlib trend chart, top keywords).
    WeasyPrint (HLD's choice) needs GTK on Windows, so fpdf2 is the default engine.
  - **CSV** via Pandas (`mentions` ⨝ `sentiment_results`).
- `app/storage.py` — **S3** (boto3 put + 24h pre-signed URL) when `AWS_BUCKET` is set,
  else **local** files under `data/reports/` served by the `/download` endpoint.
- `app/celery_app.py` — `generate_report_task` (Celery worker runs `asyncio.run(generate_report)`).
- `app/routers/reports.py` — `POST /api/v1/reports` (202 + queue), `GET /reports`,
  `GET /reports/{id}`, `GET /reports/{id}/download`, `DELETE /reports/{id}`,
  `POST /reports/schedule` (recurring Beat is a follow-up).

## Run (host)

```bash
cp .env.example .env            # AWS_* blank => local storage
../.venv/Scripts/uvicorn main:app --port 8006
# generation worker (separate terminal):
../.venv/Scripts/celery -A app.celery_app.celery worker --loglevel=info --pool=solo
```

`manual_test.py` is an end-to-end check (queue → generate → download for PDF + CSV, event, delete).
