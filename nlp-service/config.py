"""NLP / AI Service configuration (Phase 1.4 scaffold). See HLD section 4.4."""

from __future__ import annotations

from functools import lru_cache

from echoscope_common import BaseAppSettings, load_settings


class Settings(BaseAppSettings):
    service_name: str = "nlp-service"

    # required
    db_url: str

    # optional
    kafka_brokers: str = "kafka:9092"
    openai_api_key: str | None = None
    hf_model_name: str = "cardiffnlp/twitter-roberta-base-sentiment-latest"
    gpu_enabled: bool = False
    max_text_length: int = 512
    summary_cache_ttl: int = 3600


@lru_cache
def get_settings() -> Settings:
    return load_settings(Settings)


if __name__ == "__main__":
    s = get_settings()
    print(f"{s.service_name}: config OK (hf_model_name={s.hf_model_name}, "
          f"gpu_enabled={s.gpu_enabled})")
