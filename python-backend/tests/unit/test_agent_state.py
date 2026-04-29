"""T006: Test dead state field removal in SalesAgentState.

PDCA Called Shot:
- test_state_has_no_dead_fields: verify SalesAgentState has exactly 3 keys,
  no matched_products or product_images.
  Expected RED: AssertionError 'matched_products' found in state keys
- test_state_can_be_instantiated_minimal: verify state can be created with
  only messages, channel, channel_user_id.
  Expected RED: TypeError for missing required keys (dead fields still required)
"""

import pytest

from src.state.agent_state import SalesAgentState


class TestAgentStateNoDeadFields:

    def test_state_has_no_dead_fields(self):
        """SalesAgentState should have exactly 4 keys: messages, channel, channel_user_id, escalation_reason."""
        expected_keys = {"messages", "channel", "channel_user_id", "escalation_reason"}
        actual_keys = set(SalesAgentState.__annotations__.keys())
        assert actual_keys == expected_keys, (
            f"Expected keys {expected_keys}, got {actual_keys}. "
            f"Dead fields still present: {actual_keys - expected_keys}"
        )

    def test_state_can_be_instantiated_minimal(self):
        """SalesAgentState should be creatable with just the 3 required fields (escalation_reason is NotRequired)."""
        state: SalesAgentState = {
            "messages": [],
            "channel": "web",
            "channel_user_id": "test-user",
        }
        assert "messages" in state
        assert state["channel"] == "web"
        assert state["channel_user_id"] == "test-user"