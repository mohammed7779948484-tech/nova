<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan
at `specs/002-nova-backend/plan.md`
<!-- SPECKIT END -->

# Nova Backend — Agent Guide

## Build / Lint / Test Commands

```bash
# Install dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run unit tests only
pytest tests/unit/

# Run a single test file
pytest tests/unit/test_llm_service.py

# Run one test by name
pytest -k "test_llm_service_retries_on_rate_limit"

# Run with coverage
pytest --cov=src --cov-report=term-missing

# Lint (uses ruff, line-length 119)
ruff check .

# Format
ruff format .

# Run dev server
uvicorn src.app:app --host 0.0.0.0 --port 8000 --reload
```

**Important**: The venv is at `python-backend/.venv/`. Activate it before running commands:
```bash
# Windows
python-backend/.venv/Scripts\activate
# Linux/Mac
source python-backend/.venv/bin/activate
```

Pytest config: `asyncio_mode = "auto"`, `testpaths = ["tests"]`. Explicit `@pytest.mark.asyncio` is used on async test methods for clarity despite auto mode.

## Project Structure

```
python-backend/
├── src/
│   ├── app.py                  # FastAPI app, lifespan, router mounts
│   ├── config/                 # Settings, tenant config, LLM provider
│   ├── services/               # Business logic: graph_service, llm_service, conversation_service
│   ├── channels/               # Routers + adapters (web/, whatsapp/, admin/)
│   ├── graphs/sales_graph.py   # LangGraph StateGraph assembly
│   ├── nodes/                  # Graph nodes: assistant, tool_executor, escalation
│   ├── state/agent_state.py    # SalesAgentState TypedDict
│   ├── models/                 # Pydantic schemas + enums
│   ├── repositories/           # Data access (db_repo, base)
│   ├── tools/                  # LangChain tools (search, promotions, product details)
│   └── middleware/              # Rate limiter, correlation, sanitizer (Phases 5-7)
├── tests/
│   ├── conftest.py             # Shared fixtures (app_client, env vars)
│   └── unit/                   # Unit tests by feature
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

### Structure
- **Unit tests**: `tests/unit/` — test business logic with mocks at infrastructure boundaries
- **Integration tests**: `tests/integration/` — test with real services (requires DB)
- PDCA Called Shot format in module docstrings: declare test name, behavior, expected RED failure
- Class per feature: `TestLLMServiceRetry`, `TestContextSummary`

### Mocking
- Use `AsyncMock` for async methods, `MagicMock` for sync
- Mock at infrastructure boundaries (httpx client, DB connections), not internal collaborators
- Create factory helpers for common test fixtures (`_make_tc()`, `_make_mock_model()`)

```python
mock_model = AsyncMock()
mock_model.ainvoke.return_value = AIMessage(content="response")
mock_model.bind_tools = MagicMock(return_value=mock_model)
```

### Environment
`conftest.py` sets required env vars: `ENVIRONMENT=test`, `SUPABASE_URL=https://test.supabase.co`, `SUPABASE_SERVICE_KEY=test-key`. Integration tests skip if `DATABASE_URL` is unset or on Windows (psycopg_pool limitation).

## Key Patterns

### Services are module-level singletons
```python
llm_service = LLMService()  # at bottom of llm_service.py
graph_service = GraphService()  # at bottom of graph_service.py
```

### LangGraph routing uses Command, not conditional edges
```python
return Command(update={"messages": [result]}, goto="tools")
```

### Pydantic v2
- `model_config = ConfigDict(from_attributes=True)` on all models
- `Field(default_factory=list)` for mutable defaults, never `[]`
- `.model_dump()` for serialization, never `.dict()`

### Tenant config caching
- Sync: `@lru_cache(maxsize=1)` for `get_settings()`
- Async: manual dict with TTL (`_tenant_cache: dict[str, tuple[TenantConfig, float]]`)

### 300-line file limit
All source files must stay under 300 lines. If a file exceeds this, split it.