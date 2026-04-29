"""T008: Test async DB repository.

PDCA Called Shot:
- test_repository_uses_async_client: verify DBProductRepository.client is an
  instance of httpx.AsyncClient.
  Expected RED: AssertionError <httpx.Client> is not an instance of <httpx.AsyncClient>
- test_search_is_async: verify DBProductRepository.search is a coroutine function.
  Expected RED: AssertionError False is not true
"""

import asyncio
import inspect

import pytest
import httpx


class TestDBRepoAsync:

    def test_repository_uses_async_client(self):
        """DBProductRepository must use httpx.AsyncClient, not httpx.Client."""
        import os
        os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
        os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-key")

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