"""Correlation ID middleware for request tracing.

Generates a UUID4 correlation ID per request, stores it in a
contextvars.ContextVar so structlog can automatically include it
in every log entry.  Also adds X-Correlation-ID response header.
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


class CorrelationMiddleware(BaseHTTPMiddleware):
    """Middleware that generates/propagates correlation IDs.

    If the client sends X-Correlation-ID, that value is preserved.
    Otherwise a new UUID4 is generated.  The ID is stored in a
    contextvar and added as a response header.
    """

    async def dispatch(self, request: Request, call_next):
        incoming = request.headers.get("X-Correlation-ID", "")

        corr_id = incoming if incoming else str(uuid.uuid4())
        token = correlation_id_var.set(corr_id)

        tenant_id = request.headers.get("X-Tenant-ID", "")
        if tenant_id:
            structlog.contextvars.bind_contextvars(tenant_id=tenant_id)

        try:
            response = await call_next(request)
        finally:
            if tenant_id:
                structlog.contextvars.unbind_contextvars("tenant_id")
            correlation_id_var.reset(token)

        response.headers["X-Correlation-ID"] = corr_id
        return response
