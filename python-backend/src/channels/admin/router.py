"""Admin router — conversation management, escalation, and supervisor endpoints.

Endpoints:
- GET  /api/conversations                  — list conversations
- GET  /api/conversations/{id}/messages    — get messages
- POST /api/conversations/{id}/resolve     — resolve conversation
- POST /api/conversations/{id}/message     — supervisor direct message
- POST /api/conversations/{id}/return      — return from handoff to AI
- GET  /api/escalations                    — list escalated conversations
- POST /api/escalations/{id}/resume        — resume with supervisor response
- POST /api/escalations/{id}/handoff       — handoff to human agent
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from src.models.schemas import EscalationResumeRequest, SupervisorMessageRequest
from src.services.conversation_service import conversation_service
from src.services.graph_service import graph_service

router = APIRouter(prefix="/api", tags=["admin"])


# ── Conversation endpoints ──────────────────────────────────────────────


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
        agent_id=agent_id, page=page, limit=limit, status_filter=status,
    )

    return {"conversations": rows, "total": total, "page": page, "limit": limit}


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: str):
    """Get all messages for a specific conversation."""
    try:
        conv_uuid = uuid.UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid conversation_id format")

    messages = await conversation_service.get_messages(str(conv_uuid))
    return {"conversation_id": str(conv_uuid), "messages": messages}


@router.post("/conversations/{conversation_id}/resolve")
async def resolve_conversation(conversation_id: str):
    """Mark a conversation as resolved."""
    try:
        conv_uuid = uuid.UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid conversation_id format")

    result = await conversation_service.update_status(str(conv_uuid), "resolved")
    return {"conversation_id": str(conv_uuid), "status": result.get("status", "resolved")}


@router.post("/conversations/{conversation_id}/message")
async def supervisor_send_message(conversation_id: str, body: SupervisorMessageRequest):
    """Send a direct supervisor message during handoff.

    Adds the supervisor's message to the conversation without
    resuming the AI graph.
    """
    try:
        conv_uuid = uuid.UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid conversation_id format")

    result = await conversation_service.add_message(
        conversation_id=str(conv_uuid), role="supervisor", content=body.content,
    )
    return {"conversation_id": str(conv_uuid), "message": result}


@router.post("/conversations/{conversation_id}/return")
async def return_from_handoff(conversation_id: str):
    """Return a handed-off conversation back to the AI.

    Transitions the conversation from 'handed_off' to 'active',
    returning control to the AI agent.
    """
    try:
        conv_uuid = uuid.UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid conversation_id format")

    result = await conversation_service.update_status(str(conv_uuid), "active")
    if result.get("status") != "active":
        raise HTTPException(
            status_code=409,
            detail=f"Cannot return conversation: current status is '{result.get('status')}'",
        )
    return {"conversation_id": str(conv_uuid), "status": "active"}


# ── Escalation endpoints ───────────────────────────────────────────────


def _enrich_escalation(row: dict) -> dict:
    """Add escalation-specific fields to a conversation row.

    Populates: reason, escalated_at, wait_time_seconds, last_message.
    """
    enriched = {
        "conversation_id": row.get("id"),
        "session_id": row.get("session_id"),
        "status": row.get("status"),
        "customer_phone": row.get("customer_phone"),
        "channel": row.get("channel"),
    }

    # Use last_message_at as escalation time if available
    last_msg_at = row.get("last_message_at")
    if last_msg_at:
        enriched["escalated_at"] = last_msg_at
        try:
            # Calculate wait time in seconds
            if isinstance(last_msg_at, str):
                escalated_dt = datetime.fromisoformat(last_msg_at.replace("Z", "+00:00"))
            else:
                escalated_dt = last_msg_at
            delta = datetime.now(timezone.utc) - escalated_dt
            enriched["wait_time_seconds"] = int(delta.total_seconds())
        except (ValueError, TypeError):
            enriched["wait_time_seconds"] = None
    else:
        enriched["escalated_at"] = None
        enriched["wait_time_seconds"] = None

    enriched["reason"] = row.get("escalation_reason")
    enriched["last_message"] = row.get("last_message_preview")
    return enriched


@router.get("/escalations")
async def list_escalations(
    agent_id: str = Query(..., description="UUID of the agent to filter by"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """List escalated conversations for an agent.

    Returns conversations with status='escalated', indicating they
    are waiting for supervisor input. Each escalation includes the
    reason, wait time, and last message preview.
    """
    try:
        uuid.UUID(agent_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid agent_id format")

    rows, total = await conversation_service.list_conversations(
        agent_id=agent_id, page=page, limit=limit, status_filter="escalated",
    )

    # Enrich each escalation with reason, wait time, and last message
    escalations = []
    for row in rows:
        conv_id = row.get("id")
        enriched = _enrich_escalation(row)

        # Fetch escalation reason from graph state (if available)
        reason = await graph_service.get_escalation_reason(session_id=str(conv_id))
        if reason:
            enriched["reason"] = reason

        # Fetch last message preview if not already in row
        if not enriched.get("last_message") and conv_id:
            last_msg = await conversation_service.get_last_message(str(conv_id))
            if last_msg:
                content = last_msg.get("content", "")
                enriched["last_message"] = content[:100] if content else None

        escalations.append(enriched)

    return {"escalations": escalations, "total": total, "page": page, "limit": limit}


@router.post("/escalations/{conversation_id}/resume")
async def resume_escalation(conversation_id: str, body: EscalationResumeRequest):
    """Resume an escalated conversation with a supervisor response.

    Injects the supervisor's response into the graph via
    Command(resume=...) and returns the AI's follow-up response.
    """
    try:
        conv_uuid = uuid.UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid conversation_id format")

    # Use the conversation_id as session_id for graph lookup
    session_id = str(conv_uuid)

    result = await graph_service.resume_conversation(
        session_id=session_id, supervisor_response=body.supervisor_response,
    )

    if result.get("status") == "error":
        raise HTTPException(
            status_code=409,
            detail=result.get("message", "Cannot resume conversation"),
        )

    # Update conversation status in Supabase
    if result.get("status") == "active":
        await conversation_service.update_status(str(conv_uuid), "active")

    return {
        "conversation_id": str(conv_uuid),
        "status": result.get("status", "active"),
        "ai_response": result.get("ai_response"),
    }


@router.post("/escalations/{conversation_id}/handoff")
async def handoff_conversation(conversation_id: str):
    """Hand off an escalated conversation to a human agent.

    Transitions the conversation from 'escalated' to 'handed_off'
    status, indicating a human agent is now directly handling it.
    """
    try:
        conv_uuid = uuid.UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid conversation_id format")

    result = await conversation_service.update_status(str(conv_uuid), "handed_off")
    return {"conversation_id": str(conv_uuid), "status": result.get("status", "handed_off")}
