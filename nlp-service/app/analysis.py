"""NLP analysis — sentiment, NER, keyword extraction, summarisation (HLD §4.4).

Lightweight & offline by default:
  - sentiment: VADER (pure-Python lexicon)
  - NER: capitalized-phrase regex
  - keywords: stopword-filtered frequency ranking
  - summary: extractive (leading sentences)

Heavy models are opt-in (config flags) and lazy-loaded so they never slow down
or bloat the default install:
  - use_transformers -> HuggingFace RoBERTa (settings.hf_model_name)
  - use_spacy        -> spaCy en_core_web_sm
  - openai_api_key   -> GPT-4o-mini summarisation
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from loguru import logger as log

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'\-]{2,}")
_CAP_RE = re.compile(r"\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\b")
_SENT_RE = re.compile(r"(?<=[.!?])\s+")

_STOPWORDS = {
    "the", "and", "for", "are", "but", "not", "you", "all", "any", "can", "her", "was",
    "one", "our", "out", "day", "get", "has", "him", "his", "how", "man", "new", "now",
    "old", "see", "two", "way", "who", "boy", "did", "its", "let", "put", "say", "she",
    "too", "use", "that", "this", "with", "have", "from", "they", "will", "your", "what",
    "when", "were", "there", "their", "would", "about", "which", "been", "them", "than",
    "then", "into", "more", "over", "such", "only", "just", "also", "very", "some", "like",
    "http", "https", "www", "com",
}


@dataclass
class AnalysisResult:
    sentiment: str
    confidence: float
    positive_score: float
    negative_score: float
    neutral_score: float
    keywords: list[str]
    entities: list[dict[str, Any]]
    model_version: str
    summary: str | None = None
    key_points: list[str] = field(default_factory=list)


# ── sentiment ─────────────────────────────────────────────────────────────────
@lru_cache
def _vader():
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

    return SentimentIntensityAnalyzer()


def _sentiment_vader(text: str) -> tuple[str, float, float, float, float, str]:
    s = _vader().polarity_scores(text or "")
    compound = s["compound"]
    if compound >= 0.05:
        label = "positive"
    elif compound <= -0.05:
        label = "negative"
    else:
        label = "neutral"
    confidence = round(max(s["pos"], s["neg"], s["neu"]), 4)
    return label, confidence, round(s["pos"], 4), round(s["neg"], 4), round(s["neu"], 4), "vader-3.3"


@lru_cache
def _transformer_pipeline(model_name: str, gpu: bool):
    from transformers import pipeline  # type: ignore

    device = 0 if gpu else -1
    return pipeline("sentiment-analysis", model=model_name, top_k=None, device=device)


def _sentiment_transformer(text: str, settings) -> tuple[str, float, float, float, float, str]:
    pipe = _transformer_pipeline(settings.hf_model_name, settings.gpu_enabled)
    text = (text or "")[: settings.max_text_length]
    scores = {d["label"].lower(): float(d["score"]) for d in pipe(text)[0]}
    # cardiffnlp labels: negative / neutral / positive
    pos = scores.get("positive", 0.0)
    neg = scores.get("negative", 0.0)
    neu = scores.get("neutral", 0.0)
    label = max(("positive", pos), ("negative", neg), ("neutral", neu), key=lambda x: x[1])[0]
    confidence = round(max(pos, neg, neu), 4)
    return label, confidence, round(pos, 4), round(neg, 4), round(neu, 4), f"hf:{settings.hf_model_name}"


# ── keywords ──────────────────────────────────────────────────────────────────
def _keywords(text: str, top: int = 5) -> list[str]:
    words = [w for w in _WORD_RE.findall((text or "").lower()) if w not in _STOPWORDS]
    return [w for w, _ in Counter(words).most_common(top)]


# ── entities ──────────────────────────────────────────────────────────────────
def _entities_regex(text: str, limit: int = 8) -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    for match in _CAP_RE.findall(text or ""):
        if match.lower() in _STOPWORDS or len(match) < 3:
            continue
        seen.setdefault(match, {"text": match, "label": "ENTITY", "score": 0.5})
        if len(seen) >= limit:
            break
    return list(seen.values())


@lru_cache
def _spacy_nlp():
    import spacy  # type: ignore

    return spacy.load("en_core_web_sm")


def _entities_spacy(text: str, limit: int = 12) -> list[dict[str, Any]]:
    doc = _spacy_nlp()(text or "")
    wanted = {"ORG", "PERSON", "GPE", "PRODUCT"}
    seen: dict[tuple, dict[str, Any]] = {}
    for ent in doc.ents:
        if ent.label_ in wanted:
            seen.setdefault((ent.text, ent.label_), {"text": ent.text, "label": ent.label_, "score": 0.9})
    return list(seen.values())[:limit]


# ── summary ───────────────────────────────────────────────────────────────────
def summarize(text: str, settings) -> str | None:
    text = (text or "").strip()
    if len(text) < settings.summary_min_chars:
        return None
    if settings.openai_api_key:
        try:
            return _gpt_summary(text, settings)
        except Exception:
            log.exception("gpt summary failed; falling back to extractive")
    sentences = _SENT_RE.split(text)
    return " ".join(sentences[:2])[:500] or None


def _gpt_summary(text: str, settings) -> str:
    import httpx

    resp = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {settings.openai_api_key}"},
        json={
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "Summarise the text in two concise sentences."},
                {"role": "user", "content": text[:4000]},
            ],
            "temperature": 0.3,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


# ── orchestration ─────────────────────────────────────────────────────────────
def analyze_text(text: str, settings, *, with_summary: bool = False) -> AnalysisResult:
    if settings.use_transformers:
        label, conf, pos, neg, neu, model = _sentiment_transformer(text, settings)
    else:
        label, conf, pos, neg, neu, model = _sentiment_vader(text)

    entities = _entities_spacy(text) if settings.use_spacy else _entities_regex(text)
    keywords = _keywords(text)
    summary = summarize(text, settings) if with_summary else None
    key_points = _SENT_RE.split(summary)[:3] if summary else []

    return AnalysisResult(
        sentiment=label,
        confidence=conf,
        positive_score=pos,
        negative_score=neg,
        neutral_score=neu,
        keywords=keywords,
        entities=entities,
        model_version=model,
        summary=summary,
        key_points=key_points,
    )
