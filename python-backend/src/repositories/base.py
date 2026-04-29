"""Repository base protocols for data access abstraction."""

from typing import Protocol

from src.models.product import Product


class ProductRepository(Protocol):
    """Interface for retrieving products, promotions, and similar items."""

    def search(self, tenant_id: str, query: str) -> list[Product]:
        """Search products by query."""
        ...

    def get_by_id(self, tenant_id: str, product_id: str) -> Product | None:
        """Get exact product by ID."""
        ...

    def get_promotions(self, tenant_id: str) -> list[Product]:
        """Get currently promoted products."""
        ...

    def find_similar(self, tenant_id: str, description: str) -> list[Product]:
        """Find products similar to a description (e.g., from an image)."""
        ...
