"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed runtime configuration for the service."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "customer-support-service"
    environment: str = "development"
    llm_provider: str = "deterministic"
    llm_model: str = "qwen2.5:3b"
    llm_base_url: str = "http://127.0.0.1:11434"
    checkpoint_path: str = "app/data/workflow.sqlite"


@lru_cache
def get_settings() -> Settings:
    """Return the cached settings object used by the application lifespan."""
    return Settings()
