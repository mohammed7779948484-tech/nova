"""Shared pytest fixtures for Nova Backend tests."""

from __future__ import annotations

import os
import sys
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# ── Force test environment before any settings import ────────────────────
os.environ["ENVIRONMENT"] = "test"

# If the host shell exported a SQLite DATABASE_URL (from Next.js/Prisma),
# remove it so we use the real PostgreSQL URL from .env instead.
if os.environ.get("DATABASE_URL", "").startswith("file:"):
    os.environ.pop("DATABASE_URL", None)

# Do NOT set fake SUPABASE_URL / SUPABASE_SERVICE_KEY here — let them come
# from the .env file so integration tests hit the real database.  Only set
# test-mode skips in Settings.model_post_init (environment="test" bypasses
# the required-field validation).

from src.config.settings import get_settings

# Reset the lru_cache so settings are re-read with the test env vars
get_settings.cache_clear()


@pytest_asyncio.fixture()
async def app_client() -> AsyncGenerator[AsyncClient, None]:
    """HTTP client wired to the FastAPI app for integration tests."""
    from src.app import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
