"""Sales agent graph assembly.

Wires together the assistant and tool_executor nodes into a
StateGraph. Compilation with a checkpointer is done separately
by GraphService using compile_with_postgres_async().
"""

from __future__ import annotations

import logging

from langgraph.graph import StateGraph, START

from src.nodes.assistant import assistant_node
from src.nodes.tool_executor import tool_executor_node
from src.state.agent_state import SalesAgentState

logger = logging.getLogger(__name__)


def build_sales_graph() -> StateGraph:
    """Build the sales agent graph (uncompiled).

    Graph structure:
        START → assistant → (tool_calls?) → tools → assistant → ... → END

    Routing is handled inside nodes via Command — no conditional
    edge functions needed.
    """
    builder = StateGraph(SalesAgentState)

    builder.add_node("assistant", assistant_node)
    builder.add_node("tools", tool_executor_node)

    builder.add_edge(START, "assistant")

    return builder


async def compile_with_postgres_async(pool):
    """Compile the graph with AsyncPostgresSaver (async).

    Args:
        pool: AsyncConnectionPool for PostgresSaver. If None, compiles
              with checkpointer=None and logs a warning (degraded mode).

    Returns:
        CompiledStateGraph ready to invoke.
    """
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    builder = build_sales_graph()

    if pool is not None:
        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()
        compiled = builder.compile(checkpointer=checkpointer)
        logger.info("graph_compiled_with_postgres_saver")
    else:
        compiled = builder.compile(checkpointer=None)
        logger.warning("graph_compiled_without_checkpointer_degraded_mode")

    return compiled