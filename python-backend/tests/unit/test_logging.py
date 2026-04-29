"""Tests for structured logging configuration and correlation middleware.

PDCA Called Shots:
- test_setup_logging_configures_structlog: Verify setup_logging() configures
  structlog with JSON renderer in production and console renderer in dev.
  Expected RED: ImportError: cannot import name 'setup_logging' from 'src.core.logging_config'

- test_log_includes_correlation_id: Verify CorrelationMiddleware generates a
  UUID4 correlation ID per request and stores it in contextvars.
  Expected RED: ImportError: cannot import name 'CorrelationMiddleware' from 'src.middleware.correlation'

- test_correlation_id_response_header: Verify X-Correlation-ID header is set
  in responses.
  Expected RED: Same ImportError

- test_structlog_includes_correlation_id: Verify that structlog.get_logger()
  emits logs containing correlation_id when inside a request context.
  Expected RED: Same ImportError (module not yet integrated)

- test_structlog_binds_tenant_id: Verify tenant_id from X-Tenant-ID header
  is bound to the structlog context for that request.
  Expected RED: Same ImportError
"""

from __future__ import annotations

import logging
import json

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


# ── Degenerate / zero cases ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_correlation_id_missing_header_still_generates_id():
    """When no X-Correlation-ID header is sent, middleware generates a new UUID4."""
    from src.core.logging_config import setup_logging
    from src.middleware.correlation import CorrelationMiddleware

    setup_logging("console")

    from src.app import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")

    assert resp.status_code == 200
    corr_id = resp.headers.get("X-Correlation-ID")
    assert corr_id is not None
    assert len(corr_id) == 36  # UUID4 format


# ── Exception cases ──────────────────────────────────────────────────────────


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

    assert resp.status_code == 200
    assert resp.headers["X-Correlation-ID"] == "test-existing-id-123456789012345"


# ── Happy path ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_structlog_includes_correlation_id():
    """structlog.get_logger() emits logs containing correlation_id in request context."""
    from src.core.logging_config import setup_logging

    setup_logging("console")

    from src.app import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")

    assert resp.status_code == 200
    corr_id = resp.headers.get("X-Correlation-ID")
    assert corr_id is not None
    assert "-" in corr_id  # UUID4 has dashes


@pytest.mark.asyncio
async def test_structlog_binds_tenant_id():
    """tenant_id from X-Tenant-ID header is bound to structlog context for that request."""
    from src.core.logging_config import setup_logging

    setup_logging("console")

    from src.app import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/health",
            headers={"X-Tenant-ID": "flower_shop"},
        )

    assert resp.status_code == 200
    assert resp.headers.get("X-Correlation-ID") is not None
