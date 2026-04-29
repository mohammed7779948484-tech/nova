<!--
=== Sync Impact Report ===
Version change: (new) → 1.0.0
Modified principles: N/A (initial population)
Added sections:
  - Core Principles (I–VII): LangGraph-First, Multi-Tenant Isolation,
    WhatsApp-Primary Channel, Async-Native, Production Resilience,
    Explicit over Implicit, Channel Adapter Pattern
  - Technology Constraints (Section 2)
  - Code Quality Standards (Section 3)
  - Reference Repository (Section 4)
  - Development Workflow (Section 5)
  - PDCA Quality Gates (Section VI — retained from template)
  - Governance
Removed sections: None
Templates requiring updates:
  ✅ plan-template.md — Constitution Check placeholder is generic; aligns
  ✅ spec-template.md — No constitution-specific tokens to update
  ✅ tasks-template.md — Phase structure compatible with PDCA gates
Follow-up TODOs: None
===========================
-->

# Nova Constitution

## Core Principles

### I. LangGraph-First Architecture

ALL conversation logic — state management, history, branching, tool
orchestration, and human-in-the-loop (HITL) — MUST flow through LangGraph.

- No direct LLM calls bypassing the graph. Every model invocation MUST be
  a node inside a LangGraph `StateGraph`.
- LangGraph is the single source of truth for agent behavior. If behavior
  cannot be expressed as a graph node or edge, the design MUST be
  reconsidered.
- `PostgresSaver` (via psycopg async pool) MUST be used for checkpoint
  persistence in all environments. `InMemorySaver` is FORBIDDEN in
  production and staging.
- HITL interrupts and resumptions MUST be handled through LangGraph's
  native interrupt/resume primitives — never via custom polling or
  external queues.

**Rationale**: A single orchestration layer eliminates hidden control flow,
makes conversation logic auditable, and enables deterministic replay of
any conversation state.

### II. Multi-Tenant Isolation

Every database query MUST include `tenant_id` in its WHERE clause or be
protected by Row Level Security (RLS) policies.

- RLS MUST be enforced at the Supabase/PostgreSQL level — application-layer
  filtering alone is NOT sufficient.
- Tenant data MUST never leak across boundaries: not in queries, not in
  caches, not in logs, not in error messages.
- Authentication MUST use `supabase.auth.uid()` exclusively. Third-party
  auth providers (Clerk, NextAuth, Firebase Auth, Auth0) are FORBIDDEN.
- All cache keys MUST be prefixed with `tenant_id`.
- Log entries MUST include `tenant_id` in structured fields but MUST NOT
  include tenant-identifying PII in free-text messages.

**Rationale**: In a multi-tenant SaaS, a single data leak destroys trust
across the entire customer base. Defense in depth (RLS + app-layer checks)
is mandatory.

### III. WhatsApp-Primary Channel Design

WhatsApp Business Cloud API is the PRIMARY customer interaction channel.

- The WhatsApp adapter MUST be the first channel implemented and the
  reference implementation for all subsequent channel adapters.
- All message formats, rate limits, and media handling MUST account for
  WhatsApp constraints first; other channels adapt from there.
- Webhook signature verification MUST be performed on every inbound
  request — unsigned payloads MUST be rejected with HTTP 403.
- All channel adapters MUST follow a unified interface pattern (see
  Principle VII) so new channels (Telegram, Instagram, web chat) can be
  added without modifying core logic.

**Rationale**: Designing for WhatsApp's constraints (24-hour session
windows, template message rules, media size limits) produces a robust
baseline that other channels relax — never the reverse.

### IV. Async-Native by Default

All I/O-bound operations in the request path MUST be async.

- HTTP clients: `httpx.AsyncClient` only — `httpx.Client` and `requests`
  are FORBIDDEN.
- Database connections: async drivers only (`asyncpg`, psycopg async pool).
- External API calls (LLM providers, WhatsApp Cloud API): MUST use async
  HTTP transport.
- Tool execution within LangGraph: MUST be async-compatible.
- Sync code in the async request path is FORBIDDEN — it blocks the entire
  event loop and degrades throughput for all tenants.

**Rationale**: A single synchronous call in an async pipeline can block
the entire event loop, silently degrading performance for every concurrent
request. Python's async ecosystem requires discipline to maintain.

### V. Production Resilience

Every external interaction (LLM calls, database queries, HTTP requests)
MUST have:

- **Explicit timeout**: No unbounded waits. Every I/O call MUST specify a
  timeout value.
- **Retry with exponential backoff**: Use `tenacity` for retry logic. Jitter
  MUST be included to prevent thundering herd.
