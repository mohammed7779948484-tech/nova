"""Node: execute tool calls made by the assistant.

Takes the last AI message's tool_calls, runs each tool,
and returns ToolMessage results. Always routes back to assistant.
"""

from __future__ import annotations

from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from src.state.agent_state import SalesAgentState
from src.tools import ALL_TOOLS


# Build a lookup map: tool_name → tool_function
_TOOL_MAP = {t.name: t for t in ALL_TOOLS}


async def tool_executor_node(
    state: SalesAgentState,
    config: RunnableConfig,
) -> Command:
    """Execute all tool calls from the last message, then return to assistant."""
    last_message = state["messages"][-1]
    results: list[ToolMessage] = []

    for call in last_message.tool_calls:
        tool_fn = _TOOL_MAP.get(call["name"])

        if tool_fn is None:
            results.append(
                ToolMessage(
                    content=f"Error: Unknown tool '{call['name']}'",
                    tool_call_id=call["id"],
                )
            )
            continue

        # Invoke the tool with its arguments + config (for tenant context)
        try:
            output = await tool_fn.ainvoke(call["args"], config=config)
        except Exception as e:
            output = f"Error executing {call['name']}: {e}"

        results.append(
            ToolMessage(
                content=str(output),
                tool_call_id=call["id"],
            )
        )

    return Command(
        update={"messages": results},
        goto="assistant",
    )
