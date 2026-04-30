"""Tests for WhatsApp typing indicator (FR-033).

Verifies that the typing indicator is sent via the Meta API
before the AI processes the message.

DEFERRED: WhatsApp channel tasks (Phase 7 / FR-033) are temporarily
deferred per user agreement. These tests will be enabled when the
WhatsApp feature is implemented.
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.channels.whatsapp.adapter import WhatsAppAdapter

pytestmark = pytest.mark.skip(reason="DEFERRED: WhatsApp channel (FR-033) — to be implemented in future phase")


class TestWhatsAppTypingIndicator:
    """WhatsApp typing indicator (FR-033)."""

    @pytest.mark.asyncio
    async def test_send_typing_indicator_calls_api(self):
        """send_typing_indicator() POSTs to Meta API with typing action."""
        adapter = WhatsAppAdapter()

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value.status_code = 200

            await adapter.send_typing_indicator(
                phone_number_id="test_phone_id",
                access_token="test_token",
                recipient_phone="+1234567890",
            )

            # Verify POST was called to the Meta API
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            url = call_args.kwargs.get("url", call_args.args[0] if call_args.args else "")
            assert "graph.facebook.com" in str(url), (
                f"Expected Meta Graph API URL, got: {url}"
            )
            assert "test_phone_id" in str(url), (
                "URL should contain phone_number_id"
            )
            # Verify the body contains messaging_product
            body = call_args.kwargs.get("json", {})
            assert body.get("messaging_product") == "whatsapp", (
                "Body must contain messaging_product=whatsapp"
            )
