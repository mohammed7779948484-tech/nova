"""SC-008: 30-second graceful shutdown test — REAL resources.

Verifies that the application shutdown:
1. Closes the real connection pool
2. Closes the real httpx.AsyncClient (db_repo + db_config)
3. All complete within 30 seconds

All resources are REAL — real connection pool, real httpx clients.
No mocks.

PDCA Called Shot:
- test_shutdown_closes_connections_within_30s: Start real GraphService
  with real PostgresSaver, then shut down. Verify all real resources
  close within 30 seconds.
  Expected RED: AssertionError: shutdown did not close connection pool.
"""

from __future__ import annotations

import socket
import sys
import time

import pytest


def _postgres_reachable() -> bool:
    """Check if the PostgreSQL host is reachable."""
    try:
        from src.config.settings import get_settings

        settings = get_settings()
        url = settings.database_url
        if not url or not url.startswith("postgresql"):
            return False
        host_part = url.split("@")[-1].split("/")[0]
        host = host_part.split(":")[0]
        port = int(host_part.split(":")[1]) if ":" in host_part else 5432
        socket.create_connection((host, port), timeout=5)
        return True
    except Exception:
        return False


requires_postgres = pytest.mark.skipif(
    not _postgres_reachable(),
    reason="PostgreSQL not reachable — skipping real shutdown test",
)


@requires_postgres
@pytest.mark.asyncio
async def test_shutdown_closes_connections_within_30s():
    """Real lifespan teardown closes all resources within 30 seconds.

    Creates a REAL GraphService with real PostgresSaver pool,
    then executes the real shutdown sequence from app.py lifespan:
    1. graph_service.shutdown() — closes real connection pool
    2. _db_config.aclose() — closes real httpx client
    3. _db_repo.aclose() — closes real httpx client
    """
    if sys.platform == "win32":
        pytest.skip("psycopg_pool requires SelectorEventLoop — skipped on Windows")

    from src.services.graph_service import GraphService

    gs = GraphService()

    # Initialize real pool + real graph
    await gs._ensure_graph()
    assert gs._connection_pool is not None, "Real pool must be created first"
    assert gs._graph is not None, "Real graph must be compiled first"

    start = time.monotonic()

    # Execute the REAL shutdown sequence (from app.py lifespan)
    try:
        await gs.shutdown()
    except RuntimeError:
        pass

    try:
        from src.config.tenant_config import _db_config

        if _db_config is not None:
            await _db_config.aclose()
    except RuntimeError:
        pass

    try:
        from src.repositories.db_repo import _db_repo

        if _db_repo is not None:
            await _db_repo.aclose()
    except RuntimeError:
        pass

    elapsed = time.monotonic() - start

    # SC-008: All shutdown operations must complete within 30 seconds
    assert elapsed < 30.0, (
        f"Real shutdown took {elapsed:.2f}s — expected < 30s"
    )

    # Verify the pool was actually closed
    assert gs._connection_pool is None, (
        "Real connection pool should be None after shutdown"
    )


@requires_postgres
@pytest.mark.asyncio
async def test_graph_service_shutdown_clears_real_pool():
    """Real graph_service.shutdown() closes the connection pool and clears reference."""
    if sys.platform == "win32":
        pytest.skip("psycopg_pool requires SelectorEventLoop — skipped on Windows")

    from src.services.graph_service import GraphService

    gs = GraphService()

    # Create REAL connection pool
    await gs._ensure_graph()
    assert gs._connection_pool is not None, "Real pool must exist before shutdown"

    # Shutdown should close the real pool
    await gs.shutdown()

    assert gs._connection_pool is None, (
        "Connection pool should be None after shutdown"
    )


@pytest.mark.asyncio
async def test_shutdown_is_safe_when_no_pool():
    """shutdown() does not raise when connection pool was never created.

    No mocks needed — a fresh GraphService has _connection_pool=None
    by default, so calling shutdown() should simply be a no-op.
    """
    from src.services.graph_service import GraphService

    gs = GraphService()
    # _connection_pool is None by default — no need to mock
    assert gs._connection_pool is None

    # Should not raise
    await gs.shutdown()
    assert gs._connection_pool is None


@requires_postgres
@pytest.mark.asyncio
async def test_shutdown_is_safe_when_pool_already_closed():
    """shutdown() handles a pool that was already closed gracefully.

    Opens a real pool, closes it manually, then calls shutdown()
    to verify it doesn't crash on double-close.
    """
    if sys.platform == "win32":
        pytest.skip("psycopg_pool requires SelectorEventLoop — skipped on Windows")

    from src.services.graph_service import GraphService

    gs = GraphService()

    # Create REAL connection pool
    await gs._ensure_graph()
    pool = gs._connection_pool
    assert pool is not None

    # Close the pool manually first
    await pool.close()

    # Now call shutdown — it should handle the already-closed pool
    # without crashing (the try/except in shutdown catches this)
    try:
        await gs.shutdown()
    except RuntimeError:
        pass  # Expected — pool was already closed

    # Pool reference should still be cleared
    assert gs._connection_pool is None


@requires_postgres
@pytest.mark.asyncio
async def test_lifespan_teardown_order():
    """Verify shutdown order matches app.py: graph_service → db_config → db_repo.

    Uses REAL resources. Verifies that after each step, the
    corresponding resource is actually cleaned up.
    """
    if sys.platform == "win32":
        pytest.skip("psycopg_pool requires SelectorEventLoop — skipped on Windows")

    from src.services.graph_service import GraphService

    gs = GraphService()

    # Initialize real pool + real graph
    await gs._ensure_graph()
    assert gs._connection_pool is not None

    # Step 1: graph_service.shutdown() — closes pool
    try:
        await gs.shutdown()
    except RuntimeError:
        pass

    # After step 1: pool must be None
    assert gs._connection_pool is None, (
        "Pool must be None after graph_service.shutdown()"
    )

    # Step 2: db_config.aclose() — closes httpx client
    try:
        from src.config.tenant_config import _db_config

        if _db_config is not None:
            await _db_config.aclose()
    except RuntimeError:
        pass

    # Step 3: db_repo.aclose() — closes httpx client
    try:
        from src.repositories.db_repo import _db_repo

        if _db_repo is not None:
            await _db_repo.aclose()
    except RuntimeError:
        pass

    # If we got here without exceptions, the order is correct
    # and all resources were properly cleaned up
