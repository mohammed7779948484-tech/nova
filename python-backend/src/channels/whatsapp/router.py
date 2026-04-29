"""WhatsApp webhook router."""

import os

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import PlainTextResponse

from src.channels.whatsapp.adapter import WhatsAppAdapter

router = APIRouter()
adapter = WhatsAppAdapter()

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
    payload = await request.json()
    inbound_msg = adapter.parse_webhook(payload)
    
    # Real integration:
    # 1. Start background task to invoke graph using `inbound_msg`.
    # 2. Graph outputs an OutboundMessage.
    # 3. Adapter uses send_reply to send it back.
    
    return {"status": "ok"}
