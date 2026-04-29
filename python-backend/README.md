<div align="center">

# Nova Backend

**Multi-tenant AI customer service platform powered by LangGraph**

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Tests](https://img.shields.io/badge/Tests-83%20passing-success?style=flat-square)]()

</div>

---

## What is this?

The Python/FastAPI backend for Nova — a multi-tenant AI customer service SaaS platform. It orchestrates LangGraph-based AI agents, persists conversations via PostgresSaver, and provides admin endpoints for conversation management and HITL (human-in-the-loop) workflows.

---

## Project Structure

```
python-backend/
├── src/
│   ├── app.py                       # FastAPI app, lifespan, router mounts
│   ├── config/                      # Settings, tenant config (DB + cache), LLM provider
│   ├── core/                        # Logging config (structlog), input sanitizer
│   ├── services/                    # graph_service, llm_service, conversation_service
│   ├── channels/                    # Routers + adapters (web/, whatsapp/, admin/)
│   ├── graphs/sales_graph.py        # LangGraph StateGraph assembly
│   ├── nodes/                       # assistant, tool_executor, escalation
│   ├── state/agent_state.py         # SalesAgentState TypedDict
│   ├── models/                      # Pydantic schemas, enums, lifecycle
│   ├── repositories/                # db_repo (async httpx), json_repo
│   ├── tools/                       # search_products, get_promotions, etc.
│   └── middleware/                  # Rate limiter, correlation ID, sanitizer
├── tests/                           # 83 tests, real DB + real LLM, NO mocks
├── database/                        # SQL schema (11 tables)
├── tenants/                         # Per-tenant config (flower_shop, tech_store, restaurant)
├── Dockerfile                       # uv + Python 3.12
├── docker-compose.yml               # backend + test services
└── .env.example                     # Environment variable template
```

---

## Quick Start

### Prerequisites

- Python 3.12+
- Docker Desktop (optional, for containerized runs)
- Supabase project with the 11-table schema provisioned
- At least one LLM API key

### 1. Install dependencies

```bash
cd python-backend

# Using uv (recommended, 10-100x faster than pip)
uv sync --extra dev

# Or using pip
pip install -e ".[dev]"
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and add your Supabase and LLM credentials
```

Required variables:

| Variable | Description |
|----------|-------------|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Supabase service_role key |
| `DATABASE_URL` | PostgreSQL connection string |
| `OPENAI_API_KEY` | LLM API key (OpenAI-compatible) |
| `OPENAI_API_BASE` | LLM API base URL |
| `ENVIRONMENT` | `development` / `staging` / `production` |
| `LOG_FORMAT` | `console` (dev) / `json` (production) |

### 3. Run the dev server

```bash
# Locally
uv run uvicorn src.app:app --host 0.0.0.0 --port 8000 --reload

# Or via Docker
docker compose up backend
```

### 4. Verify

```bash
curl http://localhost:8000/health
# {"status":"ok","service":"nova-backend","database":"connected","uptime_seconds":1.2}
```

---

## Running Tests

All tests use **real Supabase PostgreSQL** and **real LLM** — no mocks.

```bash
# All tests
uv run pytest tests/ -v

# Specific test file
uv run pytest tests/unit/test_health.py -v

# With coverage
uv run pytest --cov=src --cov-report=term-missing

# Lint
uv run ruff check src/

# Format
uv run ruff format src/

# Via Docker
docker compose run --rm test uv run pytest tests/ -v
```

---

## Docker

```bash
# Build
docker compose build

# Run backend
docker compose up backend

# Run tests
docker compose run --rm test

# Run specific test
docker compose run --rm test uv run pytest tests/unit/test_rate_limiter.py -v

# Stop
docker compose down
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check with DB status and uptime |
| POST | `/chat` | Web chat endpoint |
| GET | `/admin/{agent_id}/conversations` | List conversations |
| GET | `/admin/{agent_id}/conversations/{id}/messages` | Get messages |
| POST | `/admin/conversations/{id}/resume` | Resume escalated conversation |
| POST | `/admin/conversations/{id}/handoff` | Hand off to human |
| POST | `/api/webhooks/whatsapp` | WhatsApp webhook |

---

## Architecture

- **LangGraph StateGraph** with PostgresSaver for conversation persistence
- **Circular LLM fallback** — retries with next model on failure
- **HITL** — escalation interrupts graph, supervisor resumes via admin API
- **Structured logging** — structlog with JSON output in production, correlation IDs per request
- **Rate limiting** — sliding window, 60 req/min per tenant per IP
- **Input sanitization** — HTML stripping, length limits, prompt injection detection

---

## Code Style

- Line length: 119 (ruff)
- All I/O is async (httpx.AsyncClient only)
- 300-line file limit
- Google-style docstrings
- `structlog.get_logger()` for all logging

---

## License

MIT
