"""All tools available to the sales agent."""

from src.tools.search_products import search_products
from src.tools.search_by_image import search_by_image
from src.tools.get_promotions import get_promotions
from src.tools.send_product_image import send_product_image

ALL_TOOLS = [
    search_products,
    search_by_image,
    get_promotions,
    send_product_image,
]

__all__ = [
    "search_products",
    "search_by_image",
    "get_promotions",
    "send_product_image",
    "ALL_TOOLS",
]
