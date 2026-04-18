from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ENV_FILE), env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    database_url: str = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/yoyo"
    redis_url: str = "redis://localhost:6379/0"
    log_level: str = "INFO"
    llm_provider: str = "openrouter"
    llm_model: str = "google/gemini-2.5-flash-lite"
    llm_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    eval_default_provider: str = "anthropic"
    eval_default_model: str = "claude-sonnet-4-6"
    eval_google_api_key: str = ""
    eval_dashscope_api_key: str = ""
    eval_openrouter_api_key: str = ""
    live_search_provider: str = "tavily"
    tavily_api_key: str = ""
    map_provider: str = ""
    map_api_key: str = ""
    openrouter_api_key: str = ""
    rag_enabled: bool = False
    rag_backend: str = "llamaindex_pgvector"
    rag_pgvector_dsn: str = ""
    rag_embedding_provider: str = "openrouter"
    rag_embedding_base_url: str = "https://openrouter.ai/api/v1"
    rag_embedding_model: str = "text-embedding-3-small"
    rag_embedding_dimension: int = 1536
    rag_embedding_api_key: str = ""
    rag_collection_name: str = "yoyo_attraction_knowledge"
    tts_provider: str = "dashscope"
    tts_base_url: str = "https://dashscope.aliyuncs.com/api/v1"
    tts_api_key: str = ""
    tts_model: str = "qwen3-tts-flash"
    tts_voice: str = "Cherry"
    tts_audio_format: str = "mp3"
    tts_storage_dir: str = ".generated_tts"


@lru_cache
def get_settings() -> Settings:
    return Settings()
