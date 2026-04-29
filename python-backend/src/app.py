"""Application entry point.

Mounts all channel routers into a single FastAPI app.
Manages the lifecycle of shared resources (httpx clients, DB connections)
via the FastAPI lifespan context manager.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.channels.admin.router import router as admin_router
from src.channels.web.router import router as web_router
from src.channels.whatsapp.router import router as whatsapp_router
from src.middleware.rate_limiter import RateLimiterMiddleware
from src.services.graph_service import graph_service

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown of application resources.

    Startup:
      - Initialize logging
      - Pre-warm graph service (compile graph with PostgresSaver)

    Shutdown:
      - Close graph service (connection pool)
      - Close DBTenantConfig's httpx.AsyncClient
      - Close DBProductRepository's httpx.AsyncClient
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    logger.info("Nova Backend starting up — initializing resources")

    await graph_service._ensure_graph()

    yield

    logger.info("Nova Backend shutting down — cleaning up resources")

    # Wrap each shutdown step in try/except to be resilient to
    # event-loop-closed errors during test teardown (a known issue
    # with pytest-asyncio + FastAPI ASGI transport).
    try:
        await graph_service.shutdown()
    except RuntimeError:
        logger.warning("graph_service.shutdown() skipped — event loop closed")

    try:
        from src.config.tenant_config import _db_config
        if _db_config is not None:
            await _db_config.aclose()
    except RuntimeError:
        logger.warning("_db_config.aclose() skipped — event loop closed")

    try:
        from src.repositories.db_repo import _db_repo
        if _db_repo is not None:
            await _db_repo.aclose()
    except RuntimeError:
        logger.warning("_db_repo.aclose() skipped — event loop closed")

    logger.info("All resources cleaned up")


app = FastAPI(title="Nova Backend", lifespan=lifespan)

# Middleware order: LIFO — last added runs first on the way in.
# Rate limiter should run before CORS on inbound requests.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimiterMiddleware)


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring and API bridge."""
    return {"status": "ok", "service": "nova-backend"}


app.include_router(admin_router)
app.include_router(web_router, prefix="")
app.include_router(whatsapp_router, prefix="/api/webhooks/whatsapp")


if __name__ == "__main__":
    import uvicorn
    print("Nova Backend starting on http://localhost:8000")
    uvicorn.run("src.app:app", host="0.0.0.0", port=8000, reload=False)