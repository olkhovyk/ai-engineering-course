from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from .models import MODEL_CATALOG


class Settings(BaseSettings):
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    qdrant_url: str = "http://localhost:6333"
    redis_url: str = "redis://localhost:6379/0"
    sqlite_path: str = "data/usage.db"
    force_bad_primary: bool = False

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    chunks_collection: str = "rag_chunks"
    cache_collection: str = "rag_cache"

    api_key_free: str = "demo-free-key"
    api_key_pro: str = "demo-pro-key"
    api_key_enterprise: str = "demo-enterprise-key"
    api_key_rate_limit_test: str = "demo-low-key"

    phoenix_enabled: bool = False
    phoenix_collector_endpoint: str = "http://localhost:6006/v1/traces"
    phoenix_project_name: str = "lesson-10-rag-api"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_api_keys() -> dict[str, dict]:
    settings = get_settings()
    bad_primary = "openai/this-does-not-exist" if settings.force_bad_primary else None

    return {
        settings.api_key_free: {
            "name": "demo-free",
            "tokens_per_minute": 5_000,
            "models": [
                bad_primary or MODEL_CATALOG["openrouter/free"].id,
                MODEL_CATALOG["meta-llama/llama-3.2-3b-instruct:free"].id,
                MODEL_CATALOG["mistralai/mistral-nemo"].id,
            ],
        },
        settings.api_key_pro: {
            "name": "demo-pro",
            "tokens_per_minute": 20_000,
            "models": [
                MODEL_CATALOG["mistralai/mistral-nemo"].id,
                MODEL_CATALOG["meta-llama/llama-3.1-8b-instruct"].id,
                MODEL_CATALOG["google/gemma-3-4b-it"].id,
            ],
        },
        settings.api_key_enterprise: {
            "name": "demo-enterprise",
            "tokens_per_minute": 100_000,
            "models": [
                MODEL_CATALOG["openai/gpt-4o-mini"].id,
                MODEL_CATALOG["anthropic/claude-3.5-haiku"].id,
                MODEL_CATALOG["mistralai/mistral-large"].id,
            ],
        },
        settings.api_key_rate_limit_test: {
            "name": "demo-rate-limit-test",
            "tokens_per_minute": 50,
            "models": [
                bad_primary or MODEL_CATALOG["openrouter/free"].id,
                MODEL_CATALOG["meta-llama/llama-3.2-3b-instruct:free"].id,
                MODEL_CATALOG["mistralai/mistral-nemo"].id,
            ],
        },
    }
