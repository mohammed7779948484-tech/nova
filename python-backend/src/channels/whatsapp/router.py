"""WhatsApp webhook router."""

from __future__ import annotations

import structlog
import os

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import PlainTextResponse

from src.channels.whatsapp.adapter import WhatsAppAdapter

router = APIRouter()
adapter = WhatsAppAdapter()
logger = structlog.get_logger(__name__)

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "your_verify_token_here")


@router.get("", response_class=PlainTextResponse)
async def verify_webhook(request: Request):
    """WhatsApp webhook verification."""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge
    raise HTTPException(status_code=403, detail="Forbidden")


@router.post("")
async def receive_webhook(request: Request):
    """Receive messages from WhatsApp."""
    # TODO(US5): Wire to GraphService
    payload = await request.json()
    logger.warning(
        "WhatsApp webhook received but not processed — awaiting Phase 4 integration"
    )
    _inbound_msg = adapter.parse_webhook(payload)

    return {"status": "ok"}
