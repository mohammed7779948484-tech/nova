"""Tool: search products in the tenant's catalog."""

from __future__ import annotations

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from src.repositories import get_repository


@tool
def search_products(query: str, config: RunnableConfig) -> str:
    """Search for products matching a text query.

    Use this when the customer asks about available products,
    wants to browse the catalog, or mentions a specific item.

    Args:
        query: Search terms (product name, category, or description keywords).
    """
    tenant_id = config["configurable"]["tenant_id"]
    repo = get_repository()
    results = repo.search(tenant_id, query)

    if not results:
        return f"No products found for '{query}'. Try broader terms or ask me what's available."

    lines = [f"Found {len(results)} product(s):\n"]
    for p in results:
        lines.append(p.to_display())
        lines.append("")  # blank line separator
    return "\n".join(lines)
