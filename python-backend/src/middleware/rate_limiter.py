"""Per-tenant, per-IP sliding window rate limiter middleware.

Uses an in-memory sliding window counter keyed by (client_ip, tenant_id).
Default limit: 60 requests per minute per tenant per IP.
When the limit is exceeded, returns 429 with a Retry-After header.
"""

from __future__ import annotations

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


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Sliding window rate limiter keyed by (client_ip, tenant_id).

    Reads X-Forwarded-For for the real client IP and X-Tenant-ID for
    the tenant identifier.  When either header is missing the request
    is allowed through (no rate limiting).
    """

    def __init__(
        self,
        app,
        rate_limit: int = DEFAULT_RATE_LIMIT,
        window_seconds: int = DEFAULT_WINDOW_SECONDS,
    ) -> None:
        super().__init__(app)
        self.rate_limit = rate_limit
        self.window_seconds = window_seconds
        # Key: (ip, tenant_id) → list of timestamps
        self._windows: dict[tuple[str, str], list[float]] = defaultdict(list)

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
        """Check if (ip, tenant_id) has exceeded the rate limit.

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

    async def dispatch(self, request: Request, call_next):
        """Process request through rate limiter before forwarding."""
        ip = self._get_client_ip(request)
        tenant_id = self._get_tenant_id(request)

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

        return await call_next(request)
