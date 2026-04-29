"""Global application settings loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env path relative to the python-backend project root
# (the directory that contains this src/ package), so that settings
# work regardless of the caller's current working directory.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Application-level settings (not tenant-specific)."""

    model_config = SettingsConfigDict(env_file=str(_ENV_FILE))

    openai_api_key: str = ""
    openai_api_base: str = ""
    anthropic_api_key: str = ""
    langchain_api_key: str = ""
    tenants_dir: str = str(_PROJECT_ROOT / "tenants")
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
