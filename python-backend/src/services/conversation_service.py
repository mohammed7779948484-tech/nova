"""ConversationService — CRUD for conversations and messages via Supabase REST API."""

from __future__ import annotations

import logging
from uuid import UUID

import httpx

logger = logging.getLogger(__name__)


class ConversationService:
    """CRUD operations for conversations and messages via Supabase PostgREST API."""

    def __init__(self) -> None:
        from src.config.settings import get_settings
        settings = get_settings()

        self.base_url = settings.supabase_url.rstrip("/")
        self.headers = {
            "apikey": settings.supabase_service_key,
            "Authorization": f"Bearer {settings.supabase_service_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=f"{self.base_url}/rest/v1",
                headers=self.headers,
                timeout=30.0,
            )
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _query(
        self,
        table: str,
        params: dict[str, str],
        select: str = "*",
    ) -> list[dict]:
        client = await self._get_client()
        params["select"] = select
        response = await client.get(f"/{table}", params=params)
        response.raise_for_status()
        return response.json()

    async def list_conversations(
        self,
        agent_id: str,
        page: int = 1,
        limit: int = 20,
        status_filter: str | None = None,
    ) -> tuple[list[dict], int]:
        """List conversations for an agent with pagination.

        Returns:
            Tuple of (conversations list, total count)
        """
        params: dict[str, str] = {
            "agent_id": f"eq.{agent_id}",
            "order": "last_message_at.desc",
            "offset": str((page - 1) * limit),
            "limit": str(limit),
        }
        if status_filter:
            params["status"] = f"eq.{status_filter}"

        rows = await self._query("conversations", params)

        count_params = {"agent_id": f"eq.{agent_id}"}
        if status_filter:
            count_params["status"] = f"eq.{status_filter}"
        client = await self._get_client()
        count_response = await client.get(
            "/conversations",
            params={**count_params, "select": "id"},
            headers={**self.headers, "Prefer": "count=exact"},
        )
        total = int(count_response.headers.get("content-range", "/").split("/")[-1] or 0)

        return rows, total

    async def get_messages(self, conversation_id: str | UUID) -> list[dict]:
        """Get all messages for a conversation ordered by created_at."""
        params = {
            "conversation_id": f"eq.{conversation_id}",
            "order": "created_at.asc",
        }
        return await self._query("messages", params)

    async def create_conversation(
        self,
        agent_id: str,
        session_id: str,
        channel: str,
        customer_phone: str | None = None,
    ) -> dict:
        """Insert a new conversation record."""
        client = await self._get_client()
        payload = {
            "agent_id": agent_id,
            "session_id": session_id,
            "channel": channel,
            "customer_phone": customer_phone,
            "status": "active",
        }
        response = await client.post("/conversations", json=payload)
        response.raise_for_status()
        result = response.json()
        return result[0] if isinstance(result, list) else result

    async def add_message(
        self,
        conversation_id: str | UUID,
        role: str,
        content: str,
    ) -> dict:
        """Insert a new message into a conversation."""
        client = await self._get_client()
        payload = {
            "conversation_id": str(conversation_id),
            "role": role,
            "content": content,
        }
        response = await client.post("/messages", json=payload)
        response.raise_for_status()
        result = response.json()
        return result[0] if isinstance(result, list) else result

    async def update_status(
        self,
        conversation_id: str | UUID,
        status: str,
    ) -> dict:
        """Update the status of a conversation.

        Returns:
            Updated conversation dict, or {"status": status} if no rows matched.
        """
        client = await self._get_client()
        response = await client.patch(
            "/conversations",
            params={"id": f"eq.{conversation_id}"},
            json={"status": status},
        )
        response.raise_for_status()
        result = response.json()
        if isinstance(result, list) and result:
            return result[0]
        if isinstance(result, dict):
            return result
        # No rows matched — return the intended status
        return {"status": status}

    async def get_last_message(self, conversation_id: str | UUID) -> dict | None:
        """Get the most recent message for a conversation."""
        params = {
            "conversation_id": f"eq.{conversation_id}",
            "order": "created_at.desc",
            "limit": "1",
        }
        rows = await self._query("messages", params)
        return rows[0] if rows else None


conversation_service = ConversationService()