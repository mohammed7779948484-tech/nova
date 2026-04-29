# Research: Nova Backend

**Feature**: 002-nova-backend | **Date**: 2026-04-28

## Research Tasks

### R1: PostgresSaver Integration with Supabase

**Decision**: Use `langgraph.checkpoint.postgres.aio.AsyncPostgresSaver` with
`psycopg_pool.AsyncConnectionPool` connecting to the Supabase PostgreSQL
instance via `DATABASE_URL`.

**Rationale**: The reference template demonstrates this exact pattern
(`reference-template/app/core/langgraph/graph.py:77-113`). Supabase exposes a
standard PostgreSQL connection string. The 4 checkpoint tables
(`checkpoints`, `checkpoint_blobs`, `checkpoint_writes`,
`checkpoint_migrations`) are already provisioned in the live database
(`database/11_checkpoints.sql`). RLS is intentionally disabled on checkpoint
tables — LangGraph manages them via service_role key.

**Alternatives considered**:
- `InMemorySaver`: FORBIDDEN by constitution (Principle I)
- SQLite-backed checkpointer: Not compatible with Supabase PostgreSQL
- Custom checkpoint implementation: Unnecessary — LangGraph's built-in works

### R2: Supabase REST API vs. Direct SQL for Business Queries

**Decision**: Use `httpx.AsyncClient` to call the Supabase REST API
(PostgREST) for all business entity CRUD (tenants, agents, products,
conversations, messages). Use `psycopg` async pool only for LangGraph
checkpointing.

**Rationale**: The existing codebase (`db_repo.py`, `db_tenant_config.py`)
already uses Supabase REST. RLS policies reference `auth.uid()` which is
automatically set by Supabase when using the API with a user JWT. The Python
backend uses the `service_role` key (bypasses RLS) for system operations like
webhook processing. Switching to raw SQL would require reimplementing RLS
enforcement at the application layer.

**Alternatives considered**:
- Raw asyncpg queries: Would bypass RLS enforcement, requiring manual tenant filtering
- SQLAlchemy async: Heavier ORM not needed for PostgREST-backed tables
- Supabase Python SDK: Adds an unnecessary abstraction layer over REST

### R3: WhatsApp Cloud API Integration Pattern

**Decision**: Raw `httpx.AsyncClient` calls to the Meta Graph API v21.0
endpoints. No third-party WhatsApp SDK (pywa is FORBIDDEN by constitution).

**Rationale**: Constitution Principle III mandates raw httpx to maintain full
control over retries, timeouts, and error handling. The endpoints needed are:
- `POST /{phone_number_id}/messages` — send text/media
- `GET /` — webhook verification (challenge-response)
- `POST /` — webhook event reception
- Webhook signature verification via `X-Hub-Signature-256` header

**Alternatives considered**:
- pywa library: FORBIDDEN by constitution
- python-whatsapp-business: Unnecessary abstraction, sync-only

### R4: LLM Circular Fallback Architecture

**Decision**: Adopt the reference template's `LLMService` pattern
(`reference-template/app/services/llm/service.py`) — tenant-configurable
default model, per-model retry with `tenacity`, circular fallback loop across
registered providers.

**Rationale**: The reference implementation handles the exact requirements:
per-model retry (`stop_after_attempt`), exponential backoff with jitter
(`wait_exponential`), and circular model switching. Nova extends this with
per-tenant model configuration (each agent has `llm_provider` and `llm_model`
columns in the `agents` table).

**Alternatives considered**:
- Simple try/except chain: No retry logic, no backoff
- LangChain's built-in fallback: Less control over retry behavior and tenant config

### R5: HITL (Human-in-the-Loop) Implementation

**Decision**: Use LangGraph's native `interrupt()` / `Command(resume=...)`
primitives. The escalation node calls `interrupt()` to pause the graph.
The supervisor endpoint calls `graph.ainvoke(Command(resume=response))` to
resume.

**Rationale**: The reference template demonstrates this pattern
(`reference-template/app/core/langgraph/graph.py:276-314`). Using native
LangGraph primitives ensures checkpoint compatibility and eliminates custom
polling/queue infrastructure. The conversation's lifecycle state is tracked
separately in the `conversations` table (`status` column) alongside the
LangGraph checkpoint state.

**Alternatives considered**:
- External queue (Redis/RabbitMQ): Adds infrastructure complexity, FORBIDDEN by implicit constitution preference for fewer moving parts
- Custom polling endpoint: Fragile, doesn't leverage PostgresSaver state

### R6: Rate Limiting Strategy

**Decision**: In-memory sliding window rate limiter using a dict keyed by
`(client_ip, tenant_id)`. No external Redis dependency for v1.

**Rationale**: At 50 concurrent conversations, in-memory rate limiting is
sufficient. The rate limiter is a FastAPI middleware that reads `X-Forwarded-For`
for proxy-aware IP detection. Per-tenant limits are loaded from the tenant's
subscription plan configuration.

**Alternatives considered**:
- Redis-backed rate limiter: Adds infrastructure dependency not justified at current scale
- slowapi library: Depends on `limits` library which adds complexity for simple sliding window

### R7: Structured Logging Architecture

**Decision**: `structlog` with JSON output in production, console output in
development. Correlation ID injected via middleware into `contextvars`.
Tenant ID and conversation ID added as bound fields.

**Rationale**: Constitution mandates structlog exclusively. The reference template
uses structlog with structured key-value logging. Contextvars-based correlation
ID propagation is the standard pattern for async Python applications.

**Alternatives considered**:
- Python stdlib logging with JSON formatter: Less ergonomic, no built-in context binding
- loguru: Not mentioned in constitution's mandatory stack

## All NEEDS CLARIFICATION Resolved

No unresolved items. All technical decisions have clear rationale backed by
codebase evidence and constitution constraints.
