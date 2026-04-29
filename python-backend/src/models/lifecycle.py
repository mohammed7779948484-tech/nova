"""Conversation lifecycle state machine.

Defines valid state transitions for conversation status,
ensuring the lifecycle follows the spec:
    active → {escalated, resolved}
    escalated → {active, handed_off, resolved}
    handed_off → {active, resolved}
    resolved → {}  (terminal state)
"""

from __future__ import annotations

from src.models.enums import ConversationStatus

VALID_TRANSITIONS: dict[ConversationStatus, set[ConversationStatus]] = {
    ConversationStatus.ACTIVE: {
        ConversationStatus.ESCALATED,
        ConversationStatus.RESOLVED,
    },
    ConversationStatus.ESCALATED: {
        ConversationStatus.ACTIVE,
        ConversationStatus.HANDED_OFF,
        ConversationStatus.RESOLVED,
    },
    ConversationStatus.HANDED_OFF: {
        ConversationStatus.ACTIVE,
        ConversationStatus.RESOLVED,
    },
    ConversationStatus.RESOLVED: set(),  # terminal state
}


def validate_transition(current: ConversationStatus, target: ConversationStatus) -> bool:
    """Check whether a transition from current to target is allowed.

    Args:
        current: The current conversation status.
        target: The desired next status.

    Returns:
        True if the transition is valid, False otherwise.
    """
    allowed = VALID_TRANSITIONS.get(current, set())
    return target in allowed


def transition_or_raise(current: ConversationStatus, target: ConversationStatus) -> None:
    """Validate a transition and raise ValueError if invalid.

    Args:
        current: The current conversation status.
        target: The desired next status.

    Raises:
        ValueError: If the transition is not allowed.
    """
    if not validate_transition(current, target):
        raise ValueError(
            f"Invalid transition: {current.value} → {target.value}. "
            f"Allowed transitions from {current.value}: "
            f"{[s.value for s in VALID_TRANSITIONS.get(current, set())]}"
        )
