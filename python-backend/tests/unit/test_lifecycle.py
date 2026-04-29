"""T038: Test lifecycle state transitions.

PDCA Called Shot:
- test_valid_transitions: verify all allowed transitions:
  active→escalated, escalated→active, escalated→handed_off,
  handed_off→active, active→resolved, escalated→resolved,
  handed_off→resolved.
  Expected RED: ImportError: cannot import name 'validate_transition'.
- test_invalid_transitions: verify disallowed:
  resolved→active, active→handed_off (must go through escalated).
  Expected RED: same ImportError.
"""

from __future__ import annotations

import pytest

from src.models.enums import ConversationStatus


class TestLifecycleValidTransitions:

    @pytest.mark.asyncio
    async def test_valid_transitions(self):
        """All allowed state transitions should return True."""
        from src.models.lifecycle import validate_transition

        # active → escalated
        assert validate_transition(
            ConversationStatus.ACTIVE, ConversationStatus.ESCALATED
        ), "active → escalated should be valid"

        # active → resolved
        assert validate_transition(
            ConversationStatus.ACTIVE, ConversationStatus.RESOLVED
        ), "active → resolved should be valid"

        # escalated → active (resume)
        assert validate_transition(
            ConversationStatus.ESCALATED, ConversationStatus.ACTIVE
        ), "escalated → active should be valid"

        # escalated → handed_off
        assert validate_transition(
            ConversationStatus.ESCALATED, ConversationStatus.HANDED_OFF
        ), "escalated → handed_off should be valid"

        # escalated → resolved
        assert validate_transition(
            ConversationStatus.ESCALATED, ConversationStatus.RESOLVED
        ), "escalated → resolved should be valid"

        # handed_off → active
        assert validate_transition(
            ConversationStatus.HANDED_OFF, ConversationStatus.ACTIVE
        ), "handed_off → active should be valid"

        # handed_off → resolved
        assert validate_transition(
            ConversationStatus.HANDED_OFF, ConversationStatus.RESOLVED
        ), "handed_off → resolved should be valid"


class TestLifecycleInvalidTransitions:

    @pytest.mark.asyncio
    async def test_invalid_transitions(self):
        """Disallowed transitions should return False."""
        from src.models.lifecycle import validate_transition

        # resolved → anything (resolved is terminal)
        assert not validate_transition(
            ConversationStatus.RESOLVED, ConversationStatus.ACTIVE
        ), "resolved → active should be invalid"

        assert not validate_transition(
            ConversationStatus.RESOLVED, ConversationStatus.ESCALATED
        ), "resolved → escalated should be invalid"

        assert not validate_transition(
            ConversationStatus.RESOLVED, ConversationStatus.HANDED_OFF
        ), "resolved → handed_off should be invalid"

        # active → handed_off (must go through escalated first)
        assert not validate_transition(
            ConversationStatus.ACTIVE, ConversationStatus.HANDED_OFF
        ), "active → handed_off should be invalid (must escalate first)"


class TestLifecycleTransitionOrRaise:

    @pytest.mark.asyncio
    async def test_valid_transition_does_not_raise(self):
        """Valid transitions should not raise."""
        from src.models.lifecycle import transition_or_raise

        # Should not raise
        transition_or_raise(ConversationStatus.ACTIVE, ConversationStatus.ESCALATED)

    @pytest.mark.asyncio
    async def test_invalid_transition_raises_value_error(self):
        """Invalid transitions should raise ValueError."""
        from src.models.lifecycle import transition_or_raise

        with pytest.raises(ValueError, match="Invalid transition"):
            transition_or_raise(
                ConversationStatus.RESOLVED, ConversationStatus.ACTIVE
            )

    @pytest.mark.asyncio
    async def test_same_status_is_invalid(self):
        """Transition from a status to itself should be invalid."""
        from src.models.lifecycle import validate_transition

        assert not validate_transition(
            ConversationStatus.ACTIVE, ConversationStatus.ACTIVE
        ), "active → active should be invalid"
