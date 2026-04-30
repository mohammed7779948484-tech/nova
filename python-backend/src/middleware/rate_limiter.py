"""Per-tenant, per-IP sliding window rate limiter middleware.

Uses an in-memory sliding window counter keyed by (client_ip, tenant_id).
Default limit: 60 requests per minute per tenant per IP.

Also enforces a per-tenant aggregate limit (FR-037) across all customer
IPs combined.  Default: 600 requests per hour per tenant plan.
When either limit is exceeded, returns 429 with a Retry-After header.
"""

from __future__ import annotations

import os
import structlog
import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = structlog.get_logger(__name__)

# Default: 60 requests per minute per tenant per IP
DEFAULT_RATE_LIMIT = 60
DEFAULT_WINDOW_SECONDS = 60

# Default: 600 requests per hour per tenant (aggregate across all IPs)
DEFAULT_TENANT_RATE_LIMIT = 600
DEFAULT_TENANT_WINDOW_SECONDS = 3600


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Sliding window rate limiter keyed by (client_ip, tenant_id).

    Reads X-Forwarded-For for the real client IP and X-Tenant-ID for
    the tenant identifier.  When either header is missing the request
    is allowed through (no rate limiting).

    Enforces two limits:
      1. Per-IP + tenant: prevents a single customer from flooding.
      2. Per-tenant aggregate: prevents a tenant's plan from being
         exceeded across all their customers combined (FR-037).
    """

    def __init__(
        self,
        app,
        rate_limit: int = DEFAULT_RATE_LIMIT,
        window_seconds: int = DEFAULT_WINDOW_SECONDS,
        tenant_rate_limit: int | None = None,
        tenant_window_seconds: int | None = None,
    ) -> None:
        super().__init__(app)
        self.rate_limit = rate_limit
        self.window_seconds = window_seconds

        # Per-tenant aggregate limits (FR-037)
        self.tenant_rate_limit = tenant_rate_limit or int(
            os.getenv("TENANT_RATE_LIMIT_PER_HOUR", str(DEFAULT_TENANT_RATE_LIMIT))
        )
        self.tenant_window_seconds = (
            tenant_window_seconds or DEFAULT_TENANT_WINDOW_SECONDS
        )

        # Key: (ip, tenant_id) → list of timestamps
        self._windows: dict[tuple[str, str], list[float]] = defaultdict(list)
        # Key: tenant_id → list of timestamps (aggregate across all IPs)
        self._tenant_windows: dict[str, list[float]] = defaultdict(list)

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from X-Forwarded-For or fallback to client.host."""
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            # X-Forwarded-For may contain multiple IPs; use the first
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    def _get_tenant_id(self, request: Request) -> str:
        """Extract tenant ID from X-Tenant-ID header."""
        return request.headers.get("X-Tenant-ID", "")

    def _is_rate_limited(self, ip: str, tenant_id: str) -> bool:
        """Check if (ip, tenant_id) has exceeded the per-IP rate limit.

        Uses a sliding window: remove timestamps older than window_seconds,
        then check if remaining count >= rate_limit.
        """
        if not tenant_id:
            # No tenant header → no rate limiting
            return False

        key = (ip, tenant_id)
        now = time.monotonic()
        cutoff = now - self.window_seconds

        # Prune old timestamps
        self._windows[key] = [ts for ts in self._windows[key] if ts > cutoff]

        if len(self._windows[key]) >= self.rate_limit:
            return True

        # Record this request
        self._windows[key].append(now)
        return False

    def _is_tenant_rate_limited(self, tenant_id: str) -> bool:
        """Check if tenant aggregate has exceeded the plan rate limit (FR-037).

        Sliding window across ALL customer IPs for a given tenant.
        """
        if not tenant_id:
            return False

        now = time.monotonic()
        cutoff = now - self.tenant_window_seconds

        # Prune old timestamps
        self._tenant_windows[tenant_id] = [
            ts for ts in self._tenant_windows[tenant_id] if ts > cutoff
        ]

        return len(self._tenant_windows[tenant_id]) >= self.tenant_rate_limit

    def _record_tenant_request(self, tenant_id: str) -> None:
        """Record a request against the tenant aggregate counter."""
        if not tenant_id:
            return
        now = time.monotonic()
        self._tenant_windows[tenant_id].append(now)

    async def dispatch(self, request: Request, call_next):
        """Process request through rate limiter before forwarding.

        Order: check tenant aggregate first (FR-037), then per-IP limit.
        """
        ip = self._get_client_ip(request)
        tenant_id = self._get_tenant_id(request)

        # 1. Tenant aggregate check (FR-037)
        if self._is_tenant_rate_limited(tenant_id):
            logger.info("tenant_rate_limit_exceeded", tenant=tenant_id)
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Tenant plan limit exceeded",
                    "retry_after": self.tenant_window_seconds,
                },
                headers={"Retry-After": str(self.tenant_window_seconds)},
            )

        # 2. Per-IP + tenant check
        if self._is_rate_limited(ip, tenant_id):
            logger.info("rate_limit_exceeded", ip=ip, tenant=tenant_id)
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "retry_after": self.window_seconds,
                },
                headers={"Retry-After": str(self.window_seconds)},
            )

        # Record against tenant aggregate after both checks pass
        self._record_tenant_request(tenant_id)

        return await call_next(request)
