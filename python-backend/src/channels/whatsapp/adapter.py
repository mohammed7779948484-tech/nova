"""WhatsApp Cloud API adapter."""

from datetime import datetime, timezone

from src.channels.base import ChannelAdapter
from src.models.message import InboundMessage, OutboundMessage


class WhatsAppAdapter(ChannelAdapter):
    """Translates WhatsApp webhooks to InboundMessages, and OutboundMessages to WhatsApp API."""

    def parse_webhook(self, raw: dict) -> InboundMessage:
        """Parse raw WhatsApp Cloud API webhook."""
        # This is a scaffold. In production, properly parse the WA payload structure.
        entry = raw.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [{}])
        msg_obj = messages[0] if messages else {}
        
        # In a real system, you'd map the WhatsApp Business Account ID to a tenant_id.
        # waba_id = value.get("metadata", {}).get("display_phone_number")
        
        return InboundMessage(
            channel="whatsapp",
            channel_message_id=msg_obj.get("id", "test-wa-id"),
            channel_user_id=msg_obj.get("from", "test-user"),
            tenant_id="flower_shop",  # placeholder for scaffold
            text=msg_obj.get("text", {}).get("body"),
            received_at=datetime.now(timezone.utc),
            raw_payload=raw
        )

    async def send_reply(
        self, channel_user_id: str, message: OutboundMessage
    ) -> None:
        """Send message back to user via WhatsApp Cloud API."""
        # Use HTTPX/Aiohttp to call https://graph.facebook.com/v19.0/.../messages
        print(f"[WhatsApp] Sending to {channel_user_id}: {message.text}")
        for media in message.media:
            print(f"[WhatsApp] Sending Media ({media.type}): {media.url}")
