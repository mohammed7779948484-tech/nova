"""T021: Test GraphService.

Tests verify:
- process_message is async (unit)
- process_message returns string in degraded mode (unit)
- GraphService compiles with real PostgresSaver when DATABASE_URL is set (integration)
- Reuses compiled graph across calls (integration)
"""

import inspect
import os
import socket
import sys

import pytest

from src.services.graph_service import GraphService


def _postgres_reachable() -> bool:
    """Check if the PostgreSQL host is reachable."""
    try:
        from src.config.settings import get_settings
        settings = get_settings()
        url = settings.database_url
        if not url or not url.startswith("postgresql"):
            return False
        # Extract host from URL
        # e.g. postgresql://user:pass@host:port/db
        host_part = url.split("@")[-1].split("/")[0]
        host = host_part.split(":")[0]
        port = int(host_part.split(":")[1]) if ":" in host_part else 5432
        socket.create_connection((host, port), timeout=5)
        return True
    except Exception:
        return False


requires_postgres = pytest.mark.skipif(
    not _postgres_reachable(),
    reason="PostgreSQL not reachable — skipping integration test",
)


class TestGraphServiceUnit:

    def test_graph_service_process_message_is_async(self):
        """GraphService.process_message must be an async coroutine function."""
        gs = GraphService()
        assert inspect.iscoroutinefunction(gs.process_message), (
            "GraphService.process_message must be an async function"
        )

    @pytest.mark.asyncio
    async def test_graph_service_process_message_returns_string_degraded(self):
        """process_message returns graceful string when no DB connection."""
        gs = GraphService()
        result = await gs.process_message(
            tenant_slug="flower_shop",
            session_id="test-phase4-degraded",
            message="hello",
            channel="web",
        )
        assert isinstance(result, str), f"Expected str, got {type(result)}"

    @pytest.mark.asyncio
    async def test_graph_service_shutdown_cleans_up(self):
        """shutdown() should not raise even with no pool."""
        gs = GraphService()
        await gs.shutdown()
        assert gs._connection_pool is None
        assert gs._graph is None


class TestGraphServiceIntegration:
    """Integration tests against the real PostgreSQL database."""

    @requires_postgres
    @pytest.mark.asyncio
    async def test_graph_service_compiles_with_real_postgres(self):
        """GraphService should compile graph with real PostgresSaver."""
        if sys.platform == "win32":
            pytest.skip("psycopg_pool requires SelectorEventLoop — skipped on Windows")

        gs = GraphService()
        try:
            await gs._ensure_graph()

            assert gs._graph is not None, "Graph should be compiled"
            assert gs._connection_pool is not None, "Pool should be initialized"
        finally:
            await gs.shutdown()

    @requires_postgres
    @pytest.mark.asyncio
    async def test_graph_service_reuses_compiled_graph(self):
        """Multiple _ensure_graph() calls should not recompile."""
        if sys.platform == "win32":
            pytest.skip("psycopg_pool requires SelectorEventLoop — skipped on Windows")

        gs = GraphService()
        try:
            await gs._ensure_graph()
            graph_ref = gs._graph

            await gs._ensure_graph()
            assert gs._graph is graph_ref, "Graph should be the same instance"
        finally:
            await gs.shutdown()

    @requires_postgres
    @pytest.mark.asyncio
    async def test_graph_service_process_message_real(self):
        """process_message against real PostgresSaver returns a string."""
        if sys.platform == "win32":
            pytest.skip("psycopg_pool requires SelectorEventLoop — skipped on Windows")

        gs = GraphService()
        try:
            result = await gs.process_message(
                tenant_slug="flower_shop",
                session_id="test-phase4-real",
                message="hello",
            )
            assert isinstance(result, str)
            assert len(result) > 0
        finally:
            await gs.shutdown()
