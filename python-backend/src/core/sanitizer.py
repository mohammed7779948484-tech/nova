"""Input sanitization and prompt-injection detection.

Provides:
- sanitize_input(): strip HTML, truncate, normalize whitespace
- detect_prompt_injection(): flag common injection patterns
"""

from __future__ import annotations

import re

# Regex to strip entire script/style blocks (tag + content)
_SCRIPT_BLOCK_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE)
# Regex to strip remaining HTML tags
_HTML_TAG_RE = re.compile(r"<[^>]+>")

# Common prompt-injection patterns (case-insensitive)
_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+previous\s+instructions", re.IGNORECASE),
    re.compile(r"system\s+prompt\s*:", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+", re.IGNORECASE),
    re.compile(r"forget\s+everything", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(previous|above)\s+", re.IGNORECASE),
    re.compile(r"new\s+instructions?\s*:", re.IGNORECASE),
]


def sanitize_input(text: str, max_length: int = 4000) -> str:
    """Sanitize user input by stripping HTML, truncating, and normalizing.

    Steps:
    1. Strip HTML tags
    2. Collapse whitespace (spaces, newlines, tabs) into single spaces
    3. Strip leading/trailing whitespace
    4. Truncate to max_length characters
    """
    # Strip script/style blocks first (tag + content), then remaining tags
    cleaned = _SCRIPT_BLOCK_RE.sub("", text)
    cleaned = _HTML_TAG_RE.sub("", cleaned)
    # Normalize whitespace: collapse runs of whitespace into a single space
    cleaned = re.sub(r"\s+", " ", cleaned)
    # Strip leading/trailing
    cleaned = cleaned.strip()
    # Truncate
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]
    return cleaned


def detect_prompt_injection(text: str) -> bool:
    """Detect common prompt-injection patterns in user input.

    Returns True if any known injection pattern is found.
    This is a basic heuristic check — not a security guarantee.
    """
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            return True
    return False
