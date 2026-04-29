"""Tool: retrieve current promotions for a tenant."""

from __future__ import annotations

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from src.repositories import get_repository


@tool
def get_promotions(config: RunnableConfig) -> str:
    """Get current special offers and promoted products.

    Use this when the customer asks about sales, deals, specials,
    or when you want to proactively suggest promoted items.
    """
    tenant_id = config["configurable"]["tenant_id"]
    repo = get_repository()
    promos = repo.get_promotions(tenant_id)

    if not promos:
        return "No active promotions at the moment."

    lines = [f"🔥 We have {len(promos)} special offer(s) right now:\n"]
    for p in promos:
        lines.append(p.to_display())
        lines.append("")
    return "\n".join(lines)
