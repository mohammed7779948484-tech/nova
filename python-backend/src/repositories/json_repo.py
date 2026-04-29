"""JSON file-backed product repository."""

import json
import re
from functools import lru_cache
from pathlib import Path

from src.config.settings import get_settings
from src.models.product import Product
from src.repositories.base import ProductRepository

# Common Russian and English suffixes for naive stemming.
# Sorted longest-first so we strip the most specific ending.
_RU_SUFFIXES = (
    "ами", "ями", "ому", "ого", "ему", "его",
    "ов", "ев", "ей", "ий", "ый", "ой",
    "ам", "ям", "ах", "ях",
    "ы", "и", "а", "я", "у", "ю", "е", "о",
)
_EN_SUFFIXES = ("ing", "tion", "ies", "es", "ed", "ly", "er", "s")
_MIN_STEM = 3  # don't strip if the remaining stem is shorter than this


def _stem(word: str) -> str:
    """Very light suffix stripping for RU/EN — good enough for catalog search."""
    w = word.lower().strip()
    for sfx in _RU_SUFFIXES + _EN_SUFFIXES:
        if w.endswith(sfx) and len(w) - len(sfx) >= _MIN_STEM:
            return w[: -len(sfx)]
    return w


def _tokenize(text: str) -> set[str]:
    """Split text into stemmed tokens."""
    words = re.findall(r"[a-zA-Zа-яА-ЯёЁ0-9]+", text.lower())
    return {_stem(w) for w in words if len(w) >= 2}


def _product_tokens(p: Product) -> set[str]:
    """Build a set of stemmed tokens from all searchable product fields."""
    parts = (
        p.name + " " + p.description + " " + p.category
        + " " + " ".join(p.tags)
        + " " + p.id
    )
    return _tokenize(parts)


class JsonProductRepository(ProductRepository):
    """Loads product data from tenants/*/products.json into memory."""

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

    def search(self, tenant_id: str, query: str) -> list[Product]:
        """Tokenized, stemmed search.  Ranks by number of matching stems."""
        products = self._get_catalog_data(tenant_id)
        q_tokens = _tokenize(query)
        if not q_tokens:
            return products[:10]  # empty query → show first items

        scored: list[tuple[int, Product]] = []
        for p in products:
            p_tokens = _product_tokens(p)
            overlap = len(q_tokens & p_tokens)
            if overlap > 0:
                scored.append((overlap, p))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored[:10]]

    def get_by_id(self, tenant_id: str, product_id: str) -> Product | None:
        products = self._get_catalog_data(tenant_id)
        for p in products:
            if p.id == product_id:
                return p
        return None

    def get_promotions(self, tenant_id: str) -> list[Product]:
        products = self._get_catalog_data(tenant_id)
        return [p for p in products if p.is_promoted]

    def find_similar(self, tenant_id: str, description: str) -> list[Product]:
        """Stemmed keyword overlap search."""
        products = self._get_catalog_data(tenant_id)
        q_tokens = _tokenize(description)
        scored: list[tuple[int, Product]] = []

        for p in products:
            overlap = len(q_tokens & _product_tokens(p))
            if overlap > 0:
                scored.append((overlap, p))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored[:5]]


# Global instance of the JSON repository
_json_repo = JsonProductRepository()

def get_repository() -> ProductRepository:
    """Get the active product repository implementation."""
    return _json_repo
