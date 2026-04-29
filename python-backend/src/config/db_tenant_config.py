"""DB Tenant Config — Supabase DB reader for tenant configuration.

Uses httpx to call the Supabase PostgREST API directly, avoiding the
heavy supabase-py dependency chain.

Usage:
    from src.config.db_tenant_config import DBTenantConfig
    db_config = DBTenantConfig()
    agent = await db_config.get_agent_by_slug(tenant_slug="flower_shop")
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx
import structlog
from dotenv import load_dotenv

from src.config.db_tenant_config_helpers import (
    agent_config_to_tenant_config,
    build_agent_config,
)

# Ensure .env is loaded before reading env vars
load_dotenv()

logger = structlog.get_logger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")


@dataclass
class DBAgentConfig:
    """Agent configuration loaded from Supabase."""

    agent_id: str
    tenant_id: str
    tenant_slug: str
    business_name: str
    language: str
    name: str
    role: str
    personality: str
    rules: list[str] = field(default_factory=list)
    llm_provider: str = "openai"
    llm_model: str = "LongCat-Flash-Chat"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 1024
    image_search: bool = True
    promotions: bool = True
    upsell: bool = True
    products: list[dict[str, Any]] = field(default_factory=list)
    instructions: list[str] = field(default_factory=list)


class DBTenantConfig:
    """Load agent configuration from Supabase database.

    Uses the Supabase PostgREST API directly via httpx, avoiding
    the heavy supabase-py dependency chain.

    The httpx.AsyncClient is created on first use and should be
    closed via ``aclose()`` when the application shuts down.
    For FastAPI apps, use the lifespan pattern to manage the lifecycle.

    Replaces the YAML-based tenant loading system with database queries.
    Maintains the same interface as get_tenant() but reads from PostgreSQL.
    """

    def __init__(self):
        if not SUPABASE_URL:
            raise ValueError(
                "SUPABASE_URL is not set. Please add it to your .env file."
            )
        if not SUPABASE_SERVICE_KEY:
            raise ValueError(
                "SUPABASE_SERVICE_KEY is not set. Please add it to your .env file."
            )

        self.base_url = SUPABASE_URL.rstrip("/")
        self.headers = {
            "apikey": SUPABASE_SERVICE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
        self.client = httpx.AsyncClient(
            base_url=f"{self.base_url}/rest/v1",
            headers=self.headers,
            timeout=30.0,
        )
        logger.info("db_tenant_config_initialized", base_url=self.base_url)

    async def aclose(self) -> None:
        """Close the underlying httpx.AsyncClient.

        Call this during application shutdown (e.g. FastAPI lifespan).
        """
        await self.client.aclose()
        logger.info("DBTenantConfig — httpx.AsyncClient closed")

    async def _query_table(
        self, table: str, filters: dict[str, str], select: str = "*"
    ) -> list[dict[str, Any]]:
        """Query a Supabase table with filters via PostgREST API.

        Args:
            table: Table name (e.g. 'agents', 'agent_products').
            filters: Dict of column=value filters.
            select: Columns to select (default '*').

        Returns:
            List of matching rows as dicts.
        """
        params = {"select": select}
        for col, val in filters.items():
            params[col] = f"eq.{val}"

        response = await self.client.get(f"/{table}", params=params)
        response.raise_for_status()
        return response.json()

    async def _query_single(
        self, table: str, filters: dict[str, str], select: str = "*"
    ) -> Optional[dict[str, Any]]:
        """Query a single row from a Supabase table.

        Args:
            table: Table name.
            filters: Dict of column=value filters.
            select: Columns to select.

        Returns:
            Single row dict or None if not found.
        """
        results = await self._query_table(table, filters, select)
        return results[0] if results else None

    async def get_agent_config(self, agent_id: str) -> DBAgentConfig:
        """Load agent config from Supabase by agent_id.

        Args:
            agent_id: UUID of the agent to load.

        Returns:
            DBAgentConfig with all fields populated from the database.

        Raises:
            ValueError: If agent not found or inactive.
        """
        agent = await self._query_single(
            "agents", {"id": agent_id, "is_active": "true"}
        )

        if not agent:
            raise ValueError(f"Agent not found or inactive: {agent_id}")

        products = await self._query_table(
            "agent_products", {"agent_id": agent_id, "is_available": "true"}
        )

        instructions = await self._query_table(
            "agent_instructions",
            {"agent_id": agent_id, "is_active": "true"},
            select="instruction",
        )

        kwargs = build_agent_config(agent, products, instructions)
        return DBAgentConfig(**kwargs)

    async def get_agent_by_slug(self, tenant_slug: str) -> Optional[DBAgentConfig]:
        """Find an agent by its tenant slug (e.g. 'flower_shop').

        Args:
            tenant_slug: The tenant slug (e.g. 'flower_shop').

        Returns:
            DBAgentConfig if found, None otherwise.
        """
        result = await self._query_single(
            "agents",
            {"tenant_slug": tenant_slug, "is_active": "true"},
            select="id",
        )

        if result:
            return await self.get_agent_config(result["id"])
        return None

    async def get_agent_by_whatsapp_phone(
        self, phone_number_id: str
    ) -> Optional[DBAgentConfig]:
        """Find which agent owns this WhatsApp phone number.

        Args:
            phone_number_id: The WhatsApp phone number ID.

        Returns:
            DBAgentConfig if found, None otherwise.
        """
        result = await self._query_single(
            "whatsapp_connections",
            {"phone_number_id": phone_number_id, "is_active": "true"},
            select="agent_id",
        )

        if result:
            return await self.get_agent_config(result["agent_id"])
        return None

    async def list_all_agents(self) -> list[dict[str, Any]]:
        """List all active agents with their tenant info.

        Returns:
            List of agent row dicts from the agents table.
        """
        agents = await self._query_table("agents", {"is_active": "true"})
        logger.debug("listed_active_agents", count=len(agents))
        return agents

    def agent_config_to_tenant_config(self, config: DBAgentConfig) -> dict:
        """Convert DBAgentConfig to the dict format expected by TenantConfig.

        Delegates to the helper function in db_tenant_config_helpers.

        Args:
            config: DBAgentConfig loaded from database.

        Returns:
            Dict matching TenantConfig Pydantic model structure.
        """
        return agent_config_to_tenant_config(config)
