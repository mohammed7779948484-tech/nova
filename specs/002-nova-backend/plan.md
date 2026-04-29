# Implementation Plan: Nova Backend — Multi-Tenant AI Customer Service Platform

**Branch**: `002-nova-backend` | **Date**: 2026-04-28 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/002-nova-backend/spec.md`

## Summary

Build the complete Python/FastAPI backend for Nova — a multi-tenant AI customer
service SaaS platform. The backend is an **internal AI core service** called by a
Next.js frontend. It orchestrates LangGraph-based AI agents, persists
conversations via PostgresSaver, routes WhatsApp webhooks to tenant-specific
agents, and provides admin endpoints for conversation management and HITL
(human-in-the-loop) workflows.

The implementation starts by stabilizing 7 critical defects in the existing
`python-backend/` codebase (Phase 0), then builds incrementally through
persistence, AI resilience, HITL, WhatsApp integration, rate limiting, structured
logging, and production readiness (Phases 1–7).

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: FastAPI (async), LangGraph + LangChain, Pydantic v2, httpx (async only), structlog, tenacity
**Storage**: Supabase PostgreSQL with Row Level Security (11 existing tables + 4 LangGraph checkpoint tables)
**Testing**: pytest + pytest-asyncio + httpx (TestClient)
**Target Platform**: Linux container (Docker multi-stage build)
**Project Type**: Internal web-service (AI core, not user-facing API)
**Performance Goals**: <10s AI response time, <15s startup, 50 concurrent conversations
**Constraints**: All I/O async, 300-line file limit, no sync HTTP clients, no global mutable state
**Scale/Scope**: Single-tenant-per-owner, multi-tenant isolation via RLS, WhatsApp as primary channel

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Status | Evidence |
|---|-----------|--------|----------|
| I | LangGraph-First Architecture | ✅ PASS | All conversation logic flows through `StateGraph`. PostgresSaver for checkpoints (FR-009). No direct LLM calls bypassing graph (FR-054). |
| II | Multi-Tenant Isolation | ✅ PASS | RLS enforced at DB level (FR-051). Cache keys include tenant_id (FR-007). Logs include tenant_id without PII (FR-045). |
| III | WhatsApp-Primary Channel | ✅ PASS | WhatsApp adapter is first channel (Phase 4). Raw httpx to Cloud API (FR-028–FR-035). Signature verification mandatory (FR-029). |
| IV | Async-Native by Default | ✅ PASS | All I/O is async (FR-004). httpx.AsyncClient only. Sync httpx.Client FORBIDDEN. |
| V | Production Resilience | ✅ PASS | Timeouts on all I/O (FR-017). Retry with backoff (FR-015). Circular LLM fallback (FR-016). Graceful degradation (FR-014, FR-018). |
| VI | Explicit over Implicit | ✅ PASS | Pydantic BaseSettings at startup (FR-047). Explicit router registration in app.py. No auto-discovery. |
| VII | Channel Adapter Pattern | ✅ PASS | Unified interface: `parse_inbound()` / `send_outbound()` (FR-053, FR-035). Core never imports channel modules. |

**Gate Result**: ✅ ALL PASS — proceed to Phase 0.

## Pre-Phase: Codebase Pattern Discovery

### Existing Architectural Patterns Found

1. **Graph Assembly** (`src/graphs/sales_graph.py`): `StateGraph` + node registration + `compile()`. Pattern: builder creates graph, nodes are registered with `add_node()`, edges with conditional routing.

2. **Channel Adapter Layout** (`src/channels/*/`): Each channel has `router.py` (FastAPI router) + `adapter.py` (parse/send logic) + `__init__.py`. Base interface at `src/channels/base.py`.

3. **Tool Registration** (`src/tools/__init__.py`): Central `ALL_TOOLS` list, tools imported individually. Tool executor uses `_TOOL_MAP` dict for O(1) lookup.

4. **Configuration Loading** (`src/config/`): Two parallel systems — `tenant_config.py` (YAML-based, local) and `db_tenant_config.py` (Supabase-based, async). Settings via `pydantic.BaseModel` (not `BaseSettings` — needs fix).

5. **Repository Pattern** (`src/repositories/`): `base.py` defines abstract interface, `db_repo.py` implements via Supabase REST API, `json_repo.py` implements via local JSON files.

6. **Node Pattern** (`src/nodes/`): Each node is an async function taking `(state, config)` and returning `Command(update={...}, goto="...")`.

### Reference Template Patterns to Adopt

1. **PostgresSaver with degradation** (`reference-template/app/core/langgraph/graph.py:77-113`): `AsyncConnectionPool` → `AsyncPostgresSaver` → graceful fallback when pool fails.

2. **LLM circular fallback** (`reference-template/app/services/llm/service.py:237-334`): `_fallback_loop()` with per-model retry + circular index advancement.

3. **Concurrent tool execution** (`reference-template/app/core/langgraph/graph.py:190-196`): `asyncio.gather()` for parallel tool calls.

4. **HITL interrupt/resume** (`reference-template/app/core/langgraph/graph.py:276-314`): `aget_state()` → check `state.next` → `Command(resume=...)`.

5. **Structured logging** (`reference-template/app/core/logging.py`): structlog with JSON processor for production, console for dev.

### Abstractions to Reuse (MUST NOT create new ones)

- `SalesAgentState` (TypedDict) → extend, don't replace
- `ChannelAdapter` base class → standardize `parse_inbound` / `send_outbound`
- `ALL_TOOLS` registry → extend with new tools
- Node function signature `(state, config) → Command` → all new nodes follow this
- Repository abstract base → extend for new data access patterns

### Integration Touch Points

| Touch Point | File | Modification Needed |
|-------------|------|-------------------|
| Graph creation | `src/graphs/sales_graph.py` | Add PostgresSaver, HITL nodes |
| App lifespan | `src/app.py` | Connection pool init/cleanup, new routers |
| State definition | `src/state/agent_state.py` | Remove dead fields, add lifecycle state |
| Assistant node | `src/nodes/assistant.py` | Fix instruction injection, add context summary |
| Settings | `src/config/settings.py` | Migrate to Pydantic BaseSettings |
| Tool executor | `src/nodes/tool_executor.py` | Add concurrent execution via asyncio.gather |
| WhatsApp router | `src/channels/whatsapp/router.py` | Wire to GraphService instead of dead-end |
| DB repository | `src/repositories/db_repo.py` | Convert to httpx.AsyncClient |

## Project Structure

### Documentation (this feature)

```text
specs/002-nova-backend/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── api-contracts.md # REST API endpoint contracts
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
python-backend/
├── main.py                          # Uvicorn entry point
├── pyproject.toml                   # Dependencies & tooling config
├── Dockerfile                       # Multi-stage production build
├── database/                        # SQL schema reference (11 tables)
│   ├── 00_shared_functions.sql
│   ├── 01_tenants.sql
│   ├── 02_agents.sql
│   ├── 03_agent_products.sql
│   ├── 04_agent_instructions.sql
│   ├── 05_whatsapp_connections.sql
│   ├── 06_conversations.sql
│   ├── 07_messages.sql
│   ├── 08_invitations.sql
│   ├── 09_subscriptions.sql
│   ├── 10_knowledge_files.sql
│   └── 11_checkpoints.sql
├── src/
│   ├── __init__.py
│   ├── app.py                       # FastAPI app, lifespan, router mounts
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py              # Pydantic BaseSettings (env validation)
│   │   ├── tenant_config.py         # Tenant config loader (DB + cache)
│   │   └── llm_provider.py          # LLM provider factory
│   ├── services/
│   │   ├── __init__.py
│   │   ├── graph_service.py         # Tenant-aware graph invocation
│   │   ├── llm_service.py           # Circular fallback + retry
│   │   ├── conversation_service.py  # CRUD for conversations/messages
│   │   └── whatsapp_service.py      # WhatsApp Cloud API client
│   ├── channels/
│   │   ├── __init__.py
│   │   ├── base.py                  # ChannelAdapter abstract interface
│   │   ├── whatsapp/
│   │   │   ├── __init__.py
│   │   │   ├── adapter.py           # WhatsApp adapter implementation
│   │   │   └── router.py            # Webhook endpoints
│   │   └── web/
│   │       ├── __init__.py
│   │       └── router.py            # Web chat endpoints
│   ├── graphs/
│   │   ├── __init__.py
│   │   └── sales_graph.py           # StateGraph assembly with HITL
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── assistant.py             # AI chat node with context injection
│   │   ├── tool_executor.py         # Concurrent tool execution
│   │   └── escalation.py            # HITL escalation node
│   ├── state/
│   │   ├── __init__.py
│   │   └── agent_state.py           # SalesAgentState TypedDict
│   ├── models/
│   │   ├── __init__.py
│   │   ├── schemas.py               # Pydantic v2 request/response models
│   │   └── enums.py                 # ConversationStatus, EscalationReason
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── base.py                  # Abstract repository interface
│   │   └── db_repo.py               # Supabase REST async repository
│   ├── tools/
│   │   ├── __init__.py              # ALL_TOOLS registry
│   │   ├── search_products.py
│   │   ├── get_promotions.py
│   │   └── search_by_image.py
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── correlation.py           # Request correlation ID
│   │   ├── rate_limiter.py          # Per-IP + per-tenant rate limiting
│   │   └── sanitizer.py             # Input sanitization
│   └── logging/
│       ├── __init__.py
│       └── config.py                # structlog configuration
└── tests/
    ├── conftest.py                  # Shared fixtures
    ├── unit/
    ├── integration/
    └── contract/
```

**Structure Decision**: Single Python backend project. The `src/services/` layer
is new — it sits between routers and repositories, encapsulating business logic
that currently lives scattered across nodes and routers. The `src/middleware/` and
`src/logging/` packages are new for Phases 5–6. Telegram and Instagram adapters
are removed (out of scope per spec).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| `services/` layer added | Graph invocation requires tenant resolution, config loading, and connection pool management in one place | Putting this in routers would violate 300-line limit and duplicate logic across channels |
| `middleware/` package | Rate limiting, correlation IDs, and sanitization are cross-cutting concerns | Inline in routers would mean duplicated code across every endpoint |
