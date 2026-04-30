"""Tests for per-tenant, per-IP sliding window rate limiter middleware.

Covers:
- Requests under threshold are allowed (200)
- Requests over threshold are blocked (429) with Retry-After header
- Rate limits are independent per tenant (same IP, different tenants)
"""

from __future__ import annotations

from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route


# ---------------------------------------------------------------------------
# Helper: create a minimal Starlette app for isolated middleware testing
# ---------------------------------------------------------------------------

def _create_app_with_limiter():
    """Create a minimal Starlette app with RateLimiterMiddleware."""
    from src.middleware.rate_limiter import RateLimiterMiddleware

    async def ok_endpoint(request):
        return JSONResponse({"status": "ok"})

    app = Starlette(routes=[Route("/test", ok_endpoint)])
    app.add_middleware(RateLimiterMiddleware)
    return app


# ---------------------------------------------------------------------------
# Test 1: Under-threshold requests are allowed
# ---------------------------------------------------------------------------

def test_rate_limiter_allows_under_threshold() -> None:
    """Making 5 requests from same IP+tenant in 1 minute → all 200."""
    app = _create_app_with_limiter()
    client = TestClient(app)

    for i in range(5):
        response = client.get(
            "/test",
            headers={"X-Forwarded-For": "1.2.3.4", "X-Tenant-ID": "tenant_a"},
        )
        assert response.status_code == 200, (
            f"Request {i + 1}/5 should be allowed, got {response.status_code}"
        )


# ---------------------------------------------------------------------------
# Test 2: Over-threshold requests are blocked with 429
# ---------------------------------------------------------------------------

def test_rate_limiter_blocks_over_threshold() -> None:
    """Making 61 requests from same IP+tenant → 429 with Retry-After header."""
    app = _create_app_with_limiter()
    client = TestClient(app)

    # Send 60 requests (the default limit per minute)
    for i in range(60):
        response = client.get(
            "/test",
            headers={"X-Forwarded-For": "5.6.7.8", "X-Tenant-ID": "tenant_b"},
        )
        assert response.status_code == 200, (
            f"Request {i + 1}/60 should be allowed, got {response.status_code}"
        )

    # 61st request should be blocked
    response = client.get(
        "/test",
        headers={"X-Forwarded-For": "5.6.7.8", "X-Tenant-ID": "tenant_b"},
    )
    assert response.status_code == 429, (
        f"61st request should be blocked (429), got {response.status_code}"
    )

    # Verify Retry-After header is present
    assert "retry-after" in response.headers, "429 response must include Retry-After header"

    # Verify response body
    body = response.json()
    assert body.get("detail") == "Rate limit exceeded", (
        f"Expected 'Rate limit exceeded', got {body}"
    )


# ---------------------------------------------------------------------------
# Test 3: Per-tenant independence
# ---------------------------------------------------------------------------

def test_rate_limiter_is_per_tenant() -> None:
    """Two different tenants from same IP have independent counters."""
    app = _create_app_with_limiter()
    client = TestClient(app)

    # Exhaust the limit for tenant_c from IP 9.9.9.9
    for i in range(60):
        response = client.get(
            "/test",
            headers={"X-Forwarded-For": "9.9.9.9", "X-Tenant-ID": "tenant_c"},
        )
        assert response.status_code == 200, (
            f"tenant_c request {i + 1}/60 should be allowed, got {response.status_code}"
        )

    # tenant_c should now be blocked
    response = client.get(
        "/test",
        headers={"X-Forwarded-For": "9.9.9.9", "X-Tenant-ID": "tenant_c"},
    )
    assert response.status_code == 429, "tenant_c should be rate-limited"

    # tenant_d from the SAME IP should still be allowed
    response = client.get(
        "/test",
        headers={"X-Forwarded-For": "9.9.9.9", "X-Tenant-ID": "tenant_d"},
    )
    assert response.status_code == 200, (
        f"tenant_d from same IP should be allowed, got {response.status_code}"
    )
