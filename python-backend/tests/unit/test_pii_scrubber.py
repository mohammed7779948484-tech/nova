"""Tests for PII scrubbing in structured logs (FR-045).

Verifies that phone numbers and email addresses are replaced with
[PHONE] and [EMAIL] tokens before logs are emitted.
"""

from src.core.pii_scrubber import scrub_pii


class TestPIIScrubber:
    """PII scrubbing for structured logging (FR-045)."""

    def test_phone_numbers_scrubbed(self):
        """Phone numbers in log output are replaced with [PHONE]."""
        input_text = "Customer called from +1234567890 about order"
        result = scrub_pii(input_text)
        assert "+1234567890" not in result, "Phone number should be scrubbed"
        assert "[PHONE]" in result, "Scrubbed phone token should appear"

    def test_email_addresses_scrubbed(self):
        """Email addresses in log output are replaced with [EMAIL]."""
        input_text = "User email is john.doe@example.com for tenant"
        result = scrub_pii(input_text)
        assert "john.doe@example.com" not in result, "Email should be scrubbed"
        assert "[EMAIL]" in result, "Scrubbed email token should appear"

    def test_multiple_pii_types_scrubbed(self):
        """Both phone and email in same text are scrubbed."""
        input_text = "Contact +1234567890 or admin@corp.io for help"
        result = scrub_pii(input_text)
        assert "+1234567890" not in result
        assert "admin@corp.io" not in result
        assert "[PHONE]" in result
        assert "[EMAIL]" in result

    def test_no_pii_left_untouched(self):
        """Text without PII passes through unchanged."""
        input_text = "Normal log message with no sensitive data"
        result = scrub_pii(input_text)
        assert result == input_text

    def test_international_phone_numbers_scrubbed(self):
        """International format phone numbers are scrubbed."""
        input_text = "Called from +966501234567 and +442071234567"
        result = scrub_pii(input_text)
        assert "+966501234567" not in result
        assert "+442071234567" not in result
        assert result.count("[PHONE]") == 2
