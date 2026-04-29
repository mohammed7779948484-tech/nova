"""Enumerations for conversation lifecycle, message roles, and escalation reasons."""

from __future__ import annotations

from enum import Enum


class ConversationStatus(str, Enum):
    ACTIVE = "active"
    ESCALATED = "escalated"
    HANDED_OFF = "handed_off"
    RESOLVED = "resolved"


class MessageRole(str, Enum):
    CUSTOMER = "customer"
    ASSISTANT = "assistant"
    SUPERVISOR = "supervisor"


class EscalationReason(str, Enum):
    CUSTOMER_REQUEST = "customer_request"
    LOW_CONFIDENCE = "low_confidence"
    COMPLEX_ISSUE = "complex_issue"
