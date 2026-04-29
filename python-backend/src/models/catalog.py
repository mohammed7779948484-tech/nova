"""Tenant-specific product catalog.

Loads products from a tenant's products.json file and provides
search / filter / lookup methods.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from src.config.settings import get_settings
from src.models.product import Product


class ProductCatalog:
    """In-memory product catalog for one tenant."""

    def __init__(self, products: list[Product]) -> None:
        self._products = products
        self._by_id = {p.id: p for p in products}

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(self, query: str) -> list[Product]:
        """Simple text search across name, description, tags."""
        q = query.lower()
        return [
            p for p in self._products
            if q in p.name.lower()
            or q in p.description.lower()
            or any(q in t.lower() for t in p.tags)
        ]

    def find_similar(self, description: str) -> list[Product]:
        """Find products matching a description (keyword overlap)."""
        words = set(description.lower().split())
        scored: list[tuple[int, Product]] = []
        for p in self._products:
            product_words = set(
                p.name.lower().split()
                + p.description.lower().split()
                + [t.lower() for t in p.tags]
            )
            overlap = len(words & product_words)
            if overlap > 0:
                scored.append((overlap, p))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored[:5]]

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------

    def get_by_id(self, product_id: str) -> Product | None:
        """Exact lookup by product ID."""
        return self._by_id.get(product_id)

    def get_promotions(self) -> list[Product]:
        """Return all currently promoted products."""
        return [p for p in self._products if p.is_promoted]

    def get_all(self) -> list[Product]:
        """Return all products."""
        return list(self._products)


# ------------------------------------------------------------------
# Loader
# ------------------------------------------------------------------

def _load_products(tenant_id: str) -> list[Product]:
    """Load products from a tenant's products.json."""
    tenants_dir = Path(get_settings().tenants_dir)
    products_path = tenants_dir / tenant_id / "products.json"

    if not products_path.exists():
        return []

    with open(products_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return [Product(**item) for item in data]


@lru_cache(maxsize=32)
def get_catalog(tenant_id: str) -> ProductCatalog:
    """Load and cache a tenant's product catalog."""
    products = _load_products(tenant_id)
    return ProductCatalog(products)
