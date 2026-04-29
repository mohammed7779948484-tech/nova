"""Pydantic v2 request/response schemas for all API endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from src.models.enums import ConversationStatus
from pydantic import BaseModel, ConfigDict, Field


class PaginationParams(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)


class ChatRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message: str = Field(..., min_length=1)
    tenant_slug: str = Field(..., min_length=1)
    session_id: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    response: str
    session_id: str


class ConversationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: str
    channel: str
    customer_phone: str | None = None
    status: ConversationStatus
    message_count: int = 0
    started_at: datetime
    last_message_at: datetime


class ConversationListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    conversations: list[ConversationItem]
    total: int
    page: int
    limit: int


class MessageItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: str
    content: str
    created_at: datetime


class ConversationDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    conversation_id: UUID
    messages: list[MessageItem]


class EscalationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    conversation_id: UUID
    session_id: str
    status: ConversationStatus
    reason: str | None = None
    customer_phone: str | None = None
    escalated_at: datetime | None = None
    last_message: str | None = None


class EscalationListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    escalations: list[EscalationItem]
    total: int
    page: int
    limit: int


class EscalationResumeRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    supervisor_response: str = Field(..., min_length=1)


class EscalationResumeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    conversation_id: UUID
    status: ConversationStatus
    ai_response: str | None = None


class HandoffRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    reason: str | None = None


class SupervisorMessageRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    content: str = Field(..., min_length=1)
