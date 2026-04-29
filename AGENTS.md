<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan
at `specs/002-nova-backend/plan.md`
<!-- SPECKIT END -->

# Nova Backend — Agent Guide

## Project Status

| Phase | User Story | Tasks | Status |
|-------|-----------|-------|--------|
| 1-3 | Codebase Health Baseline | T001-T019 | ✅ Complete |
| 4 | Persistent Conversations | T020-T029 | ✅ Complete |
| 5 | AI Resilience & Context | T030-T035 | ✅ Complete |
| 6 | Human-in-the-Loop | T036-T044 | ✅ Complete |
| 7 | WhatsApp Channel | T045-T051 | ⏸️ DEFERRED (requires WhatsApp Cloud API + phone verification) |
| 9 | Structured Logging | T058-T062 | ✅ Complete |
| 8 | Rate Limiting & Input Safety | T052-T057 | ✅ Complete |
| 9+ | Structured Logging / Production | T058+ | 🔲 Not started |

**Total tests: 79 — all using real DB (Supabase PostgreSQL) + real LLM (LongCat), NO mocks.**

## Build / Lint / Test Commands

```bash
# Install dependencies (use uv, not pip)
cd python-backend
UV_CACHE_DIR=/tmp/uv_cache uv sync

# Run all tests
UV_CACHE_DIR=/tmp/uv_cache uv run pytest tests/ -v

# Run Phase 8 tests only
UV_CACHE_DIR=/tmp/uv_cache uv run pytest tests/unit/test_rate_limiter.py tests/unit/test_sanitizer.py -v

# Run escalation integration tests (real DB + real LLM)
UV_CACHE_DIR=/tmp/uv_cache uv run pytest tests/unit/test_escalation_node.py -v --timeout=120

# Run one test by name
UV_CACHE_DIR=/tmp/uv_cache uv run pytest -k "test_rate_limiter_allows_under_threshold"

# Run with coverage
UV_CACHE_DIR=/tmp/uv_cache uv run pytest --cov=src --cov-report=term-missing

# Lint (uses ruff, line-length 119)
UV_CACHE_DIR=/tmp/uv_cache uv run ruff check .

# Format
UV_CACHE_DIR=/tmp/uv_cache uv run ruff format .

# Run dev server
UV_CACHE_DIR=/tmp/uv_cache uv run uvicorn src.app:app --host 0.0.0.0 --port 8000 --reload
```

Pytest config: `asyncio_mode = "auto"`, `testpaths = ["tests"]`. Explicit `@pytest.mark.asyncio` is used on async test methods for clarity despite auto mode.

## Environment Setup

The `.env` file lives at `python-backend/.env` and contains:

```env
# Supabase
SUPABASE_URL=https://jknpjyumqbqvhepwensn.supabase.co
SUPABASE_SERVICE_KEY=<service_role_key>

# Database
DATABASE_URL=postgresql://postgres.jknpjyumqbqvhepwensn:<password>@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres

# LLM (LongCat — OpenAI-compatible endpoint)
OPENAI_API_BASE=https://api.longcat.chat/openai
OPENAI_API_KEY=ak_2m25P19582BF8Kr6et8889lY6D69S
```

Settings are loaded via `pydantic_settings.BaseSettings` with `SettingsConfigDict(env_file=".env")`. The path is resolved relative to `python-backend/` root.

## Project Structure

