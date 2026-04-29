"""Supabase DB repository helper functions.

Stemming, tokenization, product-field tokenization, and row-to-model
conversion utilities used by db_repo.py. Extracted to keep db_repo.py
under the 300-line project limit.
"""

from __future__ import annotations

import json
import re
from typing import Any

import structlog

from src.models.product import Product

logger = structlog.get_logger(__name__)

_RU_SUFFIXES = (
    "ами",
    "ями",
    "ому",
    "ого",
    "ему",
    "его",
    "ов",
    "ев",
    "ей",
    "ий",
    "ый",
    "ой",
    "ам",
    "ям",
    "ах",
    "ях",
    "ы",
    "и",
    "а",
    "я",
    "у",
    "ю",
    "е",
    "о",
)
_EN_SUFFIXES = ("ing", "tion", "ies", "es", "ed", "ly", "er", "s")

_AR_PREFIXES = ("ال", "وال", "بال", "كال", "فال", "لل")
_AR_SUFFIXES = (
    "ها",
    "هم",
    "هن",
    "ك",
    "كما",
    "كم",
    "كن",
    "نا",
    "ه",
    "ها",
    "ي",
    "ان",
    "ين",
    "ون",
    "ات",
    "ة",
    "تى",
)

_MIN_STEM = 2


def _stem(word: str) -> str:
    """Light suffix/prefix stripping for RU/EN/AR.

    Good enough for catalog search — not a full morphological analyzer.
    """
    w = word.lower().strip()

    for pfx in _AR_PREFIXES:
        if w.startswith(pfx) and len(w) - len(pfx) >= _MIN_STEM:
            return w[len(pfx) :]

    for sfx in _AR_SUFFIXES:
        if w.endswith(sfx) and len(w) - len(sfx) >= _MIN_STEM:
            return w[: -len(sfx)]

    for sfx in _RU_SUFFIXES:
        if w.endswith(sfx) and len(w) - len(sfx) >= _MIN_STEM:
            return w[: -len(sfx)]

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
        p.name
        + " "
        + p.description
        + " "
        + p.category
        + " "
        + " ".join(p.tags)
        + " "
        + p.id
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
