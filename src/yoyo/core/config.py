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
    llm_provider: str = "volcengine"
    llm_model: str = "doubao-seed-2-0-mini-260428"
    llm_api_key: str = ""
    translator_provider: str = "xfyun_its"
    translator_model: str = "its"
    translator_timeout_seconds: float = 20.0
    translator_plain_mt_attempt_timeout_seconds: float = 1.0
    translator_plain_mt_max_attempts: int = 2
    translator_enabled: bool = True
    translator_fail_open: bool = True
    translator_pivot_language: str = "zh"
    translator_answer_enabled: bool = True
    translator_bilingual_enabled: bool = True
    hy_mt_base_url: str = "http://127.0.0.1:8001/v1"
    hy_mt_model: str = "HY-MT1.5-1.8B"
    hy_mt_api_key: str = "local-not-needed"
    xfyun_its_app_id: str = ""
    xfyun_its_api_key: str = ""
    xfyun_its_api_secret: str = ""
    xfyun_its_host: str = "itrans.xfyun.cn"
    xfyun_its_verify_ssl: bool = True
    qa_router_fallback_enabled: bool = True
    qa_router_fallback_provider: str = "openrouter"
    qa_router_fallback_model: str = "openai/gpt-5.4-nano"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    dashscope_api_key: str = ""
    volcengine_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    volcengine_api_key: str = ""
    eval_default_provider: str = "anthropic"
    eval_default_model: str = "claude-sonnet-4-6"
    eval_google_api_key: str = ""
    eval_dashscope_api_key: str = ""
    eval_openrouter_api_key: str = ""
    eval_volcengine_api_key: str = ""
    live_search_provider: str = "tavily"
    tavily_api_key: str = ""
    live_info_cache_enabled: bool = True
    live_info_cache_ttl_seconds: int = 900
    live_info_cache_notice_ttl_seconds: int = 300
    live_info_cache_failure_ttl_seconds: int = 60
    map_provider: str = ""
    map_api_key: str = ""
    amap_base_url: str = "https://restapi.amap.com"
    qa_navigation_default_mode: str = "walking"
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
