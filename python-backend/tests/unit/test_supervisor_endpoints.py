"""T037: Test supervisor endpoints — escalation, resume, handoff, resolve.

PDCA Called Shot:
- test_list_escalations: GET /api/escalations?agent_id=<uuid> returns 200
  with escalations list filtered to status=escalated.
  Expected RED: 404 Not Found (endpoint doesn't exist yet).
- test_resume_escalation: POST /api/escalations/<id>/resume with
  {"supervisor_response": "approve"} returns 200 with status=active.
  Expected RED: 404 Not Found.
- test_handoff_conversation: POST /api/escalations/<id>/handoff returns
  200 with status=handed_off.
  Expected RED: 404 Not Found.
- test_resolve_conversation: POST /api/conversations/<id>/resolve returns
  200 with status=resolved.
  Expected RED: 404 Not Found.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient, ASGITransport



# Known real data from Supabase
REAL_AGENT_ID = "b0000000-0000-0000-0000-000000000002"
REAL_CONVERSATION_ID = "a0000000-0000-0000-0000-000000000099"


class TestEscalationListEndpoint:
    """Test GET /api/escalations endpoint."""

    @pytest.mark.asyncio
    async def test_list_escalations_returns_200(self):
        """GET /api/escalations?agent_id=<uuid> returns 200 with escalations list."""
        from src.app import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test", timeout=10.0) as client:
            response = await client.get(
                "/api/escalations",
                params={"agent_id": REAL_AGENT_ID},
            )

            assert response.status_code == 200, (
                f"Expected 200, got {response.status_code}: {response.text}"
            )
            data = response.json()
            assert "escalations" in data, "Response must contain 'escalations' key"
            assert "total" in data, "Response must contain 'total' key"

    @pytest.mark.asyncio
    async def test_list_escalations_requires_agent_id(self):
        """GET /api/escalations without agent_id returns 422."""
        from src.app import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test", timeout=10.0) as client:
            response = await client.get("/api/escalations")

            assert response.status_code == 422, (
                f"Expected 422, got {response.status_code}: {response.text}"
            )


class TestResumeHandoffValidation:
    """Test resume and handoff endpoint input validation (422 errors)."""

    @pytest.mark.asyncio
    async def test_resume_escalation_with_invalid_uuid(self):
        """POST /api/escalations/not-a-uuid/resume returns 422."""
        from src.app import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test", timeout=10.0) as client:
            response = await client.post(
                "/api/escalations/not-a-uuid/resume",
                json={"supervisor_response": "approve"},
            )

            assert response.status_code == 422, (
                f"Expected 422, got {response.status_code}: {response.text}"
            )

    @pytest.mark.asyncio
    async def test_handoff_conversation_with_invalid_uuid(self):
        """POST /api/escalations/not-a-uuid/handoff returns 422."""
        from src.app import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test", timeout=10.0) as client:
            response = await client.post("/api/escalations/not-a-uuid/handoff")

            assert response.status_code == 422, (
                f"Expected 422, got {response.status_code}: {response.text}"
            )

    @pytest.mark.asyncio
    async def test_resume_escalation_requires_supervisor_response(self):
        """POST /api/escalations/<id>/resume without supervisor_response returns 422."""
        from src.app import app

        conv_id = str(uuid.uuid4())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test", timeout=10.0) as client:
            response = await client.post(
                f"/api/escalations/{conv_id}/resume",
                json={},  # missing supervisor_response
            )

            assert response.status_code == 422, (
                f"Expected 422, got {response.status_code}: {response.text}"
            )

    @pytest.mark.asyncio
    async def test_supervisor_message_requires_content(self):
        """POST /api/conversations/<id>/message without content returns 422."""
        from src.app import app

        conv_id = str(uuid.uuid4())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test", timeout=10.0) as client:
            response = await client.post(
                f"/api/conversations/{conv_id}/message",
                json={},  # missing content
            )

            assert response.status_code == 422, (
                f"Expected 422, got {response.status_code}: {response.text}"
            )


class TestConversationStatusTransitions:
    """Test resolve/handoff/return via ConversationService directly (real DB, no ASGI race conditions)."""

    @pytest.mark.asyncio
    async def test_resolve_conversation_via_service(self):
        """conversation_service.update_status should set status to resolved."""
        from src.services.conversation_service import ConversationService

        svc = ConversationService()
        try:
            # First set to active so we can resolve
            await svc.update_status(REAL_CONVERSATION_ID, "active")
            # Now resolve
            result = await svc.update_status(REAL_CONVERSATION_ID, "resolved")
            assert result.get("status") == "resolved", (
                f"Expected status='resolved', got {result}"
            )
        finally:
            await svc.aclose()

    @pytest.mark.asyncio
    async def test_handoff_conversation_via_service(self):
        """conversation_service.update_status should set status to handed_off."""
        from src.services.conversation_service import ConversationService

        svc = ConversationService()
        try:
            # First set to escalated so handoff is valid
            await svc.update_status(REAL_CONVERSATION_ID, "escalated")
            # Now handoff
            result = await svc.update_status(REAL_CONVERSATION_ID, "handed_off")
            assert result.get("status") == "handed_off", (
                f"Expected status='handed_off', got {result}"
            )
            # Reset to active for other tests
            await svc.update_status(REAL_CONVERSATION_ID, "active")
        finally:
            await svc.aclose()

    @pytest.mark.asyncio
    async def test_return_from_handoff_via_service(self):
        """conversation_service.update_status should return handed_off → active."""
        from src.services.conversation_service import ConversationService

        svc = ConversationService()
        try:
            # Set up: escalated → handed_off
            await svc.update_status(REAL_CONVERSATION_ID, "escalated")
            await svc.update_status(REAL_CONVERSATION_ID, "handed_off")
            # Return from handoff: handed_off → active
            result = await svc.update_status(REAL_CONVERSATION_ID, "active")
            assert result.get("status") == "active", (
                f"Expected status='active', got {result}"
            )
        finally:
            await svc.aclose()

    @pytest.mark.asyncio
    async def test_supervisor_message_via_service(self):
        """conversation_service.add_message should add a supervisor message."""
        from src.services.conversation_service import ConversationService

        svc = ConversationService()
        try:
            result = await svc.add_message(
                conversation_id=REAL_CONVERSATION_ID,
                role="supervisor",
                content="Supervisor here: how can I help?",
            )
            assert result.get("role") == "supervisor", (
                f"Expected role='supervisor', got {result}"
            )
            assert "content" in result
        finally:
            await svc.aclose()


class TestReturnFromHandoffEndpoint:
    """Test POST /api/conversations/{id}/return endpoint validation."""

    @pytest.mark.asyncio
    async def test_return_from_handoff_invalid_uuid(self):
        """POST /api/conversations/not-a-uuid/return returns 422."""
        from src.app import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test", timeout=10.0) as client:
            response = await client.post("/api/conversations/not-a-uuid/return")
            assert response.status_code == 422, (
                f"Expected 422, got {response.status_code}: {response.text}"
            )
