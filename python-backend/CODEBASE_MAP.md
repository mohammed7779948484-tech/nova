# Codebase Map — langgraph-sales-agent

## Entry Points

| File | Command | Purpose |
|------|---------|---------|
| `main.py` | `python main.py` | Interactive CLI chat with tenant selector, async graph invocation |
| `graph.py` | `langgraph dev` | LangGraph Studio entry point, exports `graph` variable |
| `src/app.py` | `uvicorn src.app:app --port 3000` | FastAPI server, mounts all channel routers, runs on port 3000 |

## Core Components

- **LangGraph Graph**: `src/graphs/sales_graph.py` — `build_sales_graph()` creates `StateGraph(SalesAgentState)`, nodes `assistant` + `tools`, START→assistant edge, routing via `Command`
- **State Definition**: `src/state/agent_state.py` — `SalesAgentState(TypedDict)` with `messages`, `matched_products`, `product_images`, `channel`, `channel_user_id`
- **Tenant Config (YAML)**: `src/config/tenant_config.py` — `get_tenant(tenant_id)` loads from `tenants/{id}/config.yaml`, Pydantic validation, `@lru_cache(32)`
- **LLM Factory**: `src/config/llm_provider.py` — `create_llm(tenant_config)` returns `ChatOpenAI` or `ChatAnthropic` based on `tenant_config.llm.provider`
- **Global Settings**: `src/config/settings.py` — Pydantic `Settings` model, reads env vars via `python-dotenv`, `@lru_cache(1)`
- **Assistant Node**: `src/nodes/assistant.py` — Builds system prompt from tenant config, binds tools, invokes LLM, routes via `Command`
- **Tool Executor**: `src/nodes/tool_executor.py` — Maps tool names to functions, invokes async, returns `ToolMessage` results
- **Product Repository**: `src/repositories/json_repo.py` — `JsonProductRepository` with RU/EN stemming search, `@lru_cache` on catalog loads

## Channel Adapters

| Channel | Path | Status |
|---------|------|--------|
| **Web (Sales Studio)** | `src/channels/web/router.py` + `index.html` | **Fully functional** — SSE streaming, real graph invocation |
| **WhatsApp** | `src/channels/whatsapp/adapter.py` + `router.py` | Scaffold — parses webhooks, `send_reply` prints to console |
| **Telegram** | `src/channels/telegram/adapter.py` + `router.py` | Scaffold — parses webhooks, not wired to graph |
| **Instagram** | `src/channels/instagram/adapter.py` + `router.py` | Scaffold — parses webhooks, not wired to graph |

## Tools

| Tool | File | Purpose |
|------|------|---------|
| `search_products` | `src/tools/search_products.py` | Tokenized stemmed search via repository |
| `get_promotions` | `src/tools/get_promotions.py` | Returns promoted products |
| `search_by_image` | `src/tools/search_by_image.py` | Keyword-overlap product search by image description |
| `send_product_image` | `src/tools/send_product_image.py` | Returns product image URL and price |

## Data Flow

```
User Message → Channel Adapter (Web/WhatsApp/etc.)
    → POST /api/chat (or CLI input)
    → HumanMessage wrapped with config {tenant_id, thread_id}
    → LangGraph StateGraph:
        START → assistant_node
                   ├─ Build system prompt from tenant config
                   ├─ Create LLM (ChatOpenAI/ChatAnthropic)
                   ├─ Bind ALL_TOOLS
                   ├─ Invoke model
                   └─ If tool_calls → Command(goto="tools")
                      Else → Command(goto="__end__")

               tools_node
                   ├─ Read last AI message's tool_calls
                   ├─ Look up each in _TOOL_MAP
                   ├─ Invoke tool.ainvoke(args, config)
                   │   └─ tools access tenant_id from config
                   │       → get_repository() → JsonProductRepository
                   │       → search/get products from tenants/{id}/products.json
                   └─ Return Command(update=ToolMessages, goto="assistant")

        Loops: assistant → tools → assistant → ... → END
    → Response streamed back (SSE for web, printed for CLI)
```

## Tenant System

### How YAML Config Works

