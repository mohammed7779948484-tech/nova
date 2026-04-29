"""T036: Test escalation node — interrupt() behavior.

PDCA Called Shot:
- test_escalation_node_interrupts_graph: invoke escalation node,
  verify it calls interrupt() with escalation reason dict.
  Expected RED: ImportError: cannot import name 'escalation_node'
  from 'src.nodes.escalation' (file doesn't exist).
- test_escalation_node_returns_command_with_interrupt:
  verify the node returns a Command that updates messages and routes
  back to assistant after resume.
  Expected RED: same ImportError.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from langchain_core.messages import AIMessage

from src.models.enums import EscalationReason


class TestEscalationNode:

    @pytest.mark.asyncio
    async def test_escalation_node_interrupts_graph(self):
        """escalation_node should call interrupt() with escalation reason."""
        from src.nodes.escalation import escalation_node

        state = {
            "messages": [AIMessage(content="I need to escalate this")],
            "channel": "web",
            "channel_user_id": "test-user",
        }

        with patch("src.nodes.escalation.interrupt") as mock_interrupt:
            mock_interrupt.return_value = "Supervisor says: approve the refund"

            result = await escalation_node(state, {})

            # Verify interrupt was called with reason and message
            mock_interrupt.assert_called_once()
            call_args = mock_interrupt.call_args[0][0]
            assert isinstance(call_args, dict), (
                f"interrupt() should be called with a dict, got {type(call_args)}"
            )
            assert "reason" in call_args, (
                "interrupt() payload must contain 'reason' key"
            )
            assert "message" in call_args, (
                "interrupt() payload must contain 'message' key"
            )

    @pytest.mark.asyncio
    async def test_escalation_node_uses_custom_escalation_reason(self):
        """escalation_node should use escalation_reason from state if present."""
        from src.nodes.escalation import escalation_node

        state = {
            "messages": [AIMessage(content="Complex issue")],
            "channel": "web",
            "channel_user_id": "test-user",
            "escalation_reason": "low_confidence",
        }

        with patch("src.nodes.escalation.interrupt") as mock_interrupt:
            mock_interrupt.return_value = "Supervisor response"

            await escalation_node(state, {})

            call_args = mock_interrupt.call_args[0][0]
            assert call_args["reason"] == "low_confidence", (
                f"Expected reason='low_confidence', got {call_args['reason']}"
            )

    @pytest.mark.asyncio
    async def test_escalation_node_defaults_to_customer_request(self):
        """escalation_node should default to 'customer_request' if no reason in state."""
        from src.nodes.escalation import escalation_node

        state = {
            "messages": [AIMessage(content="Help")],
            "channel": "web",
            "channel_user_id": "test-user",
        }

        with patch("src.nodes.escalation.interrupt") as mock_interrupt:
            mock_interrupt.return_value = "Supervisor response"

            await escalation_node(state, {})

            call_args = mock_interrupt.call_args[0][0]
            assert call_args["reason"] == "customer_request", (
                f"Expected default reason='customer_request', got {call_args['reason']}"
            )
