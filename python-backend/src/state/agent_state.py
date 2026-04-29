"""Agent state definition.

Single source of truth for all data flowing through the sales agent graph.
State is tenant-agnostic — tenant context is injected via runtime config.
"""

from __future__ import annotations

from typing import Annotated, NotRequired

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class SalesAgentState(TypedDict):
    """State for the sales agent graph.

    Attributes:
        messages: Conversation history. Uses add_messages reducer
                  so messages accumulate across nodes automatically.
        channel: The communication channel (e.g. "web", "whatsapp").
        channel_user_id: The user's ID on the given channel.
        escalation_reason: Optional reason for escalation (set by assistant
                          when routing to escalation node).
    """

    messages: Annotated[list[AnyMessage], add_messages]
    channel: str
    channel_user_id: str
    escalation_reason: NotRequired[str]