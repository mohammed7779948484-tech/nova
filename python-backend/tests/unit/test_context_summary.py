"""T031: Test context summary injection into system prompt.

PDCA Called Shot:
- test_system_prompt_includes_context_summary: invoke _build_system_prompt() with
  messages parameter having > 5 messages, verify context section is included.
  Expected RED: '## Conversation Context' not found in prompt
- test_system_prompt_without_history_no_context: with <= 5 messages, no context section.
  Expected RED: context section present when it shouldn't be
- test_system_prompt_without_messages_param_no_context: backward compat, no messages param.
  Expected RED: TypeError or context section present
- test_context_summary_includes_topics: context mentions discussed products.
  Expected RED: '## Conversation Context' not found
"""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage

from src.config.tenant_config import AgentConfig, TenantConfig


def _make_tc(**overrides) -> TenantConfig:
    """Create a TenantConfig with sensible defaults for testing."""
    defaults = {
        "tenant_id": "test",
        "business_name": "Test Shop",
        "language": "en",
    }
    defaults.update(overrides)
    return TenantConfig(**defaults)


class TestContextSummary:

    def test_system_prompt_includes_context_summary(self):
        """When conversation has > 5 messages, prompt includes context section."""
        from src.nodes.assistant import _build_system_prompt

        tc = _make_tc(
            agent=AgentConfig(
                name="Test Bot",
                role="assistant",
                personality="helpful",
                rules=["be nice"],
            ),
        )

        messages = [
            HumanMessage(content=f"message number {i} about products")
            for i in range(6)
        ]

        prompt = _build_system_prompt(tc, channel="web", messages=messages)

        assert "## Conversation Context" in prompt, (
            "Expected '## Conversation Context' section in prompt when > 5 messages"
        )

    def test_system_prompt_without_history_no_context(self):
        """When conversation has <= 5 messages, no context section."""
        from src.nodes.assistant import _build_system_prompt

        tc = _make_tc(
            agent=AgentConfig(
                name="Test Bot",
                role="assistant",
                personality="helpful",
                rules=["be nice"],
            ),
        )

        messages = [
            HumanMessage(content=f"message number {i} about products")
            for i in range(3)
        ]

        prompt = _build_system_prompt(tc, channel="web", messages=messages)

        assert "## Conversation Context" not in prompt, (
            "Context section should not appear with <= 5 messages"
        )

    def test_system_prompt_without_messages_param_no_context(self):
        """Backward compatibility: no messages param = no context section."""
        from src.nodes.assistant import _build_system_prompt

        tc = _make_tc(
            agent=AgentConfig(
                name="Test Bot",
                role="assistant",
                personality="helpful",
                rules=["be nice"],
            ),
        )

        prompt = _build_system_prompt(tc, channel="web")

        assert "## Conversation Context" not in prompt

    def test_context_summary_includes_topics(self):
        """Context summary mentions products or topics discussed."""
        from src.nodes.assistant import _build_system_prompt

        tc = _make_tc(
            agent=AgentConfig(
                name="Test Bot",
                role="assistant",
                personality="helpful",
                rules=["be nice"],
            ),
        )

        messages = [
            HumanMessage(content="I want roses"),
            AIMessage(content="We have red and white roses"),
            HumanMessage(content="Show me the red ones"),
            AIMessage(content="Here are our red roses"),
            HumanMessage(content="What about white?"),
            AIMessage(content="We have white roses too"),
            HumanMessage(content="I'll take both"),
        ]

        prompt = _build_system_prompt(tc, channel="web", messages=messages)

        assert "## Conversation Context" in prompt
        assert "roses" in prompt.lower() or "topics" in prompt.lower()
