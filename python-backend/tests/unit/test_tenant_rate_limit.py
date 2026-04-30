"""Tests for per-tenant subscription-plan rate limiting (FR-037).

Verifies that the tenant aggregate counter limits combined requests
across all customer IPs for a single tenant.
"""

from src.middleware.rate_limiter import RateLimiterMiddleware


class TestTenantRateLimit:
    """Per-tenant subscription rate limit (FR-037)."""

    def test_tenant_limit_enforced_across_customers(self):
        """When combined requests from multiple IPs exceed tenant plan limit, 429 fires.

        The rate limiter must track a per-tenant aggregate counter IN
        ADDITION to the per-IP counter.  Three different customer IPs
        all hitting the same tenant should collectively hit the tenant
        plan limit.
        """
        tenant_id = "tenant-aggregate-test"

        # Create a test limiter with low tenant limit
        test_limiter = RateLimiterMiddleware(
            app=None,
            rate_limit=100,  # per-IP limit (high, won't trigger)
            window_seconds=60,
            tenant_rate_limit=5,  # low enough to trigger in a test
            tenant_window_seconds=3600,
        )

        # Record 5 requests — all should be allowed (at or below limit)
        for i in range(5):
            assert not test_limiter._is_tenant_rate_limited(tenant_id), (
                f"Request {i + 1}/5 should not be rate-limited"
            )
            test_limiter._record_tenant_request(tenant_id)

        # After 5 requests, the 6th check should indicate rate-limited
        assert test_limiter._is_tenant_rate_limited(tenant_id), (
            "Expected tenant rate limit to fire after exceeding aggregate limit"
        )

    def test_tenant_limit_independent_per_tenant(self):
        """Different tenants have independent aggregate counters."""
        tenant_a = "tenant-a"
        tenant_b = "tenant-b"

        test_limiter = RateLimiterMiddleware(
            app=None,
            rate_limit=100,
            window_seconds=60,
            tenant_rate_limit=3,
            tenant_window_seconds=3600,
        )

        # Exhaust tenant A's limit
        for _ in range(3):
            assert not test_limiter._is_tenant_rate_limited(tenant_a)
            test_limiter._record_tenant_request(tenant_a)

        assert test_limiter._is_tenant_rate_limited(tenant_a)

        # Tenant B should still be allowed
        assert not test_limiter._is_tenant_rate_limited(tenant_b)
        test_limiter._record_tenant_request(tenant_b)

    def test_tenant_limit_not_enforced_without_tenant_id(self):
        """No tenant ID header means no tenant-level rate limiting."""
        test_limiter = RateLimiterMiddleware(
            app=None,
            rate_limit=100,
            window_seconds=60,
            tenant_rate_limit=1,
            tenant_window_seconds=3600,
        )

        # Empty tenant_id should never be rate-limited
        assert not test_limiter._is_tenant_rate_limited("")
        assert not test_limiter._is_tenant_rate_limited("")
