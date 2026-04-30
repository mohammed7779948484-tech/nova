"""PII scrubbing processor for structured logging (FR-045).

Replaces phone numbers and email addresses with [PHONE] and [EMAIL]
tokens before logs are emitted, ensuring no PII leaks into log files.
"""

from __future__ import annotations

import re
import structlog

# Phone: matches + followed by 10+ digits (with optional spaces/hyphens)
_PHONE_PATTERN = re.compile(r"\+?\d[\d\s\-]{8,}\d")

# Email: matches standard email format
_EMAIL_PATTERN = re.compile(r"\S+@\S+\.\S+")


def scrub_pii(value: str) -> str:
    """Replace PII in a string with safe tokens.

    Args:
        value: The string potentially containing PII.

    Returns:
        The string with phone numbers replaced by [PHONE] and
        email addresses replaced by [EMAIL].
    """
    # Process emails first (they might contain digits that look like phone)
    value = _EMAIL_PATTERN.sub("[EMAIL]", value)
    # Then process phone numbers
    value = _PHONE_PATTERN.sub("[PHONE]", value)
    return value


class PIIScrubberProcessor:
    """structlog processor that scrubs PII from log events.

    Add this processor before JSONRenderer in the structlog pipeline.
    """

    def __call__(
        self, logger: str, method: str, event_dict: structlog.types.EventDict
    ) -> structlog.types.EventDict:
        """Scrub PII from all string values in the event dict."""
        for key, value in event_dict.items():
            if isinstance(value, str):
                event_dict[key] = scrub_pii(value)
        return event_dict
