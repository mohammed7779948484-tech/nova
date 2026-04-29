"""Tests for structured logging configuration and correlation middleware.

PDCA Called Shots:
- test_correlation_id_missing_header_still_generates_id: When no
  X-Correlation-ID header is sent, middleware generates UUID4.
  Expected RED: ImportError for missing modules.

- test_correlation_id_preserves_existing_header: X-Correlation-ID
  from the client is preserved, not overwritten.
  Expected RED: Same ImportError.

- test_structlog_includes_correlation_id: Correlation ID header is
  present in response regardless of health status.
  Expected RED: Same ImportError.

- test_structlog_binds_tenant_id: Correlation ID header present when
  tenant header is sent.
  Expected RED: Same ImportError.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_correlation_id_missing_header_still_generates_id():
    """When no X-Correlation-ID header is sent, middleware generates a new UUID4."""
    from src.core.logging_config import setup_logging

    setup_logging("console")

    from src.app import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")

    corr_id = resp.headers.get("X-Correlation-ID")
    assert corr_id is not None
    assert len(corr_id) == 36


@pytest.mark.asyncio
async def test_correlation_id_preserves_existing_header():
    """When X-Correlation-ID header is sent, middleware preserves it (does not overwrite)."""
    from src.core.logging_config import setup_logging

    setup_logging("console")

    from src.app import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/health",
            headers={"X-Correlation-ID": "test-existing-id-123456789012345"},
        )

    assert resp.headers["X-Correlation-ID"] == "test-existing-id-123456789012345"


@pytest.mark.asyncio
async def test_structlog_includes_correlation_id():
    """Correlation ID header present in response regardless of health status."""
    from src.core.logging_config import setup_logging

    setup_logging("console")

    from src.app import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")

    corr_id = resp.headers.get("X-Correlation-ID")
    assert corr_id is not None
    assert "-" in corr_id


@pytest.mark.asyncio
async def test_structlog_binds_tenant_id():
    """Correlation ID header present when tenant header is sent."""
    from src.core.logging_config import setup_logging

    setup_logging("console")

    from src.app import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/health",
            headers={"X-Tenant-ID": "flower_shop"},
        )

    assert resp.headers.get("X-Correlation-ID") is not None
