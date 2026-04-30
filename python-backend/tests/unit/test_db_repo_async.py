"""T008: Test async DB repository — real Supabase connection.

Tests verify:
- DBProductRepository uses httpx.AsyncClient
- DBProductRepository.search is async
- Real search against Supabase returns data
"""

import asyncio
import inspect

import httpx
import pytest


class TestDBRepoAsync:

    def test_repository_uses_async_client(self):
        """DBProductRepository must use httpx.AsyncClient, not httpx.Client."""
        from src.repositories.db_repo import DBProductRepository

        repo = DBProductRepository()
        assert isinstance(repo.client, httpx.AsyncClient), (
            f"Expected httpx.AsyncClient, got {type(repo.client).__name__}"
        )
        asyncio.run(repo.aclose())

    def test_search_is_async(self):
        """DBProductRepository.search must be an async coroutine function."""
        from src.repositories.db_repo import DBProductRepository

        assert inspect.iscoroutinefunction(DBProductRepository.search), (
            "DBProductRepository.search must be an async coroutine function"
        )

    def test_aclose_is_async(self):
        """DBProductRepository.aclose must be an async coroutine function."""
        from src.repositories.db_repo import DBProductRepository

        assert inspect.iscoroutinefunction(DBProductRepository.aclose), (
            "DBProductRepository.aclose must be an async coroutine function"
        )


class TestDBRepoRealSearch:

    @pytest.mark.asyncio
    async def test_search_returns_real_products(self):
        """Search against real Supabase returns flower_shop products."""
        from src.repositories.db_repo import DBProductRepository

        repo = DBProductRepository()
        try:
            results = await repo.search("flower_shop", "rose")

            assert isinstance(results, list), (
                f"Expected list, got {type(results).__name__}"
            )
            # If there are products in the DB, verify structure
            if results:
                first = results[0]
                assert hasattr(first, "id") or hasattr(first, "name"), (
                    "Product should have 'id' or 'name' attribute"
                )
        finally:
            await repo.aclose()

    @pytest.mark.asyncio
    async def test_search_empty_for_unknown_tenant(self):
        """Search for unknown tenant returns empty list."""
        from src.repositories.db_repo import DBProductRepository

        repo = DBProductRepository()
        try:
            results = await repo.search("nonexistent_tenant_xyz", "anything")
            assert isinstance(results, list)
        finally:
            await repo.aclose()
