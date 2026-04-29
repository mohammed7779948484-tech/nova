"""Telegram adapter scaffold."""

from datetime import datetime, timezone

from src.channels.base import ChannelAdapter
from src.models.message import InboundMessage, OutboundMessage


class TelegramAdapter(ChannelAdapter):
    """Translates Telegram webhooks to InboundMessage, and OutboundMessage to TG API."""

    def parse_webhook(self, raw: dict) -> InboundMessage:
        msg = raw.get("message", {})
        return InboundMessage(
            channel="telegram",
            channel_message_id=str(msg.get("message_id", "")),
            channel_user_id=str(msg.get("from", {}).get("id", "")),
            tenant_id="flower_shop", # proxy for now
            text=msg.get("text"),
            received_at=datetime.now(timezone.utc),
            raw_payload=raw
        )

    async def send_reply(self, channel_user_id: str, message: OutboundMessage) -> None:
        """Call Telegram API to send message."""
        print(f"[Telegram] Sending to {channel_user_id}: {message.text}")
