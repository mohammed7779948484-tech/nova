"""Application entry point.

Mounts all channel routers into a single FastAPI app.
Manages the lifecycle of shared resources (httpx clients, DB connections)
via the FastAPI lifespan context manager.
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.channels.admin.router import router as admin_router
from src.channels.web.router import router as web_router
from src.channels.whatsapp.router import router as whatsapp_router
from src.config.settings import get_settings
from src.core.logging_config import setup_logging
from src.middleware.correlation import CorrelationMiddleware
from src.middleware.rate_limiter import RateLimiterMiddleware
from src.services.graph_service import graph_service

logger = structlog.get_logger(__name__)

_start_time: float = 0.0


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown of application resources.

    Startup:
      - Initialize structured logging
      - Pre-warm graph service (compile graph with PostgresSaver)

    Shutdown:
      - Close graph service (connection pool)
      - Close DBTenantConfig's httpx.AsyncClient
      - Close DBProductRepository's httpx.AsyncClient
    """
    settings = get_settings()
    setup_logging(settings.log_format)

    logger.info("nova_backend_starting")
    _start_time = time.monotonic()

    await graph_service._ensure_graph()

    yield

    logger.info("nova_backend_shutting_down")

    try:
        await graph_service.shutdown()
    except RuntimeError:
        logger.warning("graph_service_shutdown_skipped")

    try:
        from src.config.tenant_config import _db_config

        if _db_config is not None:
            await _db_config.aclose()
    except RuntimeError:
        logger.warning("db_config_close_skipped")

    try:
        from src.repositories.db_repo import _db_repo

        if _db_repo is not None:
            await _db_repo.aclose()
    except RuntimeError:
        logger.warning("db_repo_close_skipped")

    logger.info("all_resources_cleaned_up")


app = FastAPI(title="Nova Backend", lifespan=lifespan)

# Middleware order: LIFO — last added runs first on the way in.
# Correlation middleware runs first (innermost), rate limiter next, CORS last.
app.add_middleware(CorrelationMiddleware)
app.add_middleware(RateLimiterMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint with DB connectivity status and uptime."""
    pool = graph_service._connection_pool
    db_connected = pool is not None

    uptime = round(time.monotonic() - _start_time, 1) if _start_time > 0 else 0.0

    if db_connected:
        return {
            "status": "ok",
            "service": "nova-backend",
            "database": "connected",
            "uptime_seconds": uptime,
        }

    from starlette.responses import JSONResponse

    return JSONResponse(
        status_code=503,
        content={
            "status": "degraded",
            "service": "nova-backend",
            "database": "disconnected",
            "uptime_seconds": uptime,
        },
    )


app.include_router(admin_router)
app.include_router(web_router, prefix="")
app.include_router(whatsapp_router, prefix="/api/webhooks/whatsapp")


if __name__ == "__main__":
    import uvicorn

    print("Nova Backend starting on http://localhost:8000")
    uvicorn.run("src.app:app", host="0.0.0.0", port=8000, reload=False)
