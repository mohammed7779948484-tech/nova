"""T021: Test GraphService.

Tests verify:
- process_message is async (unit)
- process_message returns string in degraded mode (unit)
- GraphService compiles with real PostgresSaver when DATABASE_URL is set (integration)
- Reuses compiled graph across calls (integration)
"""

import inspect
import sys

import pytest

from src.services.graph_service import GraphService


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

    @pytest.mark.asyncio
    async def test_graph_service_compiles_with_real_postgres(self):
        """GraphService should compile graph with real PostgresSaver."""
        if sys.platform == "win32":
            pytest.skip("psycopg_pool requires SelectorEventLoop — skipped on Windows")

        from src.config.settings import get_settings

        settings = get_settings()
        if not settings.database_url:
            pytest.skip("DATABASE_URL not set — skipping integration test")

        gs = GraphService()
        try:
            await gs._ensure_graph()

            assert gs._graph is not None, "Graph should be compiled"
            assert gs._connection_pool is not None, "Pool should be initialized"
        finally:
            await gs.shutdown()

    @pytest.mark.asyncio
    async def test_graph_service_reuses_compiled_graph(self):
        """Multiple _ensure_graph() calls should not recompile."""
        if sys.platform == "win32":
            pytest.skip("psycopg_pool requires SelectorEventLoop — skipped on Windows")

        from src.config.settings import get_settings

        settings = get_settings()
        if not settings.database_url:
            pytest.skip("DATABASE_URL not set — skipping integration test")

        gs = GraphService()
        try:
            await gs._ensure_graph()
            graph_ref = gs._graph

            await gs._ensure_graph()
            assert gs._graph is graph_ref, "Graph should be the same instance"
        finally:
            await gs.shutdown()

    @pytest.mark.asyncio
    async def test_graph_service_process_message_real(self):
        """process_message against real PostgresSaver returns a string."""
        if sys.platform == "win32":
            pytest.skip("psycopg_pool requires SelectorEventLoop — skipped on Windows")

        from src.config.settings import get_settings

        settings = get_settings()
        if not settings.database_url:
            pytest.skip("DATABASE_URL not set — skipping integration test")

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
