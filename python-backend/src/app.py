"""Application entry point.

Mounts all channel routers into a single FastAPI app.
Manages the lifecycle of shared resources (httpx clients, DB connections)
via the FastAPI lifespan context manager.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.channels.web.router import router as web_router
from src.channels.whatsapp.router import router as whatsapp_router
from src.channels.telegram.router import router as telegram_router
from src.channels.instagram.router import router as instagram_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown of application resources.

    Startup:
      - Initialize logging
      - DB clients are lazily created on first use

    Shutdown:
      - Close httpx.AsyncClient used by DBTenantConfig
      - Close httpx.Client used by DBProductRepository
    """
    # ── Startup ──
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    logger.info("🚀 Sales Agent starting up — initializing resources")

    yield  # Application runs here

    # ── Shutdown ──
    logger.info("🛑 Sales Agent shutting down — cleaning up resources")

    # Close DBTenantConfig's httpx.AsyncClient
    from src.config.tenant_config import _db_config
    if _db_config is not None:
        await _db_config.aclose()

    # Close DBProductRepository's httpx.Client
    from src.repositories.db_repo import _db_repo
    if _db_repo is not None:
        _db_repo.close()

    logger.info("✅ All resources cleaned up")


app = FastAPI(title="Multi-Channel Sales Agent", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring and API bridge."""
    return {"status": "ok", "service": "sales-agent"}


# Web endpoints at root (for the Sales Studio)
app.include_router(web_router, prefix="")

# Webhooks (under /api prefix for consistency)
app.include_router(whatsapp_router, prefix="/api/webhooks/whatsapp")
app.include_router(telegram_router, prefix="/api/webhooks/telegram")
app.include_router(instagram_router, prefix="/api/webhooks/instagram")


if __name__ == "__main__":
    import uvicorn
    print("🚀 Sales Agent (Multi-Channel) starting on http://localhost:8000")
    uvicorn.run("src.app:app", host="0.0.0.0", port=8000, reload=False)
