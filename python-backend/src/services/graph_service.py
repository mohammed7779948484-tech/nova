"""GraphService — central service for tenant-aware LangGraph invocation.

Manages the lifecycle of the compiled LangGraph with AsyncPostgresSaver
for conversation persistence. All channels call this service instead of
invoking the graph directly.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.runnables import RunnableConfig

logger = logging.getLogger(__name__)


class GraphService:
    """Tenant-aware LangGraph invocation service.

    Handles:
    - Lazy connection pool initialization (PostgreSQL)
    - Lazy graph compilation with AsyncPostgresSaver
    - Graceful degradation when DB is unavailable
    """

    def __init__(self) -> None:
        self._connection_pool: Any = None
        self._graph: Any = None

    async def _get_connection_pool(self) -> Any:
        """Create or return the existing connection pool."""
        if self._connection_pool is not None:
            return self._connection_pool

        from src.config.settings import get_settings
        settings = get_settings()

        database_url = settings.database_url
        if not database_url:
            logger.warning("DATABASE_URL not set, running without PostgresSaver")
            return None

        try:
            from psycopg_pool import AsyncConnectionPool
            self._connection_pool = AsyncConnectionPool(
                database_url,
                open=False,
                max_size=10,
                kwargs={
                    "autocommit": True,
                    "connect_timeout": 5,
                    "prepare_threshold": None,
                },
            )
            await self._connection_pool.open()
            logger.info("connection_pool_created")
            return self._connection_pool
        except Exception:
            logger.exception("connection_pool_creation_failed")
            self._connection_pool = None
            return None

    async def _ensure_graph(self) -> None:
        """Lazily compile the graph with PostgresSaver checkpointer."""
        if self._graph is not None:
            return

        pool = await self._get_connection_pool()

        from src.graphs.sales_graph import compile_with_postgres_async
        self._graph = await compile_with_postgres_async(pool)
        logger.info("graph_service_initialized")

    async def process_message(
        self,
        tenant_slug: str,
        session_id: str,
        message: str,
        channel: str = "web",
    ) -> str:
        """Process a customer message through the LangGraph agent.

        Args:
            tenant_slug: The tenant identifier (e.g. "flower_shop")
            session_id: The conversation thread ID
            message: The customer's message
            channel: The communication channel (web, whatsapp)

        Returns:
            The AI's response text.
        """
        await self._ensure_graph()

        if self._graph is None:
            return "Agent is currently unavailable. Please try again later."

        config: RunnableConfig = {
            "configurable": {
                "thread_id": session_id,
                "tenant_id": tenant_slug,
            }
        }

        from langchain_core.messages import HumanMessage

        input_data: dict[str, Any] = {
            "messages": [HumanMessage(content=message)],
            "channel": channel,
            "channel_user_id": session_id,
        }

        try:
            result = await self._graph.ainvoke(input_data, config=config)
            response = result.get("messages", [])
            if response:
                last_msg = response[-1]
                if hasattr(last_msg, "content"):
                    return last_msg.content
                return str(last_msg)
            return ""
        except Exception:
            logger.exception("graph_invocation_failed")
            return "I encountered an error. Please try again."

    async def shutdown(self) -> None:
        """Close the connection pool on application shutdown."""
        if self._connection_pool is not None:
            await self._connection_pool.close()
            self._connection_pool = None
            logger.info("connection_pool_closed")


graph_service = GraphService()