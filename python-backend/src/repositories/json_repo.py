"""DEPRECATED: Use DBProductRepository. Retained only as YAML fallback.

This module provides a minimal JSON file-backed product repository
for environments where Supabase is unavailable. It is NOT the primary
data source — use DBProductRepository for all production workflows.
"""

import json
from functools import lru_cache
from pathlib import Path

from src.config.settings import get_settings
from src.models.product import Product
from src.repositories.base import ProductRepository


class JsonProductRepository(ProductRepository):
    """Loads product data from tenants/*/products.json into memory.

    DEPRECATED — retained solely as a YAML/JSON fallback when Supabase
    is unreachable.  Only get_all_products() is guaranteed; all other
    methods delegate to the base class (NotImplementedError).
    """

    def _load_products(self, tenant_id: str) -> list[Product]:
        tenants_dir = Path(get_settings().tenants_dir)
        products_path = tenants_dir / tenant_id / "products.json"

        if not products_path.exists():
            return []

        with open(products_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return [Product(**item) for item in data]

    @lru_cache(maxsize=32)
    def _get_catalog_data(self, tenant_id: str) -> list[Product]:
        return self._load_products(tenant_id)

    def get_all_products(self, tenant_id: str = "") -> list[Product]:
        """Return all products for a tenant (fallback-only use)."""
        if not tenant_id:
            return []
        return self._get_catalog_data(tenant_id)


# Global instance of the JSON repository (fallback only)
_json_repo = JsonProductRepository()


def get_fallback_repository() -> ProductRepository:
    """Get the fallback JSON repository implementation."""
    return _json_repo
