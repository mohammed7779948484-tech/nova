# Tasks: Nova Backend — Multi-Tenant AI Customer Service Platform

**Input**: Design documents from `specs/002-nova-backend/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Tests are MANDATORY (PDCA TDD enforced). Every implementation task MUST have a corresponding test task written FIRST, verified to FAIL, then implementation follows. See: `.agents/skills/pdca/references/do-prompts.md`

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## PDCA Called Shot Protocol

Every test task MUST include before execution:
- **Test name**: descriptive name
- **Behavior under test**: the observable behavior this verifies
- **Expected failure**: exact assertion message or error expected in RED phase

## Test Sequencing (per PDCA do-prompts.md)

1. Degenerate/zero case first (establishes API)
2. Exception cases (defines valid input contract)
3. Happy path incrementally (simplest → generalize)
4. Remaining exception cases

## Path Conventions

- Source: `python-backend/src/`
- Tests: `python-backend/tests/`
- Database: `python-backend/database/`

## User Stories (from spec.md)

| Story | Title | Priority | Spec Phase |
|-------|-------|----------|------------|
| US1 | Codebase Health Baseline | P1 | Phase 0 |
| US2 | Persistent Conversations | P1 | Phase 1 |
| US3 | AI Resilience & Context | P1 | Phase 2 |
| US4 | Human-in-the-Loop | P1 | Phase 3 |
| US5 | WhatsApp Channel | P1 | Phase 4 |
| US6 | Rate Limiting & Input Safety | P2 | Phase 5 |
| US7 | Structured Logging | P2 | Phase 6 |
| US8 | Production Readiness | P2 | Phase 7 |

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, test infrastructure, and dependency setup

- [X] T001 Create test infrastructure: `python-backend/tests/conftest.py` with shared pytest fixtures (mock Supabase client, fake tenant config, async event loop). Also create `python-backend/tests/__init__.py`, `python-backend/tests/unit/__init__.py`, `python-backend/tests/integration/__init__.py`. Install dev dependencies: `pytest`, `pytest-asyncio`, `httpx` (for TestClient), `pytest-cov`. Reference `python-backend/pyproject.toml` for dependency additions.

- [X] T002 [P] Create Pydantic v2 enums in `python-backend/src/models/enums.py`: `ConversationStatus` (active, escalated, handed_off, resolved), `MessageRole` (customer, assistant, supervisor), `EscalationReason` (customer_request, low_confidence, complex_issue). These are used by all subsequent phases. Reference: `specs/002-nova-backend/data-model.md` § Pydantic Models.

- [X] T003 [P] Create Pydantic v2 request/response schemas in `python-backend/src/models/schemas.py`: `ChatRequest`, `ChatResponse`, `ConversationListResponse`, `ConversationDetailResponse`, `EscalationListResponse`, `EscalationResumeRequest`, `EscalationResumeResponse`, `HandoffRequest`, `SupervisorMessageRequest`, `PaginationParams`. All models use `model_config = ConfigDict(from_attributes=True)`. Reference: `specs/002-nova-backend/contracts/api-contracts.md` for field definitions.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Migrate `python-backend/src/config/settings.py` from `pydantic.BaseModel` to `pydantic_settings.BaseSettings`. Currently (line 16) `class Settings(BaseModel)` reads env vars via `os.getenv()` with `default_factory`. Change to `BaseSettings` with `model_config = SettingsConfigDict(env_file=".env")`. Add new fields: `SUPABASE_URL: str`, `SUPABASE_SERVICE_KEY: str`, `DATABASE_URL: str`, `ENVIRONMENT: str = "development"`, `LOG_FORMAT: str = "console"`, `WHATSAPP_APP_SECRET: str = ""`. Remove `load_dotenv()` call (BaseSettings handles it). Add startup validation: if `SUPABASE_URL` or `SUPABASE_SERVICE_KEY` are empty, raise `ValueError` with clear message. This satisfies FR-047. Max file: ~60 lines.

- [X] T005 Remove dead channel routers from `python-backend/src/app.py`. Currently lines 17-18 import `telegram_router` and `instagram_router`, and lines 82-83 mount them. These channels are out of scope per spec. Delete: `from src.channels.telegram.router import router as telegram_router`, `from src.channels.instagram.router import router as instagram_router`, `app.include_router(telegram_router, ...)`, `app.include_router(instagram_router, ...)`. Optionally delete the `src/channels/telegram/` and `src/channels/instagram/` directories entirely. Update app title from `"Multi-Channel Sales Agent"` to `"Nova Backend"`.

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 — Codebase Health Baseline (Priority: P1) 🎯 MVP

**Goal**: Fix all 7 critical bugs in the existing `python-backend/` codebase. No feature is safe until these defects are resolved.

**Independent Test**: Run linter with zero violations. Send a web chat message and verify tenant-specific instructions appear in the AI response. Confirm 10 concurrent product-search requests complete without event-loop stalls.

### Tests for User Story 1 (MANDATORY — PDCA TDD Enforced) 🚨

> **PDCA Called Shot**: Before each test, announce: test name, behavior under test, expected failure.
> **NOTE**: Write these tests FIRST, verify they FAIL with expected error, THEN implement.

- [X] T006 [P] [US1] Write test for dead state field removal in `python-backend/tests/unit/test_agent_state.py`.
  - **Called Shot**: `test_state_has_no_dead_fields` — verify `SalesAgentState` TypedDict keys are exactly `{"messages", "channel", "channel_user_id"}` and do NOT contain `matched_products` or `product_images`. Expected RED: `AssertionError: 'matched_products' found in state keys` (will fail because fields still exist in `src/state/agent_state.py` lines 27-28).
  - **Called Shot**: `test_state_can_be_instantiated_minimal` — verify state can be created with only `messages=[]`, `channel="web"`, `channel_user_id="test"`. Expected RED: missing required keys error (TypedDict requires all fields including dead ones).

- [X] T007 [P] [US1] Write test for AgentConfig name collision fix in `python-backend/tests/unit/test_config_models.py`.
  - **Called Shot**: `test_agent_config_and_db_agent_config_are_distinct` — import `AgentConfig` from `src/config/tenant_config.py` and `DBAgentConfig` from `src/config/db_tenant_config.py`, verify they are different classes with `assertIsNot`. Expected RED: `ImportError: cannot import name 'DBAgentConfig' from 'src.config.db_tenant_config'` (because the class is still named `AgentConfig` at line 46).
  - **Called Shot**: `test_db_agent_config_has_instructions_field` — verify `DBAgentConfig` dataclass has `instructions: list[str]` field. Expected RED: same ImportError as above.

- [X] T008 [P] [US1] Write test for async DB repository in `python-backend/tests/unit/test_db_repo_async.py`.
  - **Called Shot**: `test_repository_uses_async_client` — import `DBProductRepository` from `src/repositories/db_repo.py`, instantiate with mocked env vars, verify `self.client` is an instance of `httpx.AsyncClient` (not `httpx.Client`). Expected RED: `AssertionError: <httpx.Client> is not an instance of <class 'httpx.AsyncClient'>` (because line 180 creates `httpx.Client`).
  - **Called Shot**: `test_search_is_async` — verify `DBProductRepository.search` is a coroutine function using `inspect.iscoroutinefunction()`. Expected RED: `AssertionError: False is not true` (because `search()` at line 256 is a sync method).

- [X] T009 [P] [US1] Write test for instruction injection in `python-backend/tests/unit/test_system_prompt.py`.
  - **Called Shot**: `test_system_prompt_includes_instructions` — call `_build_system_prompt()` with a `TenantConfig` that has `instructions=["Always greet in Arabic", "Never discuss competitors"]`, verify the returned prompt string contains both instruction texts. Expected RED: `AssertionError: 'Always greet in Arabic' not found in prompt` (because `_build_system_prompt()` in `src/nodes/assistant.py` lines 27-66 never references `instructions`).
  - First: add `instructions: list[str] = Field(default_factory=list)` to `TenantConfig` model in the test fixture setup. The test verifies `_build_system_prompt` behavior, not the model.

- [X] T010 [P] [US1] Write test for tool naming accuracy in `python-backend/tests/unit/test_tool_names.py`.
  - **Called Shot**: `test_no_tool_named_send_product_image` — import `ALL_TOOLS` from `src/tools/__init__.py`, verify no tool has `name == "send_product_image"`. Expected RED: `AssertionError: 'send_product_image' found in tool names` (because the tool still exists at `src/tools/send_product_image.py`).
  - **Called Shot**: `test_get_product_details_tool_exists` — verify a tool named `get_product_details` exists in `ALL_TOOLS`. Expected RED: `AssertionError: 'get_product_details' not found in tool names`.

- [X] T011 [P] [US1] Write test for tenant config caching in `python-backend/tests/unit/test_tenant_cache.py`.
  - **Called Shot**: `test_async_get_tenant_caches_result` — call `async_get_tenant("flower_shop")` twice with a mocked DB backend, verify the DB is called only once (second call returns cached). Expected RED: `AssertionError: 2 != 1` (because `async_get_tenant()` at line 130 calls DB every time with no caching).
  - Mock only at infrastructure boundary: mock the `httpx.AsyncClient.get` method, not internal functions.

### Implementation for User Story 1

- [X] T012 [P] [US1] **Bug 6: Remove dead state fields** in `python-backend/src/state/agent_state.py`. Delete lines 27-28 (`matched_products: list[dict]` and `product_images: list[str]`). The resulting `SalesAgentState` TypedDict should have exactly 3 fields: `messages`, `channel`, `channel_user_id`. File goes from 31 lines → ~25 lines. Verify T006 tests pass GREEN.

- [X] T013 [P] [US1] **Bug 5: Fix AgentConfig name collision**. In `python-backend/src/config/db_tenant_config.py`, rename `class AgentConfig` (line 46) to `class DBAgentConfig`. Update all references within the same file: line 154 return type, line 196 return statement, line 217 return type, line 241 return type, line 275 parameter type. Also update `python-backend/src/config/tenant_config.py` line 141 and 144 where `agent_cfg` type is used — change `AgentConfig` references to use the new name via import. Verify T007 tests pass GREEN.

- [X] T014 [US1] **Bug 4: Convert sync httpx to async** in `python-backend/src/repositories/db_repo.py`. This is the largest Phase 0 fix. Changes required:
  1. Line 180: Change `self.client = httpx.Client(...)` → `self.client = httpx.AsyncClient(...)` 
  2. Line 191: Change `def close()` → `async def aclose()` and call `await self.client.aclose()`
  3. Line 199-209: Change `def _query_table()` → `async def _query_table()`, change `self.client.get()` → `await self.client.get()`
  4. Line 211-227: Change `def _get_agent_id()` → `async def _get_agent_id()`, add `await` to `_query_table` call
  5. Line 229-244: Change `def _load_products()` → `async def _load_products()`, add `await` to calls
  6. Line 246-254: Change `def _get_catalog()` → `async def _get_catalog()`, add `await` to `_load_products`
  7. Lines 256, 273, 280, 284: Change `def search/get_by_id/get_promotions/find_similar` → `async def`, add `await` to `_get_catalog`
  8. Update `python-backend/src/app.py` line 54-55: Change `_db_repo.close()` → `await _db_repo.aclose()`
  9. Update `python-backend/src/tools/search_products.py`, `get_promotions.py`, `search_by_image.py` — ensure they `await` the now-async repository methods.
  File stays at ~329 lines (at limit — consider splitting `_stem`/`_tokenize` helpers into `python-backend/src/repositories/text_utils.py` if it exceeds 300). Verify T008 tests pass GREEN.

- [X] T015 [US1] **Bug 3: Inject instructions into system prompt** in `python-backend/src/nodes/assistant.py`. Two changes:
  1. Add `instructions: list[str] = Field(default_factory=list)` to `TenantConfig` in `python-backend/src/config/tenant_config.py` (around line 60, inside the class).
  2. In `python-backend/src/nodes/assistant.py` function `_build_system_prompt()` (line 27-66), add after the language section (line 66): `if tc.instructions:` followed by `instructions_block = "\n## Custom Instructions\n" + "\n".join(f"- {i}" for i in tc.instructions)` and append to the return string.
  3. In `python-backend/src/config/tenant_config.py` function `async_get_tenant()` (line 130), when building the TenantConfig from DB data (line 144-145), pass `instructions` from the `agent_cfg.instructions` field into the dict.
  Verify T009 tests pass GREEN.

- [X] T016 [P] [US1] **Bug 2: Rename misleading tool** `python-backend/src/tools/send_product_image.py` → rename file to `python-backend/src/tools/get_product_details.py`. Inside the file:
  1. Change `@tool` decorator function name from `send_product_image` to `get_product_details` (line 12)
  2. Update docstring to: `"Get product details including name, price, and image URL."`
  3. Update `python-backend/src/tools/__init__.py`: change import from `from src.tools.send_product_image import send_product_image` to `from src.tools.get_product_details import get_product_details`. Update `ALL_TOOLS` list and `__all__` list.
  Verify T010 tests pass GREEN.

- [X] T017 [US1] **Bug 7: Add tenant config caching** to `python-backend/src/config/tenant_config.py`. Add a TTL cache for `async_get_tenant()`:
  1. Add `import time` at top.
  2. Add module-level `_tenant_cache: dict[str, tuple[TenantConfig, float]] = {}` and `_TENANT_CACHE_TTL = 300` (5 min).
  3. In `async_get_tenant()` (line 130), before the DB call: check if `tenant_id` is in `_tenant_cache` and the timestamp hasn't expired. If valid cache hit, return cached value. After successful DB load, store in `_tenant_cache[tenant_id] = (config, time.monotonic() + _TENANT_CACHE_TTL)`.
  4. Add `def invalidate_tenant_cache(tenant_id: str | None = None)` to clear one or all entries.
  Verify T011 tests pass GREEN.

- [X] T018 [US1] **Bug 1: Verify WhatsApp router is dead-end** — This is documented but NOT fixed in Phase 0. The WhatsApp router fix is Phase 4 (US5). For now, add a `# TODO(US5): Wire to GraphService` comment in `python-backend/src/channels/whatsapp/router.py` line 34 and add a `logger.warning("WhatsApp webhook received but not processed — awaiting Phase 4 integration")` so the dead-end is logged, not silent. File: ~45 lines.

