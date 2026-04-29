"""Shared pytest fixtures for Nova Backend tests."""

from __future__ import annotations

import os
import sys
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

os.environ.setdefault("ENVIRONMENT", "test")
if "SUPABASE_URL" not in os.environ:
    os.environ["SUPABASE_URL"] = "https://test.supabase.co"
if "SUPABASE_SERVICE_KEY" not in os.environ:
    os.environ["SUPABASE_SERVICE_KEY"] = "test-key"

from src.config.settings import get_settings


@pytest_asyncio.fixture()
async def app_client() -> AsyncGenerator[AsyncClient, None]:
    """HTTP client wired to the FastAPI app for integration tests."""
    from src.app import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
