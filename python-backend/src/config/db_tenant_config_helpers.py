"""Helper functions for DBTenantConfig.

Extracted from db_tenant_config.py to keep it under the 300-line
project limit (FR-008).
"""

from __future__ import annotations

import json
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


def build_agent_config(agent: dict[str, Any], products: list, instructions: list) -> dict[str, Any]:
    """Build DBAgentConfig constructor kwargs from raw Supabase rows.

    Args:
        agent: Row dict from the agents table.
        products: List of row dicts from agent_products table.
        instructions: List of row dicts from agent_instructions table.

    Returns:
        Dict of keyword arguments for DBAgentConfig().
    """
    rules = agent.get("rules", [])
    if isinstance(rules, str):
        rules = json.loads(rules)

    logger.debug(
        "agent_loaded",
        tenant_slug=agent.get("tenant_slug", "?"),
        name=agent.get("name", "?"),
        rules_count=len(rules),
        products_count=len(products or []),
        instructions_count=len(instructions or []),
    )

    return dict(
        agent_id=agent["id"],
        tenant_id=agent["tenant_id"],
        tenant_slug=agent["tenant_slug"],
        business_name=agent["business_name"],
        language=agent["language"],
        name=agent["name"],
        role=agent["role"],
        personality=agent.get("personality", ""),
        rules=rules,
        llm_provider=agent.get("llm_provider", "openai"),
        llm_model=agent.get("llm_model", "LongCat-Flash-Chat"),
        llm_temperature=float(agent.get("llm_temperature", 0.7)),
        llm_max_tokens=int(agent.get("llm_max_tokens", 1024)),
        image_search=agent.get("image_search", True),
        promotions=agent.get("promotions", True),
        upsell=agent.get("upsell", True),
        products=products or [],
        instructions=[i["instruction"] for i in (instructions or [])],
    )


def agent_config_to_tenant_config(config: Any) -> dict[str, Any]:
    """Convert DBAgentConfig to the dict format expected by TenantConfig.

    This allows DB-loaded configs to be used with the existing
    create_llm() and other functions that expect TenantConfig fields.

    Args:
        config: DBAgentConfig loaded from database.

    Returns:
        Dict matching TenantConfig Pydantic model structure.
    """
    return {
        "tenant_id": config.tenant_slug,
        "business_name": config.business_name,
        "language": config.language,
        "agent": {
            "name": config.name,
            "role": config.role,
            "personality": config.personality,
            "rules": config.rules,
        },
        "llm": {
            "provider": config.llm_provider,
            "model": config.llm_model,
            "temperature": config.llm_temperature,
            "max_tokens": config.llm_max_tokens,
        },
        "features": {
            "image_search": config.image_search,
            "promotions": config.promotions,
            "upsell": config.upsell,
        },
        "instructions": config.instructions,
    }
