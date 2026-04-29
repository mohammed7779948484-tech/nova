"""CLI chat interface for local testing.

Run with: python main.py

Supports:
  - Text messages
  - Image URLs: prefix with [image] e.g. "[image] https://example.com/photo.jpg"
  - /quit to exit
  - /switch to change tenant
  - /promos to show current promotions
"""

from __future__ import annotations

import asyncio
import uuid

from langchain_core.messages import HumanMessage

from src.config.tenant_config import get_tenant, list_tenants
from src.graphs.sales_graph import compile_sales_graph


def _select_tenant() -> str:
    """Interactive tenant selection."""
    tenants = list_tenants()
    if not tenants:
        print("❌ No tenants found in ./tenants/ directory.")
        print("   Create a tenant folder with config.yaml and products.json")
        raise SystemExit(1)

    print("\n🏪 Available tenants:")
    for i, t in enumerate(tenants, 1):
        tc = get_tenant(t)
        print(f"   {i}. {t} — {tc.business_name} (agent: {tc.agent.name})")

    while True:
        choice = input(f"\nSelect tenant (1-{len(tenants)}): ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(tenants):
                return tenants[idx]
        except ValueError:
            # Try by name
            if choice in tenants:
                return choice
        print("Invalid choice. Try again.")


async def chat_loop() -> None:
    """Main chat loop."""
    tenant_id = _select_tenant()
    tc = get_tenant(tenant_id)
    thread_id = f"{tenant_id}:{uuid.uuid4().hex[:8]}"

    graph = compile_sales_graph()
    config = {
        "configurable": {
            "thread_id": thread_id,
            "tenant_id": tenant_id,
        }
    }

    print(f"\n{'='*50}")
    print(f"💬 Connected to {tc.business_name}")
    print(f"   Agent: {tc.agent.name} ({tc.agent.role})")
    print(f"   Thread: {thread_id}")
    print(f"{'='*50}")
    print("Type your message. Commands: /quit, /switch, /promos\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 Goodbye!")
            break

        if not user_input:
            continue

        # Commands
        if user_input.lower() == "/quit":
            print("👋 Goodbye!")
            break

        if user_input.lower() == "/switch":
            tenant_id = _select_tenant()
            tc = get_tenant(tenant_id)
            thread_id = f"{tenant_id}:{uuid.uuid4().hex[:8]}"
            config = {
                "configurable": {
                    "thread_id": thread_id,
                    "tenant_id": tenant_id,
                }
            }
            graph = compile_sales_graph()
            print(f"\n✅ Switched to {tc.business_name} (agent: {tc.agent.name})\n")
            continue

        if user_input.lower() == "/promos":
            user_input = "Show me your current promotions and special offers"

        # Handle image URLs
        if user_input.lower().startswith("[image]"):
            image_url = user_input[7:].strip()
            message = HumanMessage(
                content=[
                    {"type": "text", "text": "I'm sending you this image. Can you find similar products?"},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ]
            )
        else:
            message = HumanMessage(content=user_input)

        # Invoke graph
        result = await graph.ainvoke(
            {"messages": [message]},
            config=config,
        )

        # Print the last AI message
        ai_message = result["messages"][-1]
        print(f"\n{tc.agent.name}: {ai_message.content}\n")


def main() -> None:
    """Entry point."""
    print("🤖 Enterprise Sales Agent — Multi-Tenant CLI")
    asyncio.run(chat_loop())


if __name__ == "__main__":
    main()
