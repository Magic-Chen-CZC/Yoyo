from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    database_url: str = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/yoyo"
    redis_url: str = "redis://localhost:6379/0"
    log_level: str = "INFO"
    llm_provider: str = "anthropic"
    llm_model: str = "claude-sonnet-4-6"
    llm_api_key: str = ""
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
