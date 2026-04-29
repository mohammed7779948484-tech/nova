"""Base channel adapter protocol."""

from typing import Protocol

from src.models.message import InboundMessage, OutboundMessage


class ChannelAdapter(Protocol):
    """Interface that every channel (whatsapp, telegram, web) must implement."""

    def parse_webhook(self, raw: dict) -> InboundMessage:
        """Parse raw platform webhook payload into common InboundMessage."""
        ...

    async def send_reply(
        self, channel_user_id: str, message: OutboundMessage
    ) -> None:
        """Send the mapped OutboundMessage back to the user via platform API."""
        ...
