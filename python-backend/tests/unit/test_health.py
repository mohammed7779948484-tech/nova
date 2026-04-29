"""Tests for health endpoint and production readiness.

PDCA Called Shots:
- test_health_returns_ok_when_db_connected: With a real connection pool
  from graph_service, GET /health returns 200 with status "ok",
  service, database, uptime_seconds.
  Expected RED: AssertionError — endpoint only returned status+service before.

- test_health_returns_503_when_db_down: When graph_service has no connection
  pool (DB unreachable), /health returns 503 with status "degraded".
  Expected RED: AssertionError — current endpoint always returns 200 "ok".

- test_health_degraded_includes_all_fields: 503 response still includes
  service, database, uptime_seconds.
  Expected RED: KeyError — fields not present.

- test_health_uptime_is_numeric: uptime_seconds is a non-negative number.
  Expected RED: AssertionError or KeyError.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_health_returns_ok_when_db_connected():
    """With real connection pool, GET /health returns 200 with full shape."""
    from src.app import app
    from src.services.graph_service import graph_service

    original_pool = graph_service._connection_pool
    try:
        await graph_service._get_connection_pool()
    except Exception:
        pytest.skip("psycopg_pool unavailable or DB unreachable on this platform")

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
    finally:
        graph_service._connection_pool = original_pool

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "nova-backend"
    assert body["database"] == "connected"
    assert "uptime_seconds" in body


@pytest.mark.asyncio
async def test_health_returns_503_when_db_down():
    """When DB pool is None (unreachable), /health returns 503 with degraded status."""
    from src.app import app
    from src.services.graph_service import graph_service

    original_pool = graph_service._connection_pool
    graph_service._connection_pool = None
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
    finally:
        graph_service._connection_pool = original_pool

    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "degraded"


@pytest.mark.asyncio
async def test_health_degraded_includes_all_fields():
    """503 response still includes all expected fields."""
    from src.app import app
    from src.services.graph_service import graph_service

    original_pool = graph_service._connection_pool
    graph_service._connection_pool = None
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
    finally:
        graph_service._connection_pool = original_pool

    body = resp.json()
    assert body["service"] == "nova-backend"
    assert body["database"] == "disconnected"
    assert "uptime_seconds" in body


@pytest.mark.asyncio
async def test_health_uptime_is_numeric():
    """uptime_seconds is a non-negative number."""
    from src.app import app
    from src.services.graph_service import graph_service

    original_pool = graph_service._connection_pool
    try:
        await graph_service._get_connection_pool()
    except Exception:
        pytest.skip("psycopg_pool unavailable or DB unreachable on this platform")

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
    finally:
        graph_service._connection_pool = original_pool

    body = resp.json()
    assert isinstance(body["uptime_seconds"], (int, float))
    assert body["uptime_seconds"] >= 0
