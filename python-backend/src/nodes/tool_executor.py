"""Node: execute tool calls made by the assistant.

Takes the last AI message's tool_calls, runs each tool,
and returns ToolMessage results. Always routes back to assistant.

Multiple tool calls execute in parallel using asyncio.gather.
"""

from __future__ import annotations

import asyncio
import structlog

from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from src.state.agent_state import SalesAgentState
from src.tools import ALL_TOOLS

logger = structlog.get_logger(__name__)

# Build a lookup map: tool_name → tool_function
_TOOL_MAP = {t.name: t for t in ALL_TOOLS}


async def _execute_single_tool(call: dict, config: RunnableConfig) -> ToolMessage:
    """Execute a single tool call and return the result ToolMessage."""
    tool_fn = _TOOL_MAP.get(call["name"])

    if tool_fn is None:
        return ToolMessage(
            content=f"Error: Unknown tool '{call['name']}'",
            tool_call_id=call["id"],
        )

    try:
        output = await tool_fn.ainvoke(call["args"], config=config)
    except Exception as e:
        output = f"Error executing {call['name']}: {e}"

    return ToolMessage(
        content=str(output),
        tool_call_id=call["id"],
    )


async def tool_executor_node(
    state: SalesAgentState,
    config: RunnableConfig,
) -> Command:
    """Execute all tool calls from the last message, then return to assistant."""
    last_message = state["messages"][-1]
    tool_calls = last_message.tool_calls

    if len(tool_calls) == 1:
        results = [await _execute_single_tool(tool_calls[0], config)]
    elif len(tool_calls) > 1:
        coros = [_execute_single_tool(tc, config) for tc in tool_calls]
        results = await asyncio.gather(*coros)
    else:
        results = []

    return Command(
        update={"messages": results},
        goto="assistant",
    )
