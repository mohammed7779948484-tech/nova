"""GraphService — central service for tenant-aware LangGraph invocation.

Manages the compiled LangGraph with AsyncPostgresSaver for conversation
persistence. All channels call this service instead of invoking the
graph directly.

Supports:
- process_message(): regular customer message handling
- resume_conversation(): resume interrupted/escalated conversation
  with a supervisor's response via Command(resume=...)
- get_escalation_reason(): extract escalation reason from graph state
"""

from __future__ import annotations

import structlog
from typing import Any

from langchain_core.runnables import RunnableConfig

logger = structlog.get_logger(__name__)


class GraphService:
    """Tenant-aware LangGraph invocation service.

    Handles:
    - Lazy connection pool initialization (PostgreSQL)
    - Lazy graph compilation with AsyncPostgresSaver
    - Graceful degradation when DB is unavailable
    - Resuming interrupted (escalated) conversations
    """

    def __init__(self) -> None:
        self._connection_pool: Any = None
        self._graph: Any = None

    @staticmethod
    def _make_config(session_id: str, tenant_slug: str) -> RunnableConfig:
        """Build a RunnableConfig with thread_id and tenant_id."""
        return {"configurable": {"thread_id": session_id, "tenant_id": tenant_slug}}

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
        """Process a customer message through the LangGraph agent."""
        # Sanitize input before processing
        from src.core.sanitizer import sanitize_input, detect_prompt_injection

        message = sanitize_input(message)
        if detect_prompt_injection(message):
            logger.warning(
                "prompt_injection_detected", session_id=session_id, tenant=tenant_slug
            )

        await self._ensure_graph()
        if self._graph is None:
            return "Agent is currently unavailable. Please try again later."

        config = self._make_config(session_id, tenant_slug)
        from langchain_core.messages import HumanMessage

        input_data: dict[str, Any] = {
            "messages": [HumanMessage(content=message)],
            "channel": channel,
            "channel_user_id": session_id,
        }

        try:
            # Check if the graph is currently interrupted (escalated)
            state = await self._graph.aget_state(config)
            if state.next:
                logger.info(
                    "resuming_interrupted_graph", session_id=session_id, next=state.next
                )
                from langgraph.types import Command

                result = await self._graph.ainvoke(
                    Command(resume=message), config=config
                )
            else:
                result = await self._graph.ainvoke(input_data, config=config)

            # Check if the graph was interrupted during this invocation
            state = await self._graph.aget_state(config)
            if state.next:
                interrupt_value = (
                    state.tasks[0].interrupts[0].value
                    if state.tasks and state.tasks[0].interrupts
                    else "Waiting for supervisor input."
                )
                logger.info("graph_interrupted", session_id=session_id)
                return str(interrupt_value.get("message", str(interrupt_value)))

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

    async def resume_conversation(
        self,
        session_id: str,
        supervisor_response: str,
        tenant_slug: str = "flower_shop",
    ) -> dict[str, Any]:
        """Resume an interrupted/escalated conversation with a supervisor response.

        Uses Command(resume=...) to inject the supervisor's response back
        into the graph, allowing it to continue from the escalation node.
        """
        await self._ensure_graph()
        if self._graph is None:
            return {"status": "error", "message": "Graph service not available"}

        config = self._make_config(session_id, tenant_slug)

        try:
            from langgraph.types import Command
            from langgraph.errors import GraphInterrupt

            # Check that the graph is actually paused
            state = await self._graph.aget_state(config)
            if not state.next:
                return {
                    "status": "error",
                    "message": "Conversation is not in an interrupted state",
                }

            logger.info(
                "resuming_conversation", session_id=session_id, next_nodes=state.next
            )

            # Resume the graph with the supervisor's response
            result = await self._graph.ainvoke(
                Command(resume=supervisor_response), config=config
            )

            # Check if graph was interrupted again after resume
            post_state = await self._graph.aget_state(config)
            if post_state.next:
                return {
                    "status": "escalated",
                    "message": "Conversation still requires supervisor input",
                }

            # Extract AI response from the result
            response = result.get("messages", [])
            ai_response = ""
            if response:
                last_msg = response[-1]
                if hasattr(last_msg, "content"):
                    ai_response = last_msg.content

            return {"status": "active", "ai_response": ai_response}

        except GraphInterrupt:
            logger.info("graph_interrupted_again", session_id=session_id)
            return {
                "status": "escalated",
                "message": "Conversation interrupted again during processing",
            }
        except Exception:
            logger.exception("resume_conversation_failed", session_id=session_id)
            return {"status": "error", "message": "Failed to resume conversation"}

    async def get_graph_state(
        self, session_id: str, tenant_slug: str = "flower_shop"
    ) -> dict[str, Any] | None:
        """Get the current graph state for a conversation."""
        await self._ensure_graph()
        if self._graph is None:
            return None
        config = self._make_config(session_id, tenant_slug)
        try:
            state = await self._graph.aget_state(config)
            return {
                "next": list(state.next) if state.next else [],
                "values": dict(state.values) if state.values else {},
            }
        except Exception:
            logger.exception("get_graph_state_failed", session_id=session_id)
            return None

    async def get_escalation_reason(
        self, session_id: str, tenant_slug: str = "flower_shop"
    ) -> str | None:
        """Extract escalation reason from an interrupted graph's state.

        Returns the reason string (e.g. 'customer_request', 'low_confidence')
        or None if the graph is not interrupted or has no reason.
        """
        await self._ensure_graph()
        if self._graph is None:
            return None
        config = self._make_config(session_id, tenant_slug)
        try:
            state = await self._graph.aget_state(config)
            if state.next and state.tasks and state.tasks[0].interrupts:
                interrupt_value = state.tasks[0].interrupts[0].value
                if isinstance(interrupt_value, dict):
                    return interrupt_value.get("reason")
        except Exception:
            logger.exception("get_escalation_reason_failed", session_id=session_id)
        return None

    async def shutdown(self) -> None:
        """Close the connection pool on application shutdown.

        Handles errors gracefully — always clears the pool reference
        even if close() fails, preventing resource leaks.
        """
        if self._connection_pool is not None:
            try:
                await self._connection_pool.close()
            except Exception:
                logger.warning("connection_pool_close_failed")
            finally:
                self._connection_pool = None
            logger.info("connection_pool_closed")


graph_service = GraphService()
