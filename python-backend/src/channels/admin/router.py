"""Admin router — conversation management and listing endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query

from src.services.conversation_service import conversation_service

router = APIRouter(prefix="/api", tags=["admin"])


@router.get("/conversations")
async def list_conversations(
    agent_id: str = Query(..., description="UUID of the agent to filter by"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
):
    """List conversations for an agent with pagination."""
    try:
        uuid.UUID(agent_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid agent_id format")

    rows, total = await conversation_service.list_conversations(
        agent_id=agent_id,
        page=page,
        limit=limit,
        status_filter=status,
    )

    return {
        "conversations": rows,
        "total": total,
        "page": page,
        "limit": limit,
    }


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: str):
    """Get all messages for a specific conversation."""
    try:
        conv_uuid = uuid.UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid conversation_id format")

    messages = await conversation_service.get_messages(str(conv_uuid))

    return {
        "conversation_id": str(conv_uuid),
        "messages": messages,
    }


@router.post("/conversations/{conversation_id}/resolve")
async def resolve_conversation(conversation_id: str):
    """Mark a conversation as resolved."""
    try:
        conv_uuid = uuid.UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid conversation_id format")

    result = await conversation_service.update_status(str(conv_uuid), "resolved")

    return {
        "conversation_id": str(conv_uuid),
        "status": result.get("status", "resolved"),
    }