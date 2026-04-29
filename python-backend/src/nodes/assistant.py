"""Node: LLM assistant — the core chat node.

Loads tenant config, builds the system prompt, binds tools,
and invokes the model. Uses Command for routing: if the LLM
makes tool calls → go to "tools", otherwise → END.

Tenant config is loaded from Supabase DB (async) with YAML fallback.
"""

from __future__ import annotations

import logging
from typing import Literal

from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from src.config.tenant_config import TenantConfig, async_get_tenant
from src.state.agent_state import SalesAgentState
from src.tools import ALL_TOOLS

logger = logging.getLogger(__name__)


def _build_system_prompt(
    tc: TenantConfig,
    channel: str | None = None,
    messages: list[BaseMessage] | None = None,
) -> str:
    """Build a system prompt from the tenant's config.

    Args:
        tc: TenantConfig (loaded from DB or YAML).
        channel: The communication channel (e.g. "web", "whatsapp").
        messages: Conversation history for context summary injection.
    """
    agent = tc.agent

    products_hint = (
        "You have tools to search products, find promotions, "
        "send product images, and find similar items by image description.\n\n"
        "CRITICAL RULES FOR TOOLS:\n"
        "- ALWAYS call search_products FIRST when a customer asks about products, "
        "categories, flowers, bouquets, or anything related to the catalog.\n"
        "- NEVER describe, list, or suggest products from your own knowledge. "
        "You MUST use the tools to find real products.\n"
        "- If search returns no results, say so honestly — do NOT invent categories or items.\n"
        "- To show product photos, ALWAYS call the get_product_details tool with the product_id. "
        "NEVER paste image URLs directly into your text response. "
        "NEVER use markdown image syntax like ![](url). "
        "The get_product_details tool handles rendering on the customer's device.\n"
        "- When the customer says 'покажи', 'фото', 'show', or similar — "
        "call get_product_details for each relevant product."
    )

    channel_hint = f"You are chatting on {channel}.\n\n" if channel else ""

    instructions_block = ""
    if tc.instructions:
        instructions_block = (
            "\n## Custom Instructions\n"
            + "\n".join(f"- {i}" for i in tc.instructions)
            + "\n"
        )

    context_block = ""
    if messages and len(messages) > 5:
        topics = _extract_topics(messages)
        if topics:
            context_block = (
                "\n## Conversation Context\n"
                "Previous topics discussed:\n"
                + "\n".join(f"- {t}" for t in topics)
                + "\n"
            )

    return (
        f"You are {agent.name}, a {agent.role} at {tc.business_name}.\n\n"
        f"{agent.personality}\n\n"
        f"{channel_hint}"
        f"## Rules\n"
        + "\n".join(f"- {r}" for r in agent.rules)
        + f"\n\n## Important\n{products_hint}\n"
        f"\n## Language\n"
        f"You MUST respond ONLY in: {tc.language}. "
        f"If language is 'ru', respond in Russian (NOT Kazakh, NOT English). "
        f"Match the customer's language only if they explicitly write in another language.\n"
        + instructions_block
        + context_block
    )


def _extract_topics(messages: list[BaseMessage], max_topics: int = 5) -> list[str]:
    """Extract key topics from conversation history for context summary.

    Args:
        messages: Conversation messages (oldest first).
        max_topics: Maximum number of topics to extract.

    Returns:
        List of topic strings extracted from user/assistant messages.
    """
    topics: list[str] = []
    seen: set[str] = set()

    for msg in messages:
        content = msg.content if isinstance(msg.content, str) else ""
        content_lower = content.lower().strip()
        if not content_lower or len(content_lower) < 5:
            continue

        words = content_lower.split()
        for word in words:
            if len(word) > 3 and word not in seen and not word.startswith(("http", "@", "+")):
                seen.add(word)
                topics.append(content if len(content) < 60 else word)
                if len(topics) >= max_topics:
                    return topics
                break

    return topics[:max_topics]


def _should_escalate(ai_message: AIMessage) -> str | None:
    """Check if an AI message indicates escalation is needed.

    Detects escalation signals in the AI response content:
    - Explicit escalation request phrases
    - Low confidence indicators

    Returns:
        Escalation reason string if escalation is needed, None otherwise.
    """
    content = ai_message.content.lower() if isinstance(ai_message.content, str) else ""

    # Customer-requested escalation patterns
    escalation_phrases = [
        "speak to a supervisor",
        "talk to a human",
        "speak to a manager",
        "connect me to a human",
        "i want to escalate",
        "transfer to supervisor",
        "escalate this",
        "[escalate]",
    ]

    for phrase in escalation_phrases:
        if phrase in content:
            return "customer_request"

    # Low confidence patterns
    low_confidence_phrases = [
        "i'm not sure how to",
        "i cannot assist with",
        "beyond my capabilities",
        "i'm unable to help",
        "outside my expertise",
    ]

    for phrase in low_confidence_phrases:
        if phrase in content:
            return "low_confidence"

    return None


async def assistant_node(
    state: SalesAgentState,
    config: RunnableConfig,
) -> Command[Literal["tools", "escalate", "__end__"]]:
    """Invoke the LLM and route based on response.

    Routing logic:
    - If LLM returns graceful failure string → END
    - If LLM made tool calls → "tools"
    - If LLM response contains escalation triggers → "escalate"
    - Otherwise → END
    """
    from src.services.llm_service import llm_service

    tenant_id = config["configurable"]["tenant_id"]

    tc = await async_get_tenant(tenant_id)

    messages = state.get("messages", [])

    channel = state.get("channel")
    system = SystemMessage(content=_build_system_prompt(tc, channel, messages))
    full_messages = [system] + messages

    logger.debug(
        "assistant_node: tenant=%s, channel=%s, messages=%d",
        tenant_id, channel, len(messages),
    )

    result = await llm_service.call(
        full_messages,
        tenant_config=tc,
        config=config,
        tools=ALL_TOOLS,
    )

    if isinstance(result, str):
        return Command(
            update={"messages": [AIMessage(content=result)]},
            goto="__end__",
        )

    if result.tool_calls:
        return Command(
            update={"messages": [result]},
            goto="tools",
        )

    # Check for escalation triggers in the AI response
    escalation_reason = _should_escalate(result)
    if escalation_reason:
        logger.info("assistant_escalating reason=%s", escalation_reason)
        return Command(
            update={
                "messages": [result],
                "escalation_reason": escalation_reason,
            },
            goto="escalate",
        )

    return Command(
        update={"messages": [result]},
        goto="__end__",
    )