```
python-backend/
├── .env                        # Environment variables (Supabase + LLM credentials)
├── src/
│   ├── app.py                  # FastAPI app, lifespan, router mounts, middleware registration
│   ├── config/                 # Settings (BaseSettings), tenant config (caching), LLM provider, db_tenant_config
│   ├── core/                   # Core utilities: sanitizer.py (input sanitization + injection detection)
│   ├── services/               # Business logic: graph_service, llm_service, conversation_service
│   ├── channels/               # Routers + adapters (web/, whatsapp/, admin/)
│   ├── graphs/sales_graph.py   # LangGraph StateGraph assembly + compile_with_postgres_async()
│   ├── nodes/                  # Graph nodes: assistant, tool_executor, escalation
│   ├── state/agent_state.py    # SalesAgentState TypedDict (messages, channel, channel_user_id)
│   ├── models/                 # Pydantic schemas, enums (ConversationStatus, MessageRole, EscalationReason), lifecycle
│   ├── repositories/           # Data access: db_repo (async httpx), json_repo, base
│   ├── tools/                  # LangChain tools (search_products, get_promotions, get_product_details, search_by_image)
│   └── middleware/             # RateLimiterMiddleware (sliding window, per-tenant/IP)
├── tests/
│   ├── conftest.py             # Shared fixtures (sets ENVIRONMENT=test)
│   ├── test_memory_arabic.py   # Arabic language memory test
│   └── unit/                   # Unit + integration tests by feature (75 total)
├── database/                   # SQL migration files (tenants, agents, products, conversations, messages, etc.)
├── tenants/                    # Per-tenant config (flower_shop, tech_store, restaurant_test)
└── pyproject.toml              # Dependencies + tool config
```

## Code Style

### Imports
Group in 4 sections with blank lines between: `__future__`, stdlib, third-party, local. Use lazy imports inside functions to avoid circular dependencies.

```python
from __future__ import annotations

import asyncio
import logging
from typing import Any

from langchain_core.messages import BaseMessage
from tenacity import retry, stop_after_attempt

from src.config.tenant_config import TenantConfig
```

### Naming
| Element | Convention | Example |
|---|---|---|
| Classes | PascalCase | `LLMService`, `TenantConfig` |
| Functions/methods | snake_case | `process_message`, `_build_model` |
| Private methods | `_leading_underscore` | `_invoke_with_retry` |
| Constants | UPPER_SNAKE_CASE | `GRACEFUL_FAILURE_MESSAGE`, `MAX_RETRIES` |
| Module singletons | snake_case module var | `llm_service`, `graph_service` |
| Test classes | `Test` prefix | `TestLLMServiceRetry` |
| Test functions | `test_` prefix | `test_llm_service_retries_on_rate_limit` |

### Types
- Use `from __future__ import annotations` in every source file
- Use `X | None` not `Optional[X]`
- Use lowercase generics: `list[str]`, `dict[str, Any]`
- Use `Any` for LangChain model types where exact type is complex

### Docstrings
Google-style with `Args:` and `Returns:` sections. Every module has a top-level docstring. Private helpers get one-line docstrings.

```python
async def process_message(self, tenant_slug: str, message: str) -> str:
    """Process a customer message through the LangGraph agent.

    Args:
        tenant_slug: The tenant identifier (e.g. "flower_shop")
        message: The customer's message

    Returns:
        The AI's response text.
    """
```

### Logging
Use stdlib `logging.getLogger(__name__)`. Use `%`-formatting in log calls (lazy eval), not f-strings:

```python
logger = logging.getLogger(__name__)
logger.info("connection_pool_created")
logger.warning("switching_model from=%s to=%s", old_name, new_name)
logger.exception("llm_call_failed model=%s tried=%d", name, count)
```

### Error Handling
- Catch exceptions and return graceful fallbacks, don't let errors propagate to the caller
- Use `logger.exception()` for errors with traceback (includes exc_info automatically)
- Use `ValueError` for config validation, `HTTPException` for API errors
- No custom exception hierarchy — use standard Python exceptions

### Async
- **All I/O is async** — use `httpx.AsyncClient` (never `requests` or sync `httpx.Client`)
- Use `asyncio.gather()` for parallel execution of multiple tool calls
- Use `asyncio.wait_for()` for timeouts on LLM calls
- Use lazy initialization for clients and connection pools (create on first use, not at import)

### Formatting
- Line length: 119 (ruff default in reference template)
- Double quotes for strings
- Trailing commas in multi-line collections
- 2 blank lines between top-level definitions
- Section separators: `# --- 71 dashes ---`

