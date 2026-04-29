"""T020: Test PostgresSaver graph compilation.

Tests compile the graph with:
- Real PostgresSaver via DATABASE_URL (integration-level)
- Degraded mode with pool=None (unit-level)
"""

import inspect
import sys

import pytest

from src.graphs.sales_graph import build_sales_graph, compile_with_postgres_async


class TestGraphCompilation:

    def test_graph_build_returns_stategraph(self):
        """build_sales_graph() should return a StateGraph instance."""
        graph = build_sales_graph()
        assert graph is not None

    @pytest.mark.asyncio
    async def test_graph_compiles_without_checkpointer_in_degraded_mode(self):
        """When pool is None, compile with checkpointer=None (degraded mode)."""
        compiled = await compile_with_postgres_async(None)

        assert compiled is not None
        assert hasattr(compiled, "checkpointer")
        assert compiled.checkpointer is None

    def test_compile_with_postgres_async_is_async_function(self):
        """compile_with_postgres_async must be an async function."""
        assert inspect.iscoroutinefunction(compile_with_postgres_async), (
            "compile_with_postgres_async must be an async function"
        )

    @pytest.mark.asyncio
    async def test_graph_compiles_with_real_postgres_pool(self):
        """Compile graph with real AsyncConnectionPool from DATABASE_URL."""
        if sys.platform == "win32":
            pytest.skip("psycopg_pool requires SelectorEventLoop — skipped on Windows")

        from src.config.settings import get_settings

        settings = get_settings()
        if not settings.database_url:
            pytest.skip("DATABASE_URL not set — skipping real Postgres test")

        from psycopg_pool import AsyncConnectionPool

        pool = AsyncConnectionPool(
            settings.database_url,
            open=False,
            min_size=0,
            max_size=2,
            kwargs={
                "autocommit": True,
                "connect_timeout": 10,
                "prepare_threshold": None,
            },
        )
        await pool.open()
        try:
            compiled = await compile_with_postgres_async(pool)

            assert compiled is not None
            assert hasattr(compiled, "checkpointer")
            assert compiled.checkpointer is not None
        finally:
            await pool.close()
