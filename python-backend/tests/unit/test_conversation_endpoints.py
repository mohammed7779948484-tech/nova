"""T022: Test conversation endpoints with real Supabase.

Tests the ConversationService directly against the live Supabase instance,
and the admin router endpoints via ASGITransport for validation tests.

Known real data:
- Agent ID: b0000000-0000-0000-0000-000000000002 (tech_store)
- Conversation ID: a0000000-0000-0000-0000-000000000099 (belongs to tech_store)
"""

import uuid

import pytest
from httpx import AsyncClient, ASGITransport
from src.services.conversation_service import ConversationService

REAL_AGENT_ID = "b0000000-0000-0000-0000-000000000002"
REAL_CONVERSATION_ID = "a0000000-0000-0000-0000-000000000099"


class TestConversationServiceReal:
    """Test ConversationService against real Supabase database."""

    @pytest.mark.asyncio
    async def test_list_conversations_real_data(self):
        """list_conversations should return real data from Supabase."""
        svc = ConversationService()
        try:
            rows, total = await svc.list_conversations(
                agent_id=REAL_AGENT_ID,
                page=1,
                limit=10,
            )

            assert isinstance(rows, list)
            assert isinstance(total, int)
            assert total >= 1, "Should have at least 1 real conversation"
            assert len(rows) >= 1

            first = rows[0]
            assert "id" in first
            assert "agent_id" in first
            assert first["agent_id"] == REAL_AGENT_ID
        finally:
            await svc.aclose()

    @pytest.mark.asyncio
    async def test_list_conversations_empty_for_unknown_agent(self):
        """list_conversations with unknown agent_id returns empty list."""
        svc = ConversationService()
        try:
            rows, total = await svc.list_conversations(
                agent_id=str(uuid.uuid4()),
                page=1,
                limit=10,
            )

            assert rows == []
            assert total == 0
        finally:
            await svc.aclose()

    @pytest.mark.asyncio
    async def test_list_conversations_pagination(self):
        """Pagination params should work correctly."""
        svc = ConversationService()
        try:
            rows, total = await svc.list_conversations(
                agent_id=REAL_AGENT_ID,
                page=1,
                limit=1,
            )

            assert len(rows) <= 1
        finally:
            await svc.aclose()

    @pytest.mark.asyncio
    async def test_get_messages_real_data(self):
        """get_messages should return real messages from Supabase."""
        svc = ConversationService()
        try:
            messages = await svc.get_messages(REAL_CONVERSATION_ID)

            assert isinstance(messages, list)
            assert len(messages) >= 2, (
                "Should have at least 2 real messages in this conversation"
            )

            for msg in messages:
                assert "id" in msg
                assert "role" in msg
                assert "content" in msg
        finally:
            await svc.aclose()

    @pytest.mark.asyncio
    async def test_get_messages_empty_for_unknown_conversation(self):
        """get_messages with unknown conversation_id returns empty list."""
        svc = ConversationService()
        try:
            messages = await svc.get_messages(str(uuid.uuid4()))
            assert messages == []
        finally:
            await svc.aclose()


class TestConversationEndpoints:
    """Test endpoint validation (422 errors) via ASGI transport."""

    @pytest.mark.asyncio
    async def test_list_conversations_requires_agent_id(self):
        """GET /api/conversations without agent_id should return 422."""
        from src.app import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/conversations", timeout=5.0)

            assert response.status_code == 422, (
                f"Expected 422, got {response.status_code}: {response.text}"
            )

    @pytest.mark.asyncio
    async def test_get_conversation_messages_invalid_uuid(self):
        """GET /api/conversations/not-a-uuid/messages returns 422."""
        from src.app import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/conversations/not-a-uuid/messages",
                timeout=5.0,
            )

            assert response.status_code == 422