## Testing

### NO MOCKS POLICY (Phase 8 Review — Enforced)

**All tests MUST use real database (Supabase PostgreSQL) and real LLM (LongCat).**
There are NO mock tests, NO fake tests, NO `unittest.mock` imports in the codebase.

- ❌ Do NOT use `unittest.mock`, `AsyncMock`, `MagicMock`, `patch()`
- ✅ DO use real Supabase DB via `DATABASE_URL` in `.env`
- ✅ DO use real LongCat LLM via `OPENAI_API_BASE` in `.env`
- ✅ Integration tests use `@requires_postgres` skip marker when DB is unreachable
- ✅ Windows skip: `pytest.skip("psycopg_pool requires SelectorEventLoop")`

### Structure
- **Unit tests**: `tests/unit/` — test business logic with real services
- **Integration tests**: `tests/integration/` — test with real services (requires DB)
- PDCA Called Shot format in module docstrings: declare test name, behavior, expected RED failure
- Class per feature: `TestEscalationViaRealGraph`, `TestLLMServiceRealCalls`

### Environment for Testing
`conftest.py` sets `ENVIRONMENT=test` to bypass startup validation. Integration tests skip if PostgreSQL is unreachable (checked via `_postgres_reachable()` socket test).

## Key Patterns

### Services are module-level singletons
```python
llm_service = LLMService()  # at bottom of llm_service.py
graph_service = GraphService()  # at bottom of graph_service.py
conversation_service = ConversationService()  # at bottom of conversation_service.py
```

### LangGraph routing uses Command, not conditional edges
```python
return Command(update={"messages": [result]}, goto="tools")
```

### LangGraph interrupt/resume (Human-in-the-Loop)
```python
# Escalation node pauses graph execution
from langgraph.types import interrupt
interrupt({"reason": "customer_request", "message": "Waiting for supervisor input"})

# Resume with supervisor response
from langgraph.types import Command
result = await graph.ainvoke(Command(resume=supervisor_response), config=config)
```

### Pydantic v2
- `model_config = ConfigDict(from_attributes=True)` on all models
- `Field(default_factory=list)` for mutable defaults, never `[]`
- `.model_dump()` for serialization, never `.dict()`

### Tenant config caching
- Sync: `@lru_cache(maxsize=1)` for `get_settings()`
- Async: manual dict with TTL (`_tenant_cache: dict[str, tuple[TenantConfig, float]]`)
- `invalidate_tenant_cache(tenant_id=None)` to clear one or all entries

### Input sanitization (Phase 8)
```python
from src.core.sanitizer import sanitize_input, detect_prompt_injection

message = sanitize_input(message)  # strip HTML, truncate to 4000, normalize whitespace
if detect_prompt_injection(message):
    logger.warning("prompt_injection_detected session_id=%s tenant=%s", session_id, tenant_slug)
```

### Rate limiting (Phase 8)
- `RateLimiterMiddleware` — in-memory sliding window, 60 req/min per (IP, tenant_id)
- Reads `X-Forwarded-For` for real client IP, `X-Tenant-ID` for tenant
- Returns 429 with `Retry-After` header on limit exceeded
- Registered in `app.py` after CORS middleware (LIFO: runs first on inbound)

### Lifecycle state machine (Phase 6)
```python
from src.models.lifecycle import validate_transition, transition_or_raise
# Valid: active→escalated, escalated→active/handed_off/resolved, handed_off→active/resolved
transition_or_raise(current_status, target_status)  # raises ValueError if invalid
```

### 300-line file limit
All source files must stay under 300 lines. If a file exceeds this, split it.

## Git Convention

Commits follow the pattern:
```
feat: implement Phase N — Description (TXXX-TXXX)
```

Each commit includes a detailed body listing:
- New files created (with line counts)
- Modified files and what changed
- Dead code removed
- Test results (count + "real DB + real LLM, no mocks")
