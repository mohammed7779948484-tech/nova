"""Global application settings loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-level settings (not tenant-specific)."""

    model_config = SettingsConfigDict(env_file=".env")

    openai_api_key: str = ""
    openai_api_base: str = ""
    anthropic_api_key: str = ""
    langchain_api_key: str = ""
    tenants_dir: str = "./tenants"
    supabase_url: str = ""
    supabase_service_key: str = ""
    database_url: str = ""
    environment: str = "development"
    log_format: str = "console"
    whatsapp_app_secret: str = ""

    def model_post_init(self, __context: object) -> None:
        if self.environment != "test":
            if not self.supabase_url:
                raise ValueError("SUPABASE_URL is required but not set")
            if not self.supabase_service_key:
                raise ValueError("SUPABASE_SERVICE_KEY is required but not set")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
