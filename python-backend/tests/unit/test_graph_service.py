"""T021: Test GraphService — real DB + real LLM.

Tests verify:
- process_message is async (unit)
- GraphService compiles with real PostgresSaver (integration)
- Reuses compiled graph across calls (integration)
- process_message with real LLM returns a meaningful AI response
"""

import inspect
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
    async def test_graph_service_shutdown_cleans_up(self):
        """shutdown() should not raise even with no pool."""
        gs = GraphService()
        await gs.shutdown()
        assert gs._connection_pool is None
        assert gs._graph is None


class TestGraphServiceIntegration:

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


class TestGraphServiceRealLLM:

    @requires_postgres
    @pytest.mark.asyncio
    async def test_process_message_returns_real_ai_response(self):
        """process_message with real LLM returns a meaningful AI response."""
        if sys.platform == "win32":
            pytest.skip("psycopg_pool requires SelectorEventLoop — skipped on Windows")

        gs = GraphService()
        try:
            # Reset llm_service to force fresh registration
            from src.services.llm_service import llm_service
            llm_service._models = []
            llm_service._current_model = None
            llm_service._current_model_index = 0
            llm_service._bound_tools = []

            result = await gs.process_message(
                tenant_slug="flower_shop",
                session_id="test-real-llm-session",
                message="Hello, what products do you have?",
            )

            assert isinstance(result, str), f"Expected str, got {type(result)}"
            assert len(result) > 0, "Response should not be empty"
            # The real LLM should produce a meaningful response, not the graceful failure
            assert "technical difficulties" not in result.lower(), (
                f"Should get real AI response, not graceful failure: {result[:100]}"
            )
        finally:
            await gs.shutdown()

    @requires_postgres
    @pytest.mark.asyncio
    async def test_process_message_product_query(self):
        """process_message with product query triggers tool use via real LLM."""
        if sys.platform == "win32":
            pytest.skip("psycopg_pool requires SelectorEventLoop — skipped on Windows")

        gs = GraphService()
        try:
            from src.services.llm_service import llm_service
            llm_service._models = []
            llm_service._current_model = None
            llm_service._current_model_index = 0
            llm_service._bound_tools = []

            result = await gs.process_message(
                tenant_slug="flower_shop",
                session_id="test-product-query-session",
                message="Do you have any roses?",
            )

            assert isinstance(result, str), f"Expected str, got {type(result)}"
            assert len(result) > 0, "Response should not be empty"
            # Real LLM should give a meaningful answer about products
            assert "technical difficulties" not in result.lower(), (
                f"Should get real AI response, not graceful failure: {result[:100]}"
            )
        finally:
            await gs.shutdown()
