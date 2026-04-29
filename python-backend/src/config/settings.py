"""Global application settings loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field
from dotenv import load_dotenv

import os

load_dotenv()


class Settings(BaseModel):
    """Application-level settings (not tenant-specific)."""

    openai_api_key: str = Field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY", "")
    )
    openai_api_base: str = Field(
        default_factory=lambda: os.getenv("OPENAI_API_BASE", "")
    )
    anthropic_api_key: str = Field(
        default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", "")
    )
    langchain_api_key: str = Field(
        default_factory=lambda: os.getenv("LANGCHAIN_API_KEY", "")
    )
    tenants_dir: str = Field(
        default_factory=lambda: os.getenv("TENANTS_DIR", "./tenants")
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
