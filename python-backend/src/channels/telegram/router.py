"""Telegram webhook router."""

from fastapi import APIRouter, Request

from src.channels.telegram.adapter import TelegramAdapter

router = APIRouter()
adapter = TelegramAdapter()


@router.post("")
async def receive_webhook(request: Request):
    payload = await request.json()
    inbound_msg = adapter.parse_webhook(payload)
    
    # Process graph...
    
    return {"status": "ok"}
