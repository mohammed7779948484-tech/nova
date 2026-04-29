"""Shared pytest fixtures for Nova Backend tests."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-key")

from src.config.settings import get_settings


@pytest.fixture()
def mock_supabase_client():
    """Mock httpx.AsyncClient that stubs Supabase REST API calls."""
    client = AsyncMock(spec=AsyncClient)
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = []
    client.get.return_value = response
    client.post.return_value = response
    client.patch.return_value = response
    return client


@pytest.fixture()
def fake_tenant_config():
    """Minimal TenantConfig-like dict for tests."""
    return {
        "tenant_id": "flower_shop",
        "business_name": "Flower Shop",
        "language": "en",
        "agent_name": "Florist Bot",
        "role": "customer_service",
        "personality": "friendly and helpful",
        "rules": [],
        "products": [],
        "instructions": [],
    }


@pytest.fixture()
def settings():
    """Return application settings with test-safe defaults."""
    return get_settings()


@pytest_asyncio.fixture()
async def app_client() -> AsyncGenerator[AsyncClient, None]:
    """HTTP client wired to the FastAPI app for integration tests."""
    from src.app import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
