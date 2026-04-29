"""Tool: send a product image to the customer."""

from __future__ import annotations

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from src.repositories import get_repository


@tool
def send_product_image(product_id: str, config: RunnableConfig) -> str:
    """Send a product photo to the customer.

    Use this when the customer asks to see a product, or when you want
    to visually showcase a recommended item.

    Args:
        product_id: The unique product ID (e.g. "bouquet-001" or "phone-001").
    """
    tenant_id = config["configurable"]["tenant_id"]
    repo = get_repository()
    product = repo.get_by_id(tenant_id, product_id)

    if not product:
        return f"Product '{product_id}' not found."

    if not product.image_url:
        return f"No image available for {product.name}."

    return (
        f"📸 Here's {product.name}:\n"
        f"Image: {product.image_url}\n"
        f"Price: {product.price} {product.currency}"
    )
