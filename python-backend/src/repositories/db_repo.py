"""Supabase DB-backed product repository.

Loads products from the agent_products table via the Supabase REST API.
Caches products in memory with a configurable TTL for performance.

Uses the same search/get_promotions/find_similar interface as
JsonProductRepository, so it can be used as a drop-in replacement.

All I/O is async (httpx.AsyncClient) per project constitution Principle IV.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any

import httpx

from src.models.product import Product
from src.repositories.base import ProductRepository

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

# Cache TTL in seconds (5 minutes)
_CACHE_TTL = 300

# Common Russian and English suffixes for naive stemming.
# Sorted longest-first so we strip the most specific ending.
_RU_SUFFIXES = (
    "ами", "ями", "ому", "ого", "ему", "его",
    "ов", "ев", "ей", "ий", "ый", "ой",
    "ам", "ям", "ах", "ях",
    "ы", "и", "а", "я", "у", "ю", "е", "о",
)
_EN_SUFFIXES = ("ing", "tion", "ies", "es", "ed", "ly", "er", "s")

# Arabic suffixes/prefixes for light stemming.
_AR_PREFIXES = ("ال", "وال", "بال", "كال", "فال", "لل")
_AR_SUFFIXES = ("ها", "هم", "هن", "ك", "كما", "كم", "كن", "نا", "ه", "ها", "ي", "ان", "ين", "ون", "ات", "ة", "تى")

_MIN_STEM = 2  # don't strip if the remaining stem is shorter than this


def _stem(word: str) -> str:
    """Light suffix/prefix stripping for RU/EN/AR.

    Good enough for catalog search — not a full morphological analyzer.
    """
    w = word.lower().strip()

    # Try Arabic prefixes first (longest match)
    for pfx in _AR_PREFIXES:
        if w.startswith(pfx) and len(w) - len(pfx) >= _MIN_STEM:
            return w[len(pfx):]

    # Try Arabic suffixes
    for sfx in _AR_SUFFIXES:
        if w.endswith(sfx) and len(w) - len(sfx) >= _MIN_STEM:
            return w[: -len(sfx)]

    # Russian suffixes
    for sfx in _RU_SUFFIXES:
        if w.endswith(sfx) and len(w) - len(sfx) >= _MIN_STEM:
            return w[: -len(sfx)]

    # English suffixes
    for sfx in _EN_SUFFIXES:
        if w.endswith(sfx) and len(w) - len(sfx) >= _MIN_STEM:
            return w[: -len(sfx)]

    return w


def _tokenize(text: str) -> set[str]:
    """Split text into stemmed tokens.

    Supports Latin, Cyrillic, and Arabic scripts.
    """
    words = re.findall(r"[a-zA-Zа-яА-ЯёЁ0-9\u0600-\u06FF]+", text.lower())
    return {_stem(w) for w in words if len(w) >= 2}


def _product_tokens(p: Product) -> set[str]:
    """Build a set of stemmed tokens from all searchable product fields."""
    parts = (
        p.name + " " + p.description + " " + p.category
        + " " + " ".join(p.tags)
        + " " + p.id
    )
    return _tokenize(parts)


def _row_to_product(row: dict[str, Any]) -> Product:
    """Convert a Supabase agent_products row to a Product model.

    Maps:
      - product_slug → id (human-readable identifier)
      - price (decimal string) → float
      - tags (jsonb array) → list[str]
    """
    tags = row.get("tags", [])
    if isinstance(tags, str):
        tags = json.loads(tags)

    price_raw = row.get("price", 0)
    try:
        price_val = float(price_raw)
    except (ValueError, TypeError):
        price_val = 0.0

    return Product(
        id=row.get("product_slug", str(row.get("id", ""))),
        name=row.get("name", ""),
        description=row.get("description", ""),
        price=price_val,
        currency=row.get("currency", "USD"),
        category=row.get("category", ""),
        image_url=row.get("image_url", ""),
        tags=tags or [],
        is_promoted=row.get("is_promoted", False),
        promotion_text=row.get("promotion_text", ""),
    )


class _CacheEntry:
    """Cached product list with expiry."""

    __slots__ = ("products", "expires_at")

    def __init__(self, products: list[Product], ttl: int = _CACHE_TTL):
        self.products = products
        self.expires_at = time.monotonic() + ttl

    def is_valid(self) -> bool:
        return time.monotonic() < self.expires_at


class DBProductRepository(ProductRepository):
    """Loads product data from Supabase agent_products table.

    Uses the Supabase PostgREST API directly via httpx.AsyncClient.
    Caches products per tenant_slug in memory with TTL.

    The tenant_id parameter in the ProductRepository protocol maps
    to tenant_slug in the database. The repository resolves
    tenant_slug → agent_id → products via the agents table.
    """

    def __init__(self, ttl: int = _CACHE_TTL):
        if not SUPABASE_URL:
            raise ValueError(
                "SUPABASE_URL is not set. "
                "Please add it to your .env file."
            )
        if not SUPABASE_SERVICE_KEY:
            raise ValueError(
                "SUPABASE_SERVICE_KEY is not set. "
                "Please add it to your .env file."
            )

        self.base_url = SUPABASE_URL.rstrip("/")
        self.headers = {
            "apikey": SUPABASE_SERVICE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
        self.client = httpx.AsyncClient(
            base_url=f"{self.base_url}/rest/v1",
            headers=self.headers,
            timeout=30.0,
        )
        self._cache: dict[str, _CacheEntry] = {}
        self._ttl = ttl
        self._slug_to_agent_id: dict[str, str] = {}
        logger.info("DBProductRepository initialized — connected to %s", self.base_url)

    async def aclose(self) -> None:
        """Close the underlying httpx.AsyncClient.

        Call this during application shutdown.
        """
        await self.client.aclose()
        logger.info("DBProductRepository — httpx.AsyncClient closed")

    async def _query_table(
        self, table: str, filters: dict[str, str], select: str = "*"
    ) -> list[dict[str, Any]]:
        """Query a Supabase table with filters via PostgREST API."""
        params: dict[str, str] = {"select": select}
        for col, val in filters.items():
            params[col] = f"eq.{val}"

        response = await self.client.get(f"/{table}", params=params)
        response.raise_for_status()
        return response.json()

    async def _get_agent_id(self, tenant_slug: str) -> str | None:
        """Look up the agent UUID for a given tenant_slug.

        Results are cached in memory for the lifetime of the repository.
        """
        if tenant_slug in self._slug_to_agent_id:
            return self._slug_to_agent_id[tenant_slug]

        rows = await self._query_table(
            "agents",
            {"tenant_slug": tenant_slug, "is_active": "true"},
            select="id",
        )
        agent_id = rows[0]["id"] if rows else None
        if agent_id:
            self._slug_to_agent_id[tenant_slug] = agent_id
        return agent_id

    async def _load_products(self, tenant_id: str) -> list[Product]:
        """Fetch products from Supabase for the given tenant_slug."""
        agent_id = await self._get_agent_id(tenant_id)
        if not agent_id:
            logger.warning("No agent found for tenant_slug='%s'", tenant_id)
            return []

        rows = await self._query_table(
            "agent_products",
            {"agent_id": agent_id, "is_available": "true"},
        )
        logger.debug(
            "Loaded %d products for tenant_slug='%s'",
            len(rows), tenant_id,
        )
        return [_row_to_product(row) for row in rows]

    async def _get_catalog(self, tenant_id: str) -> list[Product]:
        """Get cached products, refreshing from DB if expired."""
        entry = self._cache.get(tenant_id)
        if entry and entry.is_valid():
            return entry.products

        products = await self._load_products(tenant_id)
        self._cache[tenant_id] = _CacheEntry(products, self._ttl)
        return products

    async def search(self, tenant_id: str, query: str) -> list[Product]:
        """Tokenized, stemmed search. Ranks by number of matching stems."""
        products = await self._get_catalog(tenant_id)
        q_tokens = _tokenize(query)
        if not q_tokens:
            return products[:10]

        scored: list[tuple[int, Product]] = []
        for p in products:
            p_tokens = _product_tokens(p)
            overlap = len(q_tokens & p_tokens)
            if overlap > 0:
                scored.append((overlap, p))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored[:10]]

    async def get_by_id(self, tenant_id: str, product_id: str) -> Product | None:
        products = await self._get_catalog(tenant_id)
        for p in products:
            if p.id == product_id:
                return p
        return None

    async def get_promotions(self, tenant_id: str) -> list[Product]:
        products = await self._get_catalog(tenant_id)
        return [p for p in products if p.is_promoted]

    async def find_similar(self, tenant_id: str, description: str) -> list[Product]:
        """Stemmed keyword overlap search."""
        products = await self._get_catalog(tenant_id)
        q_tokens = _tokenize(description)
        scored: list[tuple[int, Product]] = []

        for p in products:
            overlap = len(q_tokens & _product_tokens(p))
            if overlap > 0:
                scored.append((overlap, p))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored[:5]]

    def invalidate_cache(self, tenant_id: str | None = None) -> None:
        """Clear cached products.

        Also clears the slug→agent_id mapping for the given tenant
        so it will be re-fetched on next access.

        Args:
            tenant_id: If given, clear only that tenant's cache.
                       Otherwise clear all cached entries.
        """
        if tenant_id:
            self._cache.pop(tenant_id, None)
            self._slug_to_agent_id.pop(tenant_id, None)
        else:
            self._cache.clear()
            self._slug_to_agent_id.clear()


# Global instance of the DB repository
_db_repo: DBProductRepository | None = None


def get_repository() -> ProductRepository:
    """Get the active product repository implementation (DB-backed).

    Lazily creates the singleton on first call.
    """
    global _db_repo
    if _db_repo is None:
        _db_repo = DBProductRepository()
    return _db_repo