- **Graceful degradation**: When an external dependency fails beyond retry
  limits, the system MUST return a meaningful fallback (e.g., "I'm
  temporarily unable to help, please try again") rather than crash.
- **LLM circular fallback**: When the primary LLM provider fails, the
  system MUST attempt fallback providers in a configured sequence before
  returning degraded responses.
- **Connection pool lifecycle**: All connection pools (database, HTTP)
  MUST be opened on application startup and closed on application shutdown
  via FastAPI lifespan events. Leaked connections are a production
  incident.

**Rationale**: Transient failures are normal in distributed systems. The
system MUST recover without human intervention. Every crash at 3 AM is
a customer lost.

### VI. Explicit over Implicit

No magic routing, no hidden middleware side effects, no global mutable
state, no implicit behavior.

- Every component MUST declare its dependencies explicitly (constructor
  injection or FastAPI `Depends`).
- Configuration MUST be validated at startup via Pydantic `BaseSettings` —
  fail fast on missing or invalid environment variables.
- No module-level side effects: imports MUST NOT trigger database
  connections, HTTP requests, or state mutations.
- Router registration MUST be explicit — no auto-discovery of endpoints.
- Middleware MUST be registered in a single, auditable location
  (`main.py` or a dedicated `middleware.py`).

**Rationale**: Implicit behavior creates debugging nightmares in
production. If a developer cannot trace a request path by reading the
code linearly, the architecture has failed.

### VII. Channel Adapter Pattern

All external channels MUST implement a unified adapter interface:

- `parse_inbound(raw_payload) → StandardMessage`: Convert
  channel-specific inbound payloads to a standardized internal format.
- `send_outbound(standard_message) → ChannelResponse`: Convert
  standardized outbound messages to channel-specific delivery calls.
- Each adapter MUST live in a dedicated module under `src/channels/`.
- Core business logic (graph nodes, services, tools) MUST NEVER import
  channel-specific modules. The dependency arrow points inward: adapters
  depend on core, never the reverse.
- Adding a new channel MUST NOT require modifying any existing adapter or
  core module.

**Rationale**: Channel proliferation is inevitable in customer service
platforms. The adapter pattern ensures that adding Telegram or Instagram
is an additive operation, not a risky refactor.

## Technology Constraints

### Mandatory Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Language | Python | 3.12+ |
| Web Framework | FastAPI | Latest (async) |
| Database | Supabase PostgreSQL | + Row Level Security |
| ORM | Drizzle ORM | Latest |
| AI Orchestration | LangGraph + LangChain | Latest |
| HTTP Client | httpx (async only) | Latest |
| Logging | structlog | Latest |
| Retry Logic | tenacity | Latest |
| Checkpoint Store | PostgresSaver (psycopg async) | Latest |
| Schema Validation | Pydantic v2 | Latest |
| Environment Config | python-dotenv | Latest |
| Linting/Formatting | ruff | Latest |

### Forbidden Technologies

The following are EXPLICITLY FORBIDDEN in this project:

- **Auth**: Clerk, NextAuth, Firebase Auth, Auth0 — Supabase Auth only
- **WhatsApp SDK**: pywa — raw httpx calls to Cloud API only
- **HTTP**: `requests` library, sync `httpx.Client`
- **Memory**: mem0, InMemorySaver in production/staging
- **State**: Global mutable state, module-level singletons with state
- **Secrets**: Hardcoded secrets, `.env` files committed to version control
- **Logging**: `print()` statements — use `structlog` exclusively
- **Error Handling**: Bare `except:` clauses — always specify exception types

## Code Quality Standards

- **Type hints**: Mandatory on ALL function signatures (parameters and
  return types). `Any` is permitted only with explicit justification
  comment.
- **Pydantic v2 models**: All request/response schemas, configuration
  objects, and domain entities MUST use Pydantic v2 `BaseModel`.
- **Environment variables**: Loaded via `python-dotenv`, validated at
  startup through Pydantic `BaseSettings`. Missing required variables
  MUST cause immediate startup failure with a clear error message.
- **Linting**: All code MUST pass `ruff check` and `ruff format` with
  zero violations before merge.
- **No test-only methods**: Production code MUST NOT contain methods or
  branches that exist solely to support testing. Use dependency injection
  instead.
- **Structured logging**: Every log entry MUST include a correlation ID
  (`request_id` or `conversation_id`) and `tenant_id`. Free-text log
  messages MUST NOT contain PII.
- **Import discipline**: No circular imports. Barrel files (`__init__.py`)
  MUST export only the public API of their package.

## Reference Repository

The `reference-template/` directory contains the
`wassim249/langchain-agent-template` repository. It provides production
patterns that MUST be adopted and adapted:

- **PostgresSaver with degradation**: Checkpoint persistence with graceful
  fallback when the database is temporarily unavailable.
- **HITL interrupt/resume**: LangGraph-native human-in-the-loop patterns
  for escalation and approval workflows.
- **LLM circular fallback with retries**: Multi-provider failover chain
  with configurable retry policies per provider.
- **Parallel tool execution**: Concurrent tool calls within a single
  graph node for latency reduction.
- **Rate limiting**: Per-tenant and per-endpoint rate limiting to prevent
  abuse.
- **Structured logging with correlation ID**: Request-scoped logging
  context propagated through the entire call chain.

**CRITICAL RULE**: We adapt patterns to Nova's architecture — we do NOT
blindly copy code. Every adopted pattern MUST be reviewed for:
1. Multi-tenant compatibility (tenant_id propagation)
2. Async compatibility (no sync calls)
3. Nova's specific error handling requirements (tenacity integration)

## Development Workflow

Development follows an **8-phase plan** (Phases 0–7). Each phase follows
the **PDCA cycle**:

1. **Plan**: Define the work, acceptance criteria, and dependencies.
2. **Do**: Implement following TDD (Red → Green → Refactor).
3. **Check**: Validate against acceptance criteria; run full test suite.
4. **Act**: Retrospective — identify improvements for the next cycle.

### Phase Sequencing

- **Phase 0** (Code Cleanup): MUST complete before any feature work
  begins. Establishes clean baseline.
- **Phases 1–7**: Feature implementation in priority order. Each phase
  MUST pass its PDCA Check gate before the next phase begins.

### Commit Discipline

- Atomic commits: one logical change per commit.
- Commit message format: `type(scope): description` (conventional
  commits).
- No work-in-progress commits on `main` — use feature branches.

## PDCA Quality Gates (NON-NEGOTIABLE)

**7.1 TDD Mandatory**
Every implementation task MUST have a corresponding test task that is
written and verified to FAIL before implementation begins.
Red-Green-Refactor cycle is strictly enforced. No exceptions.

**7.2 Called Shot Protocol**
Before writing ANY test, the developer MUST announce:
1. **Test name**: Descriptive name of the test
2. **Behavior under test**: What observable behavior this verifies
3. **Expected failure**: The exact assertion message or error expected
   when test runs red

If actual failure ≠ expected failure → **STOP** — the test is testing
the wrong thing.

**7.3 Test Ordering (Mandatory Sequence)**
For every feature, tests MUST follow this order:
1. Degenerate/zero case first (empty state, null input, no items)
2. 1–2 exception cases (invalid input, error conditions)
3. Happy path incrementally (Fake It → Obvious Implementation →
   Triangulate)
4. Remaining exception cases
5. NEVER stop with only happy path coverage

**7.4 Completeness Check Gate**
After completing each User Story phase, run PDCA Check:
- All tests passing
- No TODO implementations remaining
- No untested code committed

**7.5 Retrospective**
After full implementation, run PDCA Act retrospective:
- Identify critical moments that impacted success/failure
- Start / Stop / Keep analysis
- ONE thing to change for next cycle

**7.6 Testing Anti-Patterns (Prohibited)**
The following are STRICTLY FORBIDDEN:
- ❌ Choosing mock behavior over system behavior
- ❌ Mocking without understanding (run real implementation first)
- ❌ Incomplete mocks (must reflect full API shape)
- ❌ Test-only methods in production code
- ❌ Tests written after code (if it never failed, it proves nothing)
- ❌ Integration tests as afterthought (add from the start)
- ❌ Vacuous greens (test that passes against a trivial stub)

## Governance

This constitution supersedes all other development practices, coding
conventions, and technical guidelines for the Nova project.

### Amendment Procedure

1. Amendments MUST be proposed as a pull request modifying this file.
2. Each amendment MUST include: rationale, impact assessment, and
   migration plan for existing code.
3. Amendments MUST be reviewed and approved before merge.
4. Constitution version MUST be updated following semantic versioning:
   - **MAJOR**: Principle removed, redefined, or backward-incompatible
     governance change.
   - **MINOR**: New principle or section added, or material expansion
     of existing guidance.
   - **PATCH**: Clarifications, wording improvements, typo fixes.

### Compliance

- All pull requests MUST verify compliance with this constitution.
- Complexity beyond what the constitution permits MUST be justified in
  the PR description with a "Complexity Justification" section.
- Runtime development guidance lives in the project's `AGENTS.md` and
  `.specify/` documentation.

**Version**: 1.0.0 | **Ratified**: 2026-04-28 | **Last Amended**: 2026-04-28
