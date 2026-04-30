"""Web channel adapter.

Uses JSON responses (SSE streaming deferred to future iteration).
"""

import uuid
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from src.config.tenant_config import async_list_tenants
from src.services.graph_service import graph_service

router = APIRouter()

# Singleton DBTenantConfig instance — reuse across requests
_db_config = None


async def _get_db_config():
    """Get or create the singleton DBTenantConfig instance."""
    global _db_config
    if _db_config is None:
        from src.config.db_tenant_config import DBTenantConfig
        _db_config = DBTenantConfig()
    return _db_config


# Serve the index.html from where we moved it
# We'll put index.html inside src/channels/web/index.html
WEB_DIR = Path(__file__).parent


@router.get("/", response_class=HTMLResponse)
async def index():
    return (WEB_DIR / "index.html").read_text(encoding="utf-8")


@router.get("/api/tenants")
async def tenants_list():
    return await async_list_tenants()


@router.get("/api/tenants/{slug}/config")
async def tenant_config(slug: str):
    """Get agent configuration for a specific tenant by slug."""
    try:
        db = await _get_db_config()
        agent = await db.get_agent_by_slug(slug)
        if not agent:
            return JSONResponse(
                status_code=404,
                content={"error": f"Tenant '{slug}' not found or inactive"},
            )
        return db.agent_config_to_tenant_config(agent)
    except Exception as e:
        # Fallback to YAML-based config
        try:
            from src.config.tenant_config import get_tenant
            config = get_tenant(slug)
            if config:
                return config.model_dump() if hasattr(config, 'model_dump') else config
        except Exception:
            pass
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/api/tenants/{slug}/products")
async def tenant_products(slug: str):
    """Get products for a specific tenant by slug."""
    try:
        db = await _get_db_config()
        agent = await db.get_agent_by_slug(slug)
        if not agent:
            return JSONResponse(
                status_code=404,
                content={"error": f"Tenant '{slug}' not found or inactive"},
            )
        return {"products": agent.products, "tenant_slug": slug}
    except Exception as e:
        # Fallback to JSON-based products (DEPRECATED — use DBProductRepository)
        try:
            from src.repositories.json_repo import get_fallback_repository
            repo = get_fallback_repository()
            products = repo.get_all_products(tenant_id=slug)
            return {"products": products, "tenant_slug": slug}
        except Exception:
            pass
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/api/chat")
async def chat(request: Request):
    body = await request.json()
    tenant_id = body["tenant_id"]
    thread_id = body.get("thread_id") or f"{tenant_id}:{uuid.uuid4().hex[:8]}"
    message = body["message"]

    response_text = await graph_service.process_message(
        tenant_slug=tenant_id,
        session_id=thread_id,
        message=message,
        channel="web",
    )

    return JSONResponse(content={
        "thread_id": thread_id,
        "response": response_text,
    })