- [X] T019 [US1] Run linter (`ruff check python-backend/src/`) and verify zero violations. Fix any issues found. Run all Phase 0 tests: `pytest python-backend/tests/unit/ -v`. All must pass GREEN.

**Checkpoint**: Codebase stabilized. All 7 bugs addressed. Linter clean. Ready for feature work.
## Phase 4: User Story 2 — Persistent Conversations (Priority: P1)

**Goal**: All conversation state persisted to PostgreSQL via LangGraph's AsyncPostgresSaver. Conversations survive server restarts. Admin endpoints for listing/viewing conversations.

**Independent Test**: Send 3 messages via web chat, restart server, send 4th message — agent references info from first 3.

📎 **LangGraph: AsyncPostgresSaver + AsyncConnectionPool lifecycle** — Ref: `reference-template/app/core/langgraph/graph.py:77-113, 198-241`

### Tests for User Story 2 (MANDATORY — PDCA TDD Enforced) 🚨

- [ ] T020 [P] [US2] Write test for PostgresSaver graph compilation in `python-backend/tests/unit/test_graph_compilation.py`.
  - **Called Shot**: `test_graph_compiles_with_checkpointer` — call `build_sales_graph()`, verify it returns a `StateGraph` instance. Then call a new `async compile_with_postgres(pool)` function, verify it returns a `CompiledStateGraph` with a non-None checkpointer. Expected RED: `AttributeError: module 'src.graphs.sales_graph' has no attribute 'compile_with_postgres'` (function doesn't exist yet — currently only `compile_sales_graph()` with InMemorySaver at line 44-55).
  - **Called Shot**: `test_graph_compiles_without_checkpointer_in_degraded_mode` — when connection pool is None, graph compiles with `checkpointer=None` and logs a warning. Expected RED: same AttributeError.
  - 📎 LangGraph: `StateGraph.compile(checkpointer=AsyncPostgresSaver)` — Ref: `reference-template/app/core/langgraph/graph.py:206-225`

- [ ] T021 [P] [US2] Write test for GraphService in `python-backend/tests/unit/test_graph_service.py`.
  - **Called Shot**: `test_graph_service_invokes_with_tenant_config` — create `GraphService`, call `process_message(tenant_slug="flower_shop", session_id="test-1", message="hello")`, verify it returns a non-empty response string. Expected RED: `ImportError: cannot import name 'GraphService' from 'src.services.graph_service'` (file doesn't exist).
  - **Called Shot**: `test_graph_service_reuses_compiled_graph` — call `process_message` twice, verify the graph is compiled only once (lazy singleton). Expected RED: same ImportError.
  - 📎 LangGraph: `graph.ainvoke(input, config={"configurable": {"thread_id": ..., "tenant_id": ...}})` — Ref: `reference-template/app/core/langgraph/graph.py:276-294`

- [ ] T022 [P] [US2] Write test for conversation list endpoint in `python-backend/tests/unit/test_conversation_endpoints.py`.
  - **Called Shot**: `test_list_conversations_returns_paginated` — `GET /api/conversations?agent_id=<uuid>&page=1&limit=10` returns 200 with `conversations` list, `total`, `page`, `limit` fields. Expected RED: `404 Not Found` (endpoint doesn't exist).
  - **Called Shot**: `test_list_conversations_requires_agent_id` — `GET /api/conversations` without `agent_id` returns 422 validation error. Expected RED: `404 Not Found`.
  - **Called Shot**: `test_get_conversation_messages` — `GET /api/conversations/<uuid>/messages` returns 200 with `conversation_id` and `messages` list. Expected RED: `404 Not Found`.

### Implementation for User Story 2

- [ ] T023 [US2] Create `python-backend/src/services/graph_service.py` (~120 lines). This is the central service that all channels call. Pattern adopted from `reference-template/app/core/langgraph/graph.py:77-241`:
  1. `class GraphService` with `__init__` creating `_connection_pool: AsyncConnectionPool | None = None` and `_graph: CompiledStateGraph | None = None`.
  2. `async def _get_connection_pool()` — lazy init with `psycopg_pool.AsyncConnectionPool` using `DATABASE_URL` from settings. Pool config: `max_size=10`, `open=False`, `kwargs={"autocommit": True, "connect_timeout": 5, "prepare_threshold": None}`. Graceful fallback if pool fails.
  3. `async def _ensure_graph()` — lazy compile: `build_sales_graph().compile(checkpointer=AsyncPostgresSaver(pool))` or `checkpointer=None` in degraded mode.
  4. `async def process_message(tenant_slug, session_id, message, channel="web")` — loads tenant config, invokes graph with `config={"configurable": {"thread_id": session_id, "tenant_id": tenant_slug}}`.
  5. `async def shutdown()` — close pool.
  Module-level singleton: `graph_service = GraphService()`.
  📎 LangGraph: `AsyncPostgresSaver(pool)` + `await checkpointer.setup()` + `builder.compile(checkpointer=checkpointer)`

- [ ] T024 [US2] Refactor `python-backend/src/graphs/sales_graph.py` to support PostgresSaver:
  1. Remove `from langgraph.checkpoint.memory import InMemorySaver` (line 10).
  2. Remove `compile_sales_graph()` function (lines 44-55) — compilation now happens in `GraphService`.
  3. Keep only `build_sales_graph() -> StateGraph` (the uncompiled builder).
  4. File goes from 56 lines → ~42 lines.
  📎 LangGraph: Separate graph building from compilation to allow different checkpointers per environment.

- [ ] T025 [US2] Refactor `python-backend/src/channels/web/router.py` to use `GraphService` instead of inline graph:
  1. Remove lines 15-16 (`from src.graphs.sales_graph import build_sales_graph` and `InMemorySaver` import).
  2. Remove lines 21-22 (module-level `_checkpointer` and `_graph` creation).
  3. In `chat()` endpoint (line 100), replace `_graph.astream_events(...)` with `graph_service.process_message(tenant_slug=tenant_id, session_id=thread_id, message=message, channel="web")`.
  4. Import `from src.services.graph_service import graph_service` at top.
  5. Streaming can be added later — for now return JSON response.

- [ ] T026 [US2] Create `python-backend/src/services/conversation_service.py` (~100 lines). CRUD for conversations/messages via Supabase REST API:
  1. `class ConversationService` with `httpx.AsyncClient` using `SUPABASE_URL` + `SUPABASE_SERVICE_KEY`.
  2. `async def list_conversations(agent_id, page, limit, status_filter)` — query `conversations` table with pagination. Join with messages count via PostgREST `select=*,messages(count)`.
  3. `async def get_messages(conversation_id)` — query `messages` table ordered by `created_at`.
  4. `async def create_conversation(agent_id, session_id, channel, customer_phone)` — insert into `conversations`.
  5. `async def add_message(conversation_id, role, content)` — insert into `messages`.
  6. `async def update_status(conversation_id, status)` — update `conversations.status`.
  Module-level singleton: `conversation_service = ConversationService()`.

- [ ] T027 [US2] Create conversation management endpoints. Add new router `python-backend/src/channels/admin/router.py` (~60 lines):
  1. `GET /api/conversations` — calls `conversation_service.list_conversations()`. Query params: `agent_id` (required), `page`, `limit`, `status`.
  2. `GET /api/conversations/{conversation_id}/messages` — calls `conversation_service.get_messages()`.
  3. Register in `python-backend/src/app.py`: `from src.channels.admin.router import router as admin_router` and `app.include_router(admin_router)`.

- [ ] T028 [US2] Update `python-backend/src/app.py` lifespan for connection pool lifecycle:
  1. In startup: call `await graph_service._ensure_graph()` to pre-warm the connection pool.
  2. In shutdown: call `await graph_service.shutdown()` to close the pool. Replace the old `_db_repo.close()` with `await _db_repo.aclose()` (from T014).
  3. Import `from src.services.graph_service import graph_service`.

- [ ] T029 [US2] Run all US2 tests: `pytest python-backend/tests/unit/test_graph_compilation.py python-backend/tests/unit/test_graph_service.py python-backend/tests/unit/test_conversation_endpoints.py -v`. All must pass GREEN.

**Checkpoint**: Conversations persist via PostgresSaver. Admin can list/view conversations. Server restart preserves history.

---

## Phase 5: User Story 3 — AI Resilience & Context (Priority: P1)

**Goal**: LLM calls have retry + circular fallback. Graceful degradation when all models fail. Tenant-specific context summary injected into AI.

**Independent Test**: Mock primary LLM to fail, verify fallback model responds. Verify customer receives graceful message when all models are down.

📎 **LangGraph: LLM circular fallback with tenacity** — Ref: `reference-template/app/services/llm/service.py:39-334`

### Tests for User Story 3 (MANDATORY — PDCA TDD Enforced) 🚨

- [ ] T030 [P] [US3] Write test for LLM service in `python-backend/tests/unit/test_llm_service.py`.
  - **Called Shot**: `test_llm_service_retries_on_rate_limit` — invoke LLMService with a mock that raises `RateLimitError` twice then succeeds. Verify 3 total calls. Expected RED: `ImportError: cannot import name 'LLMService' from 'src.services.llm_service'` (file doesn't exist).
  - **Called Shot**: `test_llm_service_falls_back_to_next_model` — invoke with mock that always raises `APIError`. Verify it tries all registered models before raising `RuntimeError`. Expected RED: same ImportError.
  - **Called Shot**: `test_llm_service_returns_graceful_message_on_total_failure` — when all models fail, verify the returned message is the graceful fallback text. Expected RED: same ImportError.

- [ ] T031 [P] [US3] Write test for context summary in `python-backend/tests/unit/test_context_summary.py`.
  - **Called Shot**: `test_system_prompt_includes_context_summary` — invoke `_build_system_prompt()` with a TenantConfig that has conversation context (discussed products, customer preferences). Verify the prompt includes context section. Expected RED: `AssertionError: '## Conversation Context' not found in prompt`.

### Implementation for User Story 3

- [ ] T032 [US3] Create `python-backend/src/services/llm_service.py` (~150 lines). Adopt pattern from `reference-template/app/services/llm/service.py:39-334`:
  1. `class LLMService` with `_current_model_index`, `_bound_tools`, and model list from `create_llm()` factory.
  2. `@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), retry=retry_if_exception_type((RateLimitError, APITimeoutError)))` on `_invoke_with_retry()`.
  3. `_switch_to_next_model()` — circular fallback preserving tool bindings.
  4. `_fallback_loop()` — shared loop trying each model.
  5. `async def call(messages, tenant_config)` — orchestrates retry + fallback. Timeout via `asyncio.wait_for(timeout=60)`.
  6. On total failure: return graceful message `"I'm experiencing technical difficulties. Please try again shortly."` (FR-018).
  Add `tenacity` to `python-backend/pyproject.toml` dependencies.

- [ ] T033 [US3] Update `python-backend/src/nodes/assistant.py` to use LLMService instead of direct `create_llm()` call:
  1. Replace line 80 `model = create_llm(tc).bind_tools(ALL_TOOLS)` with: `from src.services.llm_service import llm_service` then `response = await llm_service.call(messages, tc)`.
  2. Wrap the call in try/except to handle graceful fallback message.
  3. Add context summary section to `_build_system_prompt()`: if state has conversation history > 5 messages, add `## Conversation Context\nPrevious topics discussed: {summary}`.

- [ ] T034 [US3] Add parallel tool execution to `python-backend/src/nodes/tool_executor.py`. Adopt pattern from `reference-template/app/core/langgraph/graph.py:190-196`:
  1. Currently lines 29-52 execute tools sequentially in a for loop.
  2. Change to: if `len(tool_calls) == 1`, execute directly. If `> 1`, use `asyncio.gather(*[execute_tool(tc) for tc in tool_calls])`.
  3. Add `import asyncio` at top.
  📎 LangGraph: `asyncio.gather()` for concurrent tool execution within a single node.

- [ ] T035 [US3] Run all US3 tests: `pytest python-backend/tests/unit/test_llm_service.py python-backend/tests/unit/test_context_summary.py -v`. All GREEN.

**Checkpoint**: AI calls are resilient with retry + fallback. Graceful degradation works. Tools execute in parallel.

---

## Phase 6: User Story 4 — Human-in-the-Loop (Priority: P1)

**Goal**: AI can pause conversations and request supervisor input. Supervisor can resume, handoff, or send direct messages. Conversation lifecycle states enforced.

**Independent Test**: Trigger escalation, verify conversation is paused. Submit supervisor response, verify AI resumes with that context.

📎 **LangGraph: interrupt() + Command(resume=...)** — Ref: `reference-template/app/core/langgraph/graph.py:276-314`

### Tests for User Story 4 (MANDATORY — PDCA TDD Enforced) 🚨

- [ ] T036 [P] [US4] Write test for escalation node in `python-backend/tests/unit/test_escalation_node.py`.
  - **Called Shot**: `test_escalation_node_interrupts_graph` — invoke escalation node, verify it calls `interrupt()` with escalation reason. Expected RED: `ImportError: cannot import name 'escalation_node' from 'src.nodes.escalation'` (file doesn't exist).
  - 📎 LangGraph: `from langgraph.types import interrupt` — calling `interrupt(value)` pauses graph execution.

- [ ] T037 [P] [US4] Write test for supervisor endpoints in `python-backend/tests/unit/test_supervisor_endpoints.py`.
  - **Called Shot**: `test_list_escalations` — `GET /api/escalations?agent_id=<uuid>` returns 200 with `escalations` list filtered to `status=escalated`. Expected RED: `404 Not Found`.
  - **Called Shot**: `test_resume_escalation` — `POST /api/escalations/<id>/resume` with `{"supervisor_response": "approve"}` returns 200 with `status=active`. Expected RED: `404 Not Found`.
  - **Called Shot**: `test_handoff_conversation` — `POST /api/escalations/<id>/handoff` returns 200 with `status=handed_off`. Expected RED: `404 Not Found`.
  - **Called Shot**: `test_resolve_conversation` — `POST /api/conversations/<id>/resolve` returns 200 with `status=resolved`. Expected RED: `404 Not Found`.

- [ ] T038 [P] [US4] Write test for lifecycle state transitions in `python-backend/tests/unit/test_lifecycle.py`.
  - **Called Shot**: `test_valid_transitions` — verify all allowed transitions: active→escalated, escalated→active, escalated→handed_off, handed_off→active, active→resolved, escalated→resolved, handed_off→resolved. Expected RED: `ImportError: cannot import name 'validate_transition'`.
  - **Called Shot**: `test_invalid_transitions` — verify disallowed: resolved→active, active→handed_off (must go through escalated). Expected RED: same ImportError.

### Implementation for User Story 4

- [ ] T039 [US4] Create lifecycle state machine in `python-backend/src/models/lifecycle.py` (~50 lines):
  1. Import `ConversationStatus` from `src/models/enums.py`.
  2. Define `VALID_TRANSITIONS: dict[ConversationStatus, set[ConversationStatus]]` mapping each status to its allowed next states per spec: `active→{escalated, resolved}`, `escalated→{active, handed_off, resolved}`, `handed_off→{active, resolved}`, `resolved→set()`.
  3. `def validate_transition(current, target) -> bool` — returns `target in VALID_TRANSITIONS[current]`.
  4. `def transition_or_raise(current, target)` — raises `ValueError` if invalid.

- [ ] T040 [US4] Create escalation node in `python-backend/src/nodes/escalation.py` (~40 lines):
  1. `async def escalation_node(state, config) -> Command` — calls `interrupt({"reason": state.get("escalation_reason", "customer_request"), "message": "Waiting for supervisor input"})`.
  2. Import: `from langgraph.types import interrupt`.
  📎 LangGraph: `interrupt()` pauses graph execution, stores state in checkpoint. Resume via `Command(resume=value)`.

- [ ] T041 [US4] Update graph to include escalation node in `python-backend/src/graphs/sales_graph.py`:
  1. Import `escalation_node` from `src.nodes.escalation`.
  2. Add `builder.add_node("escalate", escalation_node)` after the tools node.
  3. The assistant node will route to "escalate" when it detects escalation triggers (low confidence, customer request).
  📎 LangGraph: `add_node("escalate", escalation_node)` — node that calls `interrupt()`.

- [ ] T042 [US4] Add supervisor endpoints to `python-backend/src/channels/admin/router.py` (extend from T027, keep under 300 lines):
  1. `GET /api/escalations` — calls `conversation_service.list_conversations(status="escalated")`.
  2. `POST /api/escalations/{conversation_id}/resume` — calls `graph_service.resume_conversation(conversation_id, supervisor_response)`. This invokes `graph.ainvoke(Command(resume=response), config)`.
  3. `POST /api/escalations/{conversation_id}/handoff` — updates status to `handed_off`.
  4. `POST /api/conversations/{conversation_id}/message` — supervisor direct message during handoff.
  5. `POST /api/conversations/{conversation_id}/resolve` — updates status to `resolved`.
  📎 LangGraph: `graph.ainvoke(Command(resume=supervisor_response), config={"configurable": {"thread_id": session_id}})` — Ref: `reference-template/app/core/langgraph/graph.py:285-288`

- [ ] T043 [US4] Add `resume_conversation()` method to `python-backend/src/services/graph_service.py`:
  1. `async def resume_conversation(session_id, supervisor_response)` — get graph state via `graph.aget_state(config)`, check `state.next` exists (graph is paused), then `graph.ainvoke(Command(resume=supervisor_response), config)`.
  2. Handle `GraphInterrupt` exception.
  📎 LangGraph: `aget_state()` + `Command(resume=...)` — Ref: `reference-template/app/core/langgraph/graph.py:276-314`

- [ ] T044 [US4] Run all US4 tests: `pytest python-backend/tests/unit/test_escalation_node.py python-backend/tests/unit/test_supervisor_endpoints.py python-backend/tests/unit/test_lifecycle.py -v`. All GREEN.

**Checkpoint**: HITL workflow complete. Escalation pauses AI, supervisor can resume/handoff/resolve. Lifecycle states enforced.
## Phase 7: User Story 5 — WhatsApp Channel (Priority: P1)

**Goal**: WhatsApp webhook receives messages, routes to the correct tenant's AI agent via LangGraph, and sends the AI response back via Cloud API. Signature verification on all inbound webhooks.

**Independent Test**: Send simulated WhatsApp webhook payload, verify AI processes it and `httpx.AsyncClient` calls the Meta send-message API.

📎 **LangGraph: graph.ainvoke() from webhook context** — same pattern as web channel but async background task.

### Tests for User Story 5 (MANDATORY — PDCA TDD Enforced) 🚨

- [ ] T045 [P] [US5] Write test for webhook signature verification in `python-backend/tests/unit/test_whatsapp_security.py`.
  - **Called Shot**: `test_valid_signature_passes` — compute HMAC-SHA256 of a payload with known app secret, set `X-Hub-Signature-256` header, verify the request is accepted (200). Expected RED: `ImportError: cannot import name 'verify_webhook_signature' from 'src.channels.whatsapp.security'`.
  - **Called Shot**: `test_invalid_signature_returns_403` — send request with wrong signature, verify 403. Expected RED: same ImportError.
  - **Called Shot**: `test_missing_signature_returns_403` — send request without header, verify 403. Expected RED: same ImportError.

- [ ] T046 [P] [US5] Write test for WhatsApp adapter tenant resolution in `python-backend/tests/unit/test_whatsapp_adapter.py`.
  - **Called Shot**: `test_parse_webhook_resolves_tenant_from_phone_number_id` — parse a real-shaped WhatsApp webhook payload, verify `InboundMessage.tenant_id` is resolved from `phone_number_id` (not hardcoded "flower_shop"). Expected RED: `AssertionError: 'flower_shop' != '<expected_slug>'` (because line 28 of `src/channels/whatsapp/adapter.py` hardcodes `tenant_id="flower_shop"`).
  - **Called Shot**: `test_send_reply_calls_meta_api` — call `adapter.send_reply()`, verify it makes an HTTP POST to `https://graph.facebook.com/v21.0/{phone_number_id}/messages`. Expected RED: `AssertionError` (current implementation only prints to console at line 39).

- [ ] T047 [P] [US5] Write test for WhatsApp router graph integration in `python-backend/tests/unit/test_whatsapp_integration.py`.
  - **Called Shot**: `test_webhook_invokes_graph_service` — POST a valid webhook payload to `/api/webhooks/whatsapp`, verify `graph_service.process_message()` is called with correct tenant_slug, session_id (from customer phone), and message text. Expected RED: the endpoint currently returns `{"status": "ok"}` without calling graph (lines 34-39 of router).

### Implementation for User Story 5

- [ ] T048 [US5] Create `python-backend/src/channels/whatsapp/security.py` (~40 lines):
  1. `import hashlib, hmac`.
  2. `def verify_webhook_signature(payload_body: bytes, signature_header: str, app_secret: str) -> bool` — compute HMAC-SHA256 of payload with secret, compare with `sha256=...` from header using `hmac.compare_digest`.
  3. Constants: `SIGNATURE_HEADER = "X-Hub-Signature-256"`, `SIGNATURE_PREFIX = "sha256="`.

- [ ] T049 [US5] Rewrite `python-backend/src/channels/whatsapp/adapter.py` (~80 lines) to replace scaffold:
  1. `parse_webhook(raw, db_config)` — async method that extracts `phone_number_id` from payload metadata, calls `db_config.get_agent_by_whatsapp_phone(phone_number_id)` to resolve tenant, extracts customer phone from `messages[0].from`, message text from `messages[0].text.body`. Returns `InboundMessage` with real tenant_id.
  2. `async def send_reply(phone_number_id, access_token, recipient_phone, message)` — POST to `https://graph.facebook.com/v21.0/{phone_number_id}/messages` with proper headers and body (`{"messaging_product": "whatsapp", "to": recipient, "type": "text", "text": {"body": message}}`). Use `httpx.AsyncClient` with `timeout=10`.
  3. Remove hardcoded `tenant_id="flower_shop"`.

- [ ] T050 [US5] Rewrite `python-backend/src/channels/whatsapp/router.py` (~70 lines):
  1. Add signature verification middleware: in `receive_webhook()`, read raw body, verify signature via `verify_webhook_signature()`. Return 403 if invalid.
  2. After verification: parse webhook with `adapter.parse_webhook(payload, db_config)`.
  3. Use `BackgroundTasks` to invoke `graph_service.process_message()` asynchronously — the webhook must return 200 immediately per Meta requirements.
  4. After graph returns AI response, call `adapter.send_reply()` to send it back to WhatsApp.
  5. Update verify token lookup: query `whatsapp_connections` table by phone_number_id instead of global env var.

- [ ] T051 [US5] Run all US5 tests: `pytest python-backend/tests/unit/test_whatsapp_security.py python-backend/tests/unit/test_whatsapp_adapter.py python-backend/tests/unit/test_whatsapp_integration.py -v`. All GREEN.

**Checkpoint**: WhatsApp channel fully operational. Webhooks verified, tenant resolved from phone, AI responds, reply sent via Cloud API.

---

## Phase 8: User Story 6 — Rate Limiting & Input Safety (Priority: P2)

**Goal**: Per-tenant rate limiting prevents abuse. Input sanitization guards against prompt injection.

**Independent Test**: Send 100 rapid requests, verify 429 returned after threshold. Send message with injection attempt, verify it's sanitized.

### Tests for User Story 6 (MANDATORY — PDCA TDD Enforced) 🚨

- [ ] T052 [P] [US6] Write test for rate limiter in `python-backend/tests/unit/test_rate_limiter.py`.
  - **Called Shot**: `test_rate_limiter_allows_under_threshold` — make 5 requests from same IP+tenant in 1 minute, verify all return 200. Expected RED: `ImportError: cannot import name 'RateLimiterMiddleware' from 'src.middleware.rate_limiter'`.
  - **Called Shot**: `test_rate_limiter_blocks_over_threshold` — make 61 requests from same IP+tenant, verify 429 with `Retry-After` header. Expected RED: same ImportError.
  - **Called Shot**: `test_rate_limiter_is_per_tenant` — two different tenants from same IP, verify each has independent counter. Expected RED: same ImportError.

- [ ] T053 [P] [US6] Write test for input sanitizer in `python-backend/tests/unit/test_sanitizer.py`.
  - **Called Shot**: `test_sanitize_strips_html` — input `"<script>alert('xss')</script>Hello"` returns `"Hello"`. Expected RED: `ImportError: cannot import name 'sanitize_input' from 'src.core.sanitizer'`.
  - **Called Shot**: `test_sanitize_truncates_long_input` — input exceeding 4000 chars is truncated to 4000. Expected RED: same ImportError.
  - **Called Shot**: `test_sanitize_preserves_unicode` — Arabic, Russian, emoji text preserved. Expected RED: same ImportError.

### Implementation for User Story 6

- [ ] T054 [US6] Create `python-backend/src/middleware/rate_limiter.py` (~80 lines):
  1. In-memory sliding window rate limiter using `dict[tuple[str, str], list[float]]` keyed by `(client_ip, tenant_id)`.
  2. `class RateLimiterMiddleware(BaseHTTPMiddleware)` — reads `X-Forwarded-For` for real IP.
  3. Default: 60 req/min per tenant per IP. Configurable via settings.
  4. On limit exceeded: return 429 with `Retry-After` header and `{"detail": "Rate limit exceeded", "retry_after": seconds}`.

- [ ] T055 [US6] Create `python-backend/src/core/sanitizer.py` (~50 lines):
  1. `def sanitize_input(text: str, max_length: int = 4000) -> str` — strip HTML tags, truncate, normalize whitespace.
  2. `def detect_prompt_injection(text: str) -> bool` — basic pattern matching for common injection patterns (`"ignore previous instructions"`, `"system prompt:"`, etc.). Returns True if suspicious.
  3. Apply sanitization in `GraphService.process_message()` before passing to graph.

- [ ] T056 [US6] Register rate limiter middleware in `python-backend/src/app.py`:
  1. `from src.middleware.rate_limiter import RateLimiterMiddleware`
  2. `app.add_middleware(RateLimiterMiddleware)` — must be added after CORS middleware.

- [ ] T057 [US6] Run all US6 tests. All GREEN.

**Checkpoint**: Rate limiting active. Input sanitized. Abuse prevention in place.

---

## Phase 9: User Story 7 — Structured Logging (Priority: P2)

**Goal**: All logs use structlog with JSON output in production. Correlation ID tracks request across services. Tenant ID and conversation ID bound to every log entry.

**Independent Test**: Send a request, verify JSON log output contains `correlation_id`, `tenant_id`, and `request_path`.

### Tests for User Story 7 (MANDATORY — PDCA TDD Enforced) 🚨

- [ ] T058 [P] [US7] Write test for logging setup in `python-backend/tests/unit/test_logging.py`.
  - **Called Shot**: `test_log_includes_correlation_id` — invoke the logging middleware, verify log output contains `correlation_id` field. Expected RED: `ImportError: cannot import name 'setup_logging' from 'src.core.logging_config'`.
  - **Called Shot**: `test_log_includes_tenant_id` — make a request with tenant context, verify log contains `tenant_id`. Expected RED: same ImportError.

### Implementation for User Story 7

- [ ] T059 [US7] Create `python-backend/src/core/logging_config.py` (~70 lines):
  1. `import structlog`. Configure processors: `add_log_level`, `TimeStamper(fmt="iso")`, `JSONRenderer()` for production / `ConsoleRenderer()` for development.
  2. `def setup_logging(log_format: str = "console")` — configures structlog + stdlib logging integration.
  3. Call from `python-backend/src/app.py` lifespan startup.

- [ ] T060 [US7] Create `python-backend/src/middleware/correlation.py` (~40 lines):
  1. `class CorrelationMiddleware(BaseHTTPMiddleware)` — generates UUID4 correlation ID per request, stores in `contextvars.ContextVar`.
  2. Adds `X-Correlation-ID` response header.
  3. structlog binds `correlation_id` via context processor.

- [ ] T061 [US7] Replace all `logging.getLogger()` calls across codebase with `structlog.get_logger()`. Files to update: `src/repositories/db_repo.py`, `src/config/db_tenant_config.py`, `src/config/tenant_config.py`, `src/nodes/assistant.py`, `src/channels/whatsapp/router.py`. Use `structlog.get_logger()` and `logger.info(event, key=value)` style.
  Add `structlog` to `python-backend/pyproject.toml` dependencies.

- [ ] T062 [US7] Run all US7 tests. All GREEN.

**Checkpoint**: Structured logging active. Every request traceable by correlation ID.

---

## Phase 10: User Story 8 — Production Readiness (Priority: P2)

**Goal**: Health check endpoint, Dockerfile, environment validation, and comprehensive test suite.

**Independent Test**: `docker build && docker run` — container starts, `/health` returns 200 with `"status": "ok"`.

### Tests for User Story 8 (MANDATORY — PDCA TDD Enforced) 🚨

- [ ] T063 [P] [US8] Write test for health endpoint in `python-backend/tests/unit/test_health.py`.
  - **Called Shot**: `test_health_returns_ok` — `GET /health` returns 200 with `{"status": "ok", "service": "nova-backend"}`. Expected RED: `404 Not Found` (endpoint doesn't exist or returns different format).
  - **Called Shot**: `test_health_returns_503_when_db_down` — mock DB connection failure, verify `/health` returns 503 with `"status": "degraded"`. Expected RED: same 404 or different response shape.

### Implementation for User Story 8

- [ ] T064 [US8] Create health endpoint in `python-backend/src/app.py` (add to existing file):
  1. `@app.get("/health")` — checks DB connectivity by pinging connection pool. Returns `{"status": "ok", "service": "nova-backend", "database": "connected", "uptime_seconds": ...}` or `503` with `"status": "degraded"`.

- [ ] T065 [P] [US8] Create `python-backend/Dockerfile` (~30 lines):
  1. Base: `python:3.12-slim`
  2. Install dependencies: `pip install --no-cache-dir -e .`
  3. Copy source: `COPY . /app`
  4. Expose 8000.
  5. CMD: `uvicorn src.app:app --host 0.0.0.0 --port 8000`
  6. Add `.dockerignore` for `.venv`, `__pycache__`, `.env`, `tests/`.

- [ ] T066 [US8] Create `python-backend/.env.example` with all required environment variables documented (reference `specs/002-nova-backend/quickstart.md`).

- [ ] T067 [US8] Run full test suite: `pytest python-backend/tests/ -v --cov=src --cov-report=term-missing`. Verify ≥80% coverage on `src/services/`, `src/nodes/`, `src/middleware/`.

- [ ] T068 [US8] Run `python-backend/quickstart.md` validation sequence:
  1. `ruff check src/` — zero violations
  2. `pytest tests/unit/` — all green
  3. Docker build succeeds: `docker build -t nova-backend .`

**Checkpoint**: Production-ready. Health check works. Docker builds. Tests pass with coverage.

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T069 [P] Verify all files under `python-backend/src/` are ≤ 300 lines. If any exceed, split per constitution rules. Run: `find python-backend/src -name "*.py" -exec wc -l {} + | sort -rn | head -20`.

- [ ] T070 [P] Audit all `async def` functions for missing `await` calls. Grep for `httpx.AsyncClient` usages and verify every `.get()`, `.post()` is `await`-ed.

- [ ] T071 Add README section to `python-backend/README.md` documenting: project structure, how to run, how to test, environment variables.

- [ ] T072 Security hardening: verify no secrets in code (grep for `sk-`, `eyJ`, hardcoded tokens). Verify `.env` is in `.gitignore`.

- [ ] T073 Run `specs/002-nova-backend/quickstart.md` full validation — all phases pass.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 — BLOCKS all subsequent phases (critical bugs)
- **US2 (Phase 4)**: Depends on US1 (clean codebase needed)
- **US3 (Phase 5)**: Depends on US2 (needs GraphService)
- **US4 (Phase 6)**: Depends on US2 (needs GraphService + ConversationService)
- **US5 (Phase 7)**: Depends on US2 (needs GraphService), can parallel with US3/US4
- **US6 (Phase 8)**: Depends on US2, can parallel with US3/US4/US5
- **US7 (Phase 9)**: Depends on US1, can parallel with US2+
- **US8 (Phase 10)**: Depends on all prior phases
- **Polish (Phase 11)**: Depends on all desired stories

### Critical Path

```
Setup → Foundational → US1 (bugs) → US2 (persistence) → US3 (resilience) → US4 (HITL) → US8 (production)
                                          ↓
                                     US5 (WhatsApp) ─── parallel with US3/US4
                                          ↓
                                     US6 (rate limit) ─ parallel with US3/US4/US5
                                     US7 (logging) ──── parallel with US2+
```

### Within Each User Story

- Tests MUST be written and FAIL before implementation (PDCA TDD)
- Models/enums before services
- Services before endpoints/routers
- Core implementation before integration
- Story complete (GREEN) before moving to next priority

### Parallel Opportunities

Within US1 (Phase 3):
- T006, T007, T008, T009, T010, T011 — all test tasks run in parallel
- T012, T013, T016 — independent bug fixes run in parallel
- T014 (async migration) and T015 (instruction injection) are sequential (T014 first)

After US1 completes:
- US5, US6, US7 can start in parallel with US3/US4

---

## Parallel Example: User Story 1

```bash
# Launch all US1 test tasks together (they test different files):
Task T006: "test_agent_state.py — dead fields"
Task T007: "test_config_models.py — name collision"
Task T008: "test_db_repo_async.py — async client"
Task T009: "test_system_prompt.py — instructions"
Task T010: "test_tool_names.py — tool rename"
Task T011: "test_tenant_cache.py — caching"

# After all RED tests confirmed, launch parallel fixes:
Task T012: "Remove dead state fields"    # agent_state.py
Task T013: "Fix AgentConfig collision"   # db_tenant_config.py
Task T016: "Rename misleading tool"      # send_product_image.py → get_product_details.py
```

---

## Phase 12: Coverage Gaps — Missing FR Tasks

**Purpose**: Tasks that were absent from the initial task generation, identified by `/speckit.analyze` coverage pass. All must be completed before US8 can close.

### FR-002 — Dead Code Removal (Phase 0 gap)

- [ ] T074 [P] [US1] Delete unreachable dead-code modules:
  1. Delete `python-backend/src/models/catalog.py` entirely — replaced by `src/models/product.py` + repository pattern. Grep for any remaining imports: `grep -r "from src.models.catalog" python-backend/src/` — fix any found.
  2. In `python-backend/src/repositories/json_repo.py` — convert to fallback-only: remove all public methods except `get_all_products()`. Add module docstring: `"DEPRECATED: Use DBProductRepository. Retained only as YAML fallback."`.
  3. Verify `python-backend/src/__init__.py` and `src/repositories/__init__.py` do NOT import from `catalog.py` or expose `JSONProductRepository` as primary.
  Reference: `BACKEND_BLUEPRINT_v3_EXPERT_REVIEW.md` lines 181-183.

### FR-033 — WhatsApp Typing Indicator (Phase 4 gap)

- [ ] T075 [P] [US5] Write test for typing indicator in `python-backend/tests/unit/test_whatsapp_typing.py`.
  - **Called Shot**: `test_send_typing_indicator_calls_api` — call `adapter.send_typing_indicator(phone_number_id, access_token, recipient_phone)`, verify it makes POST to `https://graph.facebook.com/v21.0/{phone_number_id}/messages` with body `{"messaging_product": "whatsapp", "to": recipient, "type": "reaction", "reaction": {"message_id": "...", "emoji": "⌛"}}` OR uses the WhatsApp `typing_on` action. Expected RED: `AttributeError: 'WhatsAppAdapter' object has no attribute 'send_typing_indicator'`.

- [ ] T076 [US5] Add `send_typing_indicator()` to `python-backend/src/channels/whatsapp/adapter.py`:
  1. `async def send_typing_indicator(self, phone_number_id, access_token, recipient_phone)` — POST to Meta API with `{"messaging_product": "whatsapp", "to": recipient_phone, "type": "text", "text": {"body": "⌛"}}`. Note: Meta's actual typing indicator uses the `status` read receipt endpoint — use `POST /{phone_number_id}/messages` with `type: "reaction"` or mark message as read.
  2. Call this in `python-backend/src/channels/whatsapp/router.py` `receive_webhook()` immediately after parsing the inbound message, BEFORE invoking `graph_service.process_message()`.
  3. File stays within 300-line limit.

### FR-034 — WhatsApp Media Messages (Phase 4 gap)

- [ ] T077 [P] [US5] Write test for WhatsApp image sending in `python-backend/tests/unit/test_whatsapp_media.py`.
  - **Called Shot**: `test_send_image_via_whatsapp` — call `adapter.send_image(phone_number_id, access_token, recipient_phone, image_url, caption)`, verify it POSTs to Meta API with `{"type": "image", "image": {"link": image_url, "caption": caption}}`. Expected RED: `AttributeError: 'WhatsAppAdapter' object has no attribute 'send_image'`.
  - **Called Shot**: `test_get_product_details_tool_triggers_media_send` — when `get_product_details` tool returns a product with `image_url`, the WhatsApp router sends it as a media message (not embedded in text). Expected RED: `AssertionError: image not sent as media`.

- [ ] T078 [US5] Add `send_image()` to `python-backend/src/channels/whatsapp/adapter.py` and wire it up:
  1. `async def send_image(self, phone_number_id, access_token, recipient_phone, image_url, caption="")` — POST to `https://graph.facebook.com/v21.0/{phone_number_id}/messages` with body `{"messaging_product": "whatsapp", "to": recipient_phone, "type": "image", "image": {"link": image_url, "caption": caption}}`.
  2. In `python-backend/src/channels/whatsapp/router.py` — after `graph_service.process_message()` returns, inspect tool call results for product image URLs. For each image URL found, call `adapter.send_image()` separately, then call `adapter.send_reply()` for the text response.

### FR-037 — Per-Tenant Subscription Rate Limits (Phase 5 gap)

- [ ] T079 [P] [US6] Write test for subscription-plan rate limiting in `python-backend/tests/unit/test_tenant_rate_limit.py`.
  - **Called Shot**: `test_tenant_limit_enforced_across_customers` — create 3 different customer IPs all hitting the same tenant, verify that when combined requests exceed tenant plan limit, the 429 fires. Expected RED: `AssertionError: expected 429 but got 200` (current limiter is IP-only, no tenant aggregate).

- [ ] T080 [US6] Extend `python-backend/src/middleware/rate_limiter.py` to add per-tenant aggregate counter:
  1. Add second counter dict: `_tenant_counters: dict[str, list[float]]` keyed by `tenant_id`.
  2. Default tenant plan limit: 600 req/hour (configurable via `TENANT_RATE_LIMIT_PER_HOUR` env var).
  3. Check tenant counter BEFORE IP counter — if tenant exceeds plan limit, return 429 with `{"detail": "Tenant plan limit exceeded"}`.

### FR-044 — Log File Daily Rotation (Phase 6 gap)

- [ ] T081 [US7] Add daily log file rotation to `python-backend/src/core/logging_config.py`:
  1. In `setup_logging()`, when `log_format == "json"` (production), add `logging.handlers.TimedRotatingFileHandler` with `when="midnight"`, `backupCount=30`, `filename="logs/nova.log"`.
  2. Ensure `logs/` directory is created on startup if it doesn't exist: `Path("logs").mkdir(exist_ok=True)`.
  3. Add `logs/` to `.gitignore` and `.dockerignore`.

### FR-045 — PII Scrubbing in Logs (Phase 6 gap)

- [ ] T082 [P] [US7] Write test for PII scrubber in `python-backend/tests/unit/test_pii_scrubber.py`.
  - **Called Shot**: `test_phone_numbers_scrubbed` — pass a log record containing `+1234567890`, verify the emitted log replaces it with `[PHONE]`. Expected RED: `AssertionError: '+1234567890' found in log output`.
  - **Called Shot**: `test_email_addresses_scrubbed` — same for email addresses. Expected RED: `AssertionError: email still present`.

- [ ] T083 [US7] Create `python-backend/src/core/pii_scrubber.py` (~40 lines) and wire into structlog:
  1. `def scrub_pii(value: str) -> str` — regex-replace: phone numbers (`+?\d[\d\s\-]{8,}\d` → `[PHONE]`), emails (`\S+@\S+\.\S+` → `[EMAIL]`).
  2. Add `PIIScrubberProcessor` as a structlog processor in `setup_logging()` before `JSONRenderer`.

### FR-050 — Multi-Stage Docker Build (Phase 7 gap)

- [ ] T084 [US8] Rewrite `python-backend/Dockerfile` as true multi-stage build (~25 lines):
  ```dockerfile
  # Stage 1: builder
  FROM python:3.12-slim AS builder
  WORKDIR /build
  COPY pyproject.toml .
  RUN pip install --no-cache-dir build && python -m build --wheel

  # Stage 2: runtime
  FROM python:3.12-slim AS runtime
  WORKDIR /app
  COPY --from=builder /build/dist/*.whl /tmp/
  RUN pip install --no-cache-dir /tmp/*.whl && rm /tmp/*.whl
  COPY src/ src/
  EXPOSE 8000
  CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]
  ```
  Verify runtime image has NO build tools (pip, setuptools) except runtime dependencies. Update `.dockerignore` to exclude `tests/`, `specs/`, `*.md`, `.env`, `.git`.

### FR-051 — Cross-Tenant Isolation Test (Cross-Cutting gap)

- [ ] T085 [P] Write cross-tenant isolation test in `python-backend/tests/integration/test_tenant_isolation.py`.
  - **Called Shot**: `test_tenant_a_cannot_read_tenant_b_conversations` — create two tenants (A and B) in test fixtures, create conversations for each, query `GET /api/conversations?agent_id=<agent_A>`, verify ZERO rows from tenant B appear. Expected RED: requires integration test harness with real Supabase test instance — use `pytest.mark.integration` marker and `SUPABASE_TEST_URL` env var.
  - **Called Shot**: `test_tenant_a_products_not_in_tenant_b_search` — search products for tenant A, verify no tenant B products appear. Expected RED: same integration harness.
  - Add `pytest.mark.integration` marker to `python-backend/pyproject.toml` markers config.

---

## Phase 13: Success Criteria — Buildable Work (SC Tests)

**Purpose**: Measurable success criteria from spec.md that require explicit test infrastructure. These are NOT unit tests — they are performance/reliability assertions.

### SC-005 — 50 Concurrent Conversations

- [ ] T086 [P] Write concurrency test in `python-backend/tests/performance/test_concurrency.py`.
  - **Called Shot**: `test_50_concurrent_conversations` — use `asyncio.gather()` to fire 50 simultaneous `GraphService.process_message()` calls across 5 simulated tenants (10 each). Assert all complete within 10 seconds and all return non-empty responses. Expected RED: either timeout or event-loop blocking from any remaining sync I/O. Use `pytest-asyncio` with `asyncio_mode = "auto"`.
  - Mock LLM responses to return instantly — only testing concurrency infrastructure, not AI quality.

- [ ] T087 [US6] Create `python-backend/tests/performance/__init__.py` and add `@pytest.mark.performance` marker to `pyproject.toml`. Performance tests excluded from default `pytest` run — run with: `pytest -m performance`.

### SC-006 — Zero Cross-Tenant Data Leakage

- [ ] T088 Covered by T085 (cross-tenant isolation tests). Confirm T085 is tagged `[SC-006]` and runs in CI.

### SC-007 — 15-Second Startup

- [ ] T089 [P] [US8] Write startup timing test in `python-backend/tests/unit/test_startup_time.py`.
  - **Called Shot**: `test_app_starts_within_15_seconds` — record time before calling `app.router.startup()` coroutine (from FastAPI lifespan), assert elapsed < 15.0 seconds. Expected RED: test currently fails because startup includes network calls to Supabase (pool init) — mock the pool creation to measure overhead only.
  - This is a regression guard, not a full integration test.

### SC-008 — 30-Second Graceful Shutdown

- [ ] T090 [P] [US8] Write graceful shutdown test in `python-backend/tests/unit/test_graceful_shutdown.py`.
  - **Called Shot**: `test_shutdown_closes_connections_within_30s` — simulate in-flight requests during shutdown. Trigger lifespan teardown. Verify: (1) `graph_service.shutdown()` is awaited, (2) `_db_repo.aclose()` is awaited, (3) all complete within 30 seconds. Expected RED: `AssertionError: shutdown did not close connection pool` (T028 adds the calls but this test verifies ordering and timing).

---

## Phase 14: Edge Cases — Spec-Mandated Behaviors

**Purpose**: Six edge cases from spec.md §Edge Cases. Each is a spec-mandated behavior with zero task coverage.

### Edge Case 1 — Non-Text WhatsApp Messages

- [ ] T091 [P] [US5] Write test in `python-backend/tests/unit/test_whatsapp_nontextmsg.py`.
  - **Called Shot**: `test_image_message_returns_polite_response` — send webhook payload with `type: "image"` (not `type: "text"`). Verify AI is NOT invoked and customer receives text: `"I currently support text messages only. Please describe what you need and I'll help you."`. Expected RED: `AssertionError: graph_service called for non-text message` or `AssertionError: no polite response sent`.

- [ ] T092 [US5] In `python-backend/src/channels/whatsapp/adapter.py` `parse_webhook()`, add message type check:
  1. Extract `msg_obj.get("type")` — if not `"text"`, return special `InboundMessage` with `text=None` and `message_type=<actual_type>`.
  2. In `python-backend/src/channels/whatsapp/router.py`, before calling `graph_service`, check `if inbound_msg.text is None` — send polite fallback reply via `adapter.send_reply()` without invoking the graph. Log: `logger.info("non_text_message_received", message_type=inbound_msg.message_type)`.
  3. Update `python-backend/src/models/message.py` to add `message_type: str = "text"` field to `InboundMessage`.

### Edge Case 2 — Tenant Subscription Expired

- [ ] T093 [P] Write test in `python-backend/tests/unit/test_tenant_inactive.py`.
  - **Called Shot**: `test_inactive_tenant_returns_503` — send message for a tenant whose `is_active=False` in DB. Verify graph is NOT invoked and response is 503 with `{"detail": "Agent is inactive"}`. Expected RED: `AssertionError: expected 503 but got 200` (current code doesn't check `is_active` in router).

- [ ] T094 [US5] In `python-backend/src/services/graph_service.py` `process_message()`, after loading tenant config, check `if agent_config is None or not agent_config.is_active` — raise `HTTPException(status_code=503, detail="Agent is inactive or not found")`. Handle in router with try/except.

### Edge Case 3 — Simultaneous Messages Same Conversation

- [ ] T095 [P] Write test in `python-backend/tests/unit/test_concurrent_messages.py`.
  - **Called Shot**: `test_simultaneous_messages_processed_sequentially` — fire 2 `process_message()` calls concurrently for the SAME `session_id` using `asyncio.gather()`. Verify both complete without state corruption (message list has exactly 2 entries in correct order). Expected RED: race condition where LangGraph processes both from same checkpoint state, or `AssertionError: messages out of order`.
  - 📎 LangGraph: PostgresSaver uses optimistic locking on checkpoint writes — concurrent writes to same thread_id raise `CheckpointConflict`. Handle in `GraphService.process_message()` with retry.

---

## Implementation Strategy



### MVP First (US1 + US2 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: US1 (codebase health) — **STOP if bugs remain**
4. Complete Phase 4: US2 (persistent conversations)
5. **VALIDATE**: Web chat works, conversations persist, admin can list them
6. Deploy/demo if ready (MVP!)

### Incremental Delivery

1. Setup + Foundational + US1 → Stable codebase
2. Add US2 → Conversations persist → Test independently
3. Add US3 → AI is resilient → Test independently
4. Add US4 → HITL works → Test independently
5. Add US5 → WhatsApp live → Test independently
6. Add US6+US7 → Hardened → Test independently
7. US8 → Production ready → Final validation

---

## Task Summary

| Phase | Story | Tasks | Test Tasks | Impl Tasks |
|-------|-------|-------|------------|------------|
| 1 | Setup | T001-T003 | 0 | 3 |
| 2 | Foundational | T004-T005 | 0 | 2 |
| 3 | US1 Bugs | T006-T019 | 6 | 8 |
| 4 | US2 Persistence | T020-T029 | 3 | 7 |
| 5 | US3 Resilience | T030-T035 | 2 | 4 |
| 6 | US4 HITL | T036-T044 | 3 | 6 |
| 7 | US5 WhatsApp | T045-T051 | 3 | 4 |
| 8 | US6 Rate Limit | T052-T057 | 2 | 4 |
| 9 | US7 Logging | T058-T062 | 1 | 4 |
| 10 | US8 Production | T063-T068 | 1 | 5 |
| 11 | Polish | T069-T073 | 0 | 5 |
| 12 | Coverage Gaps (FRs) | T074-T085 | 7 | 5 |
| 13 | SC Buildable Work | T086-T090 | 5 | 0 |
| 14 | Edge Cases | T091-T095 | 3 | 2 |
| **Total** | | **95** | **36** | **59** |



## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story
- Each user story is independently completable and testable
- Every test watched fail before watching it pass (PDCA Called Shot)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- **300-line rule enforced** — any file exceeding 300 lines must be split
