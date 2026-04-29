"""Node: escalation — pauses graph via interrupt() for supervisor input.

When the AI determines it cannot handle a conversation (low confidence,
customer request, complex issue), this node calls interrupt() which
pauses graph execution. The graph stores state in the checkpointer
and waits for a supervisor to resume via Command(resume=...).

📎 LangGraph: interrupt() + Command(resume=...) pattern
   — Ref: reference-template/app/core/langgraph/graph.py:276-314
"""

from __future__ import annotations

import structlog
from typing import Literal

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command, interrupt

from src.state.agent_state import SalesAgentState

logger = structlog.get_logger(__name__)


async def escalation_node(
    state: SalesAgentState,
    config: RunnableConfig,
) -> Command[Literal["assistant"]]:
    """Escalation node that interrupts graph execution for supervisor input.

    Calls interrupt() with escalation reason and a human-readable message.
    When the supervisor resumes, the response is injected back into the
    conversation and the graph continues to the assistant node.

    Args:
        state: Current graph state.
        config: Runnable config with tenant_id and thread_id.

    Returns:
        Command that updates messages with the supervisor response and
        routes back to the assistant node.
    """
    reason = state.get("escalation_reason", "customer_request")

    # interrupt() pauses the graph. The returned value is whatever
    # the supervisor passes when resuming via Command(resume=value).
    supervisor_response = interrupt(
        {
            "reason": reason,
            "message": "Waiting for supervisor input",
        }
    )

    logger.info(
        "escalation_resumed",
        reason=reason,
        supervisor_response_len=len(supervisor_response) if supervisor_response else 0,
    )

    # Inject the supervisor's response as an AI message so the
    # assistant node sees it as context and continues the conversation.
    return Command(
        update={
            "messages": [
                AIMessage(
                    content=f"[Supervisor]: {supervisor_response}",
                    name="supervisor",
                )
            ]
        },
        goto="assistant",
    )
