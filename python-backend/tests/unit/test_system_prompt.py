"""T009: Test instruction injection into system prompt.

PDCA Called Shot:
- test_system_prompt_includes_instructions: call _build_system_prompt() with a
  TenantConfig that has instructions, verify the prompt contains those instruction texts.
  Expected RED: AssertionError 'Always greet in Arabic' not found in prompt
"""

import pytest

from src.config.tenant_config import AgentConfig, TenantConfig
from src.nodes.assistant import _build_system_prompt


class TestSystemPromptInstructions:

    def test_system_prompt_includes_instructions(self):
        """_build_system_prompt must include custom instructions in the prompt."""
        tc = TenantConfig(
            tenant_id="test_shop",
            business_name="Test Shop",
            language="en",
            agent=AgentConfig(
                name="TestBot",
                role="assistant",
                personality="You are helpful.",
                rules=["Be polite"],
            ),
            instructions=["Always greet in Arabic", "Never discuss competitors"],
        )

        prompt = _build_system_prompt(tc, channel="web")

        assert "Always greet in Arabic" in prompt, (
            "Custom instruction 'Always greet in Arabic' not found in prompt"
        )
        assert "Never discuss competitors" in prompt, (
            "Custom instruction 'Never discuss competitors' not found in prompt"
        )

    def test_system_prompt_without_instructions(self):
        """_build_system_prompt should work fine with no custom instructions."""
        tc = TenantConfig(
            tenant_id="test_shop",
            business_name="Test Shop",
            language="en",
            agent=AgentConfig(
                name="TestBot",
                role="assistant",
                personality="You are helpful.",
            ),
            instructions=[],
        )

        prompt = _build_system_prompt(tc, channel="web")
        assert "Custom Instructions" not in prompt