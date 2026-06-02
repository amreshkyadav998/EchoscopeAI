# NLP / AI Service (:8003)

Kafka consumer on `mention-created` → analyze → write `sentiment_results` → publish
`sentiment-processed`. Plus REST endpoints (HLD §5.3).

## Analysis (HLD §4.4) — lightweight by default, heavy models opt-in

| Task | Default (offline) | Opt-in |
|------|-------------------|--------|
| Sentiment | **VADER** (pure-Python lexicon) | HuggingFace RoBERTa (`USE_TRANSFORMERS=true`) |
| NER | capitalized-phrase regex | spaCy `en_core_web_sm` (`USE_SPACY=true`) |
| Keywords | stopword-filtered frequency (top 5) | (KeyBERT later) |
| Summary | extractive (leading sentences) | GPT-4o-mini (`OPENAI_API_KEY`) |

Heavy models are lazy-loaded and **not** installed by default (see `requirements.txt`).

## Pieces

- `app/analysis.py` — analyzers + `analyze_text()` / `summarize()`.
- `app/processor.py` — `process_event()`: analyze, insert `sentiment_results`
  (ON CONFLICT DO NOTHING = idempotent), cache summary, publish `sentiment-processed`.
- `app/consumer.py` — `NlpConsumer(BaseConsumer)` on `mention-created` (group `nlp-service`).
- `app/routers/nlp.py` — `POST /analyze`, `POST /batch` + `GET /jobs/{id}`, `GET /summary/{id}`.
- The consumer runs as an in-process background task (lifespan) unless `ENABLE_CONSUMER=false`.

## Run (host)

```bash
cp .env.example .env
../.venv/Scripts/uvicorn main:app --port 8003     # serves REST + runs the consumer
```

`manual_test.py` is an end-to-end check against the live stack.
