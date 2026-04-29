"""Instagram webhook router."""

import os

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import PlainTextResponse

from src.channels.instagram.adapter import InstagramAdapter

router = APIRouter()
adapter = InstagramAdapter()

VERIFY_TOKEN = os.getenv("INSTAGRAM_VERIFY_TOKEN", os.getenv("WHATSAPP_VERIFY_TOKEN", "your_verify_token_here"))


@router.get("", response_class=PlainTextResponse)
async def verify_webhook(request: Request):
    """Instagram webhook verification."""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge
    raise HTTPException(status_code=403, detail="Forbidden")


@router.post("")
async def receive_webhook(request: Request):
    payload = await request.json()
    inbound_msg = adapter.parse_webhook(payload)
    
    # Process graph...
    
    return {"status": "ok"}
