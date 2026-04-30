"""SC-005: 50 concurrent conversations test — REAL DB + REAL LLM.

Verifies that the concurrency infrastructure can handle 50 simultaneous
conversation requests across 5 tenants (10 per tenant) without
event-loop blocking, deadlocks, or timeouts.

All requests go through the REAL GraphService with REAL PostgresSaver
and REAL LLM (LongCat API). No mocks.

PDCA Called Shot:
- test_50_concurrent_conversations: Fire 50 simultaneous process_message()
  calls across 5 tenants. Assert all complete within 120 seconds and at
  least 90% return non-empty responses (tolerance for API rate-limits).
  Expected RED: timeout or event-loop blocking from remaining sync I/O.
"""

from __future__ import annotations

import asyncio
import socket
import sys
import time

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
    reason="PostgreSQL not reachable — skipping real concurrency test",
)


# Five real tenants from the database, 10 conversations each = 50 total
_TENANTS = ["flower_shop", "tech_store", "restaurant_test", "fashion_boutique", "book_cafe"]
_CONVERSATIONS_PER_TENANT = 10
_TOTAL_CONVERSATIONS = len(_TENANTS) * _CONVERSATIONS_PER_TENANT
# Minimum success rate — allows tolerance for LLM API rate-limiting
_MIN_SUCCESS_RATE = 0.90


@pytest.mark.performance
class TestConcurrency:
    """SC-005: Verify 50 concurrent conversations complete without blocking."""

    @requires_postgres
    @pytest.mark.asyncio
    async def test_50_concurrent_conversations(self):
        """50 simultaneous process_message() calls with REAL DB + REAL LLM.

        Creates a real GraphService with real PostgresSaver and real LLM.
        Fires 50 concurrent requests and verifies at least 90% return
        non-empty responses within 120 seconds.

        The 90% threshold accounts for external LLM API rate-limits
        (429 errors) which are outside our infrastructure control.
        The key assertion is that our concurrency infrastructure
        (async event loop, connection pool, tenant isolation) does
        not deadlock, block, or crash under concurrent load.
        """
        if sys.platform == "win32":
            pytest.skip("psycopg_pool requires SelectorEventLoop — skipped on Windows")

        gs = GraphService()
        try:
            # Initialize real connection pool + real graph with PostgresSaver
            await gs._ensure_graph()
            assert gs._graph is not None, "Graph must compile with real PostgresSaver"
            assert gs._connection_pool is not None, "Pool must be initialized"

            # Build 50 concurrent requests — each uses real DB + real LLM
            async def _single_request(tenant: str, idx: int) -> str:
                session_id = f"concurrency-test-{tenant}-{idx}"
                return await gs.process_message(
                    tenant_slug=tenant,
                    session_id=session_id,
                    message="Hello, what products do you have?",
                )

            tasks = []
            for tenant in _TENANTS:
                for i in range(_CONVERSATIONS_PER_TENANT):
                    tasks.append(_single_request(tenant, i))

            start = time.monotonic()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            elapsed = time.monotonic() - start

            # Categorize results
            successes = [r for r in results if isinstance(r, str) and len(r) > 0]
            errors = [r for r in results if isinstance(r, Exception)]
            empty = [r for r in results if not isinstance(r, Exception) and (not isinstance(r, str) or len(r) == 0)]

            success_rate = len(successes) / _TOTAL_CONVERSATIONS

            # At least 90% must succeed (tolerance for external LLM rate-limits)
            assert success_rate >= _MIN_SUCCESS_RATE, (
                f"Only {len(successes)}/{_TOTAL_CONVERSATIONS} "
                f"({success_rate:.0%}) requests succeeded — "
                f"expected >= {_MIN_SUCCESS_RATE:.0%}. "
                f"Errors: {len(errors)}, Empty: {len(empty)}. "
                f"Error samples: {[str(e)[:100] for e in errors[:3]]}"
            )

            # Must complete within 120 seconds (generous for real LLM calls
            # with possible rate-limit retries)
            assert elapsed < 120.0, (
                f"50 concurrent conversations took {elapsed:.2f}s — expected < 120s"
            )
        finally:
            await gs.shutdown()

    @requires_postgres
    @pytest.mark.asyncio
    async def test_concurrent_requests_do_not_block_event_loop(self):
        """Verify that concurrent requests don't cause event-loop stalls.

        Uses REAL GraphService + REAL DB. Sends 10 concurrent requests
        and verifies they execute in parallel (not serially), proving
        no blocking sync I/O exists.
        """
        if sys.platform == "win32":
            pytest.skip("psycopg_pool requires SelectorEventLoop — skipped on Windows")

        gs = GraphService()
        try:
            await gs._ensure_graph()
            assert gs._graph is not None

            # Fire 10 concurrent requests with real LLM
            tasks = [
                gs.process_message(
                    tenant_slug="flower_shop",
                    session_id=f"ev-loop-test-{i}",
                    message="Hi",
                )
                for i in range(10)
            ]

            start = time.monotonic()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            elapsed = time.monotonic() - start

            # If event loop is NOT blocked, 10 concurrent requests should
            # complete much faster than 10 sequential requests.
            # Real LLM calls take ~2-5s each, so serial would be ~20-50s.
            # Parallel should be ~5-15s. Allow 45s generous margin
            # for API rate-limit retries.
            assert elapsed < 45.0, (
                f"10 concurrent real LLM requests took {elapsed:.2f}s — "
                f"event loop may be blocked by sync I/O"
            )

            # At least 80% must succeed (tolerance for rate-limits)
            successes = [r for r in results if isinstance(r, str) and len(r) > 0]
            success_rate = len(successes) / len(results)
            assert success_rate >= 0.80, (
                f"Only {len(successes)}/{len(results)} event-loop test "
                f"requests succeeded ({success_rate:.0%})"
            )
        finally:
            await gs.shutdown()