1. `get_tenant(tenant_id)` reads `tenants/{tenant_id}/config.yaml`
2. Parses YAML into Pydantic `TenantConfig` model with fields:
   - `tenant_id`, `business_name`, `language`
   - `agent`: `name`, `role`, `personality` (multiline), `rules` (list)
   - `llm`: `provider` (openai/anthropic), `model`, `temperature`, `max_tokens`
   - `features`: `image_search`, `promotions`, `upsell` (booleans)
3. Products loaded separately from `tenants/{tenant_id}/products.json`
4. Both are `@lru_cache`'d for performance
5. All tenant context flows through `config["configurable"]["tenant_id"]`

### Example Tenants

| Tenant | Language | LLM | Agent Name |
|--------|----------|-----|------------|
| `flower_shop` | Russian (ru) | gpt-4o-mini (openai) | Айгуль |
| `tech_store` | English (en) | gpt-4o-mini (openai) | Alex |

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `langgraph` | >=0.4 | Graph engine (StateGraph, InMemorySaver, Command) |
| `langchain-openai` | >=0.3 | ChatOpenAI LLM provider |
| `langchain-anthropic` | >=0.3 | ChatAnthropic LLM provider |
| `langchain-core` | >=0.3 | Messages, tools, runnable config |
| `python-dotenv` | >=1.0 | Environment variable loading |
| `pydantic` | >=2.0 | Data models and validation |
| `pyyaml` | >=6.0 | YAML config parsing |
| `fastapi` | >=0.115 | Web framework for channel routers |
| `uvicorn` | >=0.30 | ASGI server |

## File Tree

```
langgraph-sales-agent/
├── .env.example
├── .gitignore
├── LICENSE
├── README.md
├── graph.py                    # LangGraph Studio entry point
├── langgraph.json              # LangGraph Studio config
├── main.py                     # CLI chat entry point
├── pyproject.toml              # Project metadata + deps
├── assets/
│   └── architecture.png
├── src/
│   ├── __init__.py
│   ├── app.py                  # FastAPI app factory
│   ├── channels/
│   │   ├── __init__.py
│   │   ├── base.py             # ChannelAdapter Protocol
│   │   ├── instagram/
│   │   │   ├── __init__.py
│   │   │   ├── adapter.py      # Instagram adapter (scaffold)
│   │   │   └── router.py       # Instagram webhook endpoint
│   │   ├── telegram/
│   │   │   ├── __init__.py
│   │   │   ├── adapter.py      # Telegram adapter (scaffold)
│   │   │   └── router.py       # Telegram webhook endpoint
│   │   ├── web/
│   │   │   ├── __init__.py
│   │   │   ├── index.html      # Sales Studio web UI
│   │   │   └── router.py       # Web SSE streaming API
│   │   └── whatsapp/
│   │       ├── __init__.py
│   │       ├── adapter.py      # WhatsApp adapter (scaffold)
│   │       └── router.py       # WhatsApp webhook endpoint
│   ├── config/
│   │   ├── __init__.py
│   │   ├── llm_provider.py     # LLM factory (OpenAI/Anthropic)
│   │   ├── settings.py         # Global settings (env vars)
│   │   └── tenant_config.py    # YAML tenant loader
│   ├── graphs/
│   │   ├── __init__.py
│   │   └── sales_graph.py      # LangGraph graph definition
│   ├── models/
│   │   ├── __init__.py
│   │   ├── catalog.py          # ProductCatalog (unused by tools)
│   │   ├── message.py          # InboundMessage/OutboundMessage
│   │   └── product.py          # Product Pydantic model
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── assistant.py        # LLM assistant node
│   │   └── tool_executor.py    # Tool execution node
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── base.py             # ProductRepository Protocol
│   │   └── json_repo.py        # JSON-based product repository
│   ├── state/
│   │   ├── __init__.py
│   │   └── agent_state.py      # SalesAgentState TypedDict
│   └── tools/
│       ├── __init__.py         # ALL_TOOLS export
│       ├── get_promotions.py
│       ├── search_by_image.py
│       ├── search_products.py
│       └── send_product_image.py
└── tenants/
    ├── flower_shop/
    │   ├── config.yaml         # Russian flower shop tenant config
    │   └── products.json       # 9 products (flowers + accessories)
    └── tech_store/
        ├── config.yaml         # English tech store tenant config
        └── products.json       # 6 products (phones, laptops, etc.)
```