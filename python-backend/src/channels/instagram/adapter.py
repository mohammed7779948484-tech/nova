"""Instagram adapter scaffold."""

from datetime import datetime, timezone

from src.channels.base import ChannelAdapter
from src.models.message import InboundMessage, OutboundMessage


class InstagramAdapter(ChannelAdapter):
    """Translates Instagram webhooks to InboundMessage, and OutboundMessage to API."""

    def parse_webhook(self, raw: dict) -> InboundMessage:
        entry = raw.get("entry", [{}])[0]
        messaging = entry.get("messaging", [{}])[0]
        msg = messaging.get("message", {})
        
        return InboundMessage(
            channel="instagram",
            channel_message_id=msg.get("mid", "unknown"),
            channel_user_id=messaging.get("sender", {}).get("id", "unknown"),
            tenant_id="flower_shop", # proxy for now
            text=msg.get("text"),
            received_at=datetime.now(timezone.utc),
            raw_payload=raw
        )

    async def send_reply(self, channel_user_id: str, message: OutboundMessage) -> None:
        """Call Instagram Messenger API."""
        print(f"[Instagram] Sending to {channel_user_id}: {message.text}")
