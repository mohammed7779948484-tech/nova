"""Tenant configuration loader.

Loads tenant-specific settings from YAML files. Each tenant folder
contains a config.yaml and products.json that define the agent's
personality, rules, LLM settings, and product catalog.

Also provides async DB-based loaders that read from Supabase,
which are the primary method used in production.
"""

from __future__ import annotations

import structlog
import time
from functools import lru_cache
from pathlib import Path
from typing import Any, TYPE_CHECKING

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from src.config.settings import get_settings

if TYPE_CHECKING:
    from src.config.db_tenant_config import DBTenantConfig

load_dotenv()

logger = structlog.get_logger(__name__)

_tenant_cache: dict[str, tuple[TenantConfig, float]] = {}
_TENANT_CACHE_TTL = 300


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class AgentConfig(BaseModel):
    """Agent personality and behaviour rules."""

    name: str = "Sales Agent"
    role: str = "Sales Consultant"
    personality: str = "You are a helpful sales consultant."
    rules: list[str] = Field(default_factory=list)


class LLMConfig(BaseModel):
    """LLM provider settings (can differ per tenant)."""

    provider: str = "openai"  # "openai", "anthropic", or "google"
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 1024


class FeaturesConfig(BaseModel):
    """Feature flags – toggle capabilities per tenant."""

    image_search: bool = True
    promotions: bool = True
    upsell: bool = True


class TenantConfig(BaseModel):
    """Complete configuration for one tenant / business."""

    tenant_id: str
    business_name: str
    language: str = "en"
    agent: AgentConfig = Field(default_factory=AgentConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    features: FeaturesConfig = Field(default_factory=FeaturesConfig)
    instructions: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Loader — YAML-based (legacy fallback)
# ---------------------------------------------------------------------------


def _load_yaml(path: Path) -> dict[str, Any]:
    """Read and parse a YAML file."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@lru_cache(maxsize=32)
def get_tenant(tenant_id: str) -> TenantConfig:
    """Load a tenant config by ID. Results are cached."""
    tenants_dir = Path(get_settings().tenants_dir)
    config_path = tenants_dir / tenant_id / "config.yaml"

    if not config_path.exists():
        raise FileNotFoundError(
            f"Tenant config not found: {config_path}. "
            f"Available tenants: {list_tenants()}"
        )

    data = _load_yaml(config_path)
    data.setdefault("tenant_id", tenant_id)
    return TenantConfig(**data)


def list_tenants() -> list[str]:
    """Return all available tenant IDs."""
    tenants_dir = Path(get_settings().tenants_dir)
    if not tenants_dir.exists():
        return []
    return sorted(
        d.name
        for d in tenants_dir.iterdir()
        if d.is_dir() and (d / "config.yaml").exists()
    )


# ---------------------------------------------------------------------------
# Async DB-based loaders (Supabase) — primary in production
# ---------------------------------------------------------------------------

_db_config: "DBTenantConfig | None" = None


def _get_db_config() -> "DBTenantConfig":
    """Return a singleton DBTenantConfig instance.

    Lazily imports DBTenantConfig to avoid circular imports and
    ensures dotenv is loaded before the class reads env vars.
    """
    global _db_config
    if _db_config is None:
        from src.config.db_tenant_config import DBTenantConfig

        _db_config = DBTenantConfig()
    return _db_config


async def async_get_tenant(tenant_id: str) -> TenantConfig:
    """Load a tenant config from Supabase DB by tenant slug.

    The tenant_id parameter is actually the tenant_slug
    (e.g. "flower_shop", "tech_store").

    Results are cached for _TENANT_CACHE_TTL seconds (5 min).
    Falls back to YAML loading if the DB lookup returns None
    or if any exception occurs (network error, auth error, etc.).
    """
    cached = _tenant_cache.get(tenant_id)
    if cached and time.monotonic() < cached[1]:
        return cached[0]

    try:
        db = _get_db_config()
        agent_cfg = await db.get_agent_by_slug(tenant_id)

        if agent_cfg:
            data = db.agent_config_to_tenant_config(agent_cfg)
            config = TenantConfig(**data)
            _tenant_cache[tenant_id] = (config, time.monotonic() + _TENANT_CACHE_TTL)
            return config

        logger.warning(
            "tenant_not_found_in_db_falling_back_to_yaml", tenant_id=tenant_id
        )
    except Exception:
        logger.exception("db_lookup_failed_falling_back_to_yaml", tenant_id=tenant_id)

    # Fallback to YAML
    return get_tenant(tenant_id)


async def async_list_tenants() -> list[dict[str, Any]]:
    """List all active tenants/agents from Supabase DB.

    Returns a list of dicts with id, business_name, agent_name,
    agent_role, language, provider — matching the /api/tenants format.
    Falls back to YAML-based listing if DB fails.
    """
    try:
        db = _get_db_config()
        agents = await db.list_all_agents()

        result = []
        for agent in agents:
            result.append(
                {
                    "id": agent["tenant_slug"],
                    "business_name": agent["business_name"],
                    "agent_name": agent["name"],
                    "agent_role": agent["role"],
                    "language": agent.get("language", "en"),
                    "provider": f"{agent.get('llm_provider', 'openai')}/{agent.get('llm_model', 'LongCat-Flash-Chat')}",
                }
            )
        return result

    except Exception:
        logger.exception("db_listing_failed_falling_back_to_yaml")
        # Fallback to YAML listing
        result = []
        for tid in list_tenants():
            tc = get_tenant(tid)
            result.append(
                {
                    "id": tid,
                    "business_name": tc.business_name,
                    "agent_name": tc.agent.name,
                    "agent_role": tc.agent.role,
                    "language": tc.language,
                    "provider": f"{tc.llm.provider}/{tc.llm.model}",
                }
            )
        return result


def invalidate_tenant_cache(tenant_id: str | None = None) -> None:
    """Clear cached tenant config.

    Args:
        tenant_id: If given, clear only that tenant's cache.
                   Otherwise clear all cached entries.
    """
    if tenant_id:
        _tenant_cache.pop(tenant_id, None)
    else:
        _tenant_cache.clear()
