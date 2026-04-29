# Feature Specification: Nova Backend — Multi-Tenant AI Customer Service Platform

**Feature Branch**: `002-nova-backend`
**Created**: 2026-04-28
**Status**: Draft
**Input**: User description: "Build the complete backend for Nova — a Multi-Tenant AI Customer Service SaaS Platform"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Codebase Health Baseline (Priority: P1)

Before any feature is added, the existing codebase MUST be stabilized. Seven
known defects currently prevent reliable operation: a messaging channel that
accepts webhooks but silently discards them, a data repository that blocks
concurrent users, a naming collision between two configuration objects, dead
state fields that consume memory, tenant-specific instructions that are
fetched but never injected into agent behavior, a tool whose name promises
media delivery but only returns text, and missing tenant-configuration
caching that forces a network call on every single message.

A developer (internal) opens the project, runs the linter, and confirms
zero violations. They send a test message through the web channel and
verify that the agent responds using tenant-specific instructions stored
in the database. They confirm that the product-search tool completes
without blocking concurrent requests.

**Why this priority**: No feature work is safe until these defects are
resolved. Building on a broken foundation multiplies cost in every
subsequent phase.

**Independent Test**: Run the existing web chat endpoint with a
single tenant, verify the response includes tenant-specific
instructions, and confirm the server handles 10 concurrent requests
without event-loop stalls.

**Acceptance Scenarios**:

1. **Given** a tenant with custom instructions in the database,
   **When** a customer sends a message via the web channel,
   **Then** the AI agent's behavior reflects those stored instructions.

2. **Given** 10 simultaneous product-search requests,
   **When** all requests are in flight,
   **Then** the server responds to all within 5 seconds without
   blocking or timeouts.

3. **Given** the full codebase,
   **When** the linter runs,
   **Then** zero violations are reported and no dead code remains.

4. **Given** two configuration objects that previously shared a name,
   **When** a developer imports either one,
   **Then** there is no ambiguity — each has a distinct, unambiguous
   name.

5. **Given** the agent state definition,
   **When** a conversation runs end-to-end,
   **Then** no unused fields exist in the state that are never
   written to.

---

### User Story 2 — Persistent Conversations (Priority: P1)

A customer sends multiple messages over the course of a day, closes
their browser, and returns the next morning. When they continue the
conversation, the AI agent remembers the full history — including
products discussed, preferences mentioned, and any pending actions.

A business owner opens the admin panel and sees a list of all
conversations for their agent, with timestamps and message counts.
They can click any conversation to read the complete transcript.

**Why this priority**: Without persistent conversations, every
interaction starts from scratch. This is the foundation for customer
trust and useful AI assistance.

**Independent Test**: Send 3 messages through the web channel, restart
the server, send a 4th message, and verify the agent references
information from the first 3 messages.

**Acceptance Scenarios**:

1. **Given** a customer with an ongoing conversation,
   **When** the server restarts,
   **Then** the conversation continues from where it left off, with
   full message history intact.

2. **Given** a business owner viewing their agent's dashboard,
   **When** they request the list of conversations,
   **Then** they receive a paginated list with conversation ID,
   customer identifier, message count, and last-activity timestamp.

3. **Given** a conversation ID,
   **When** a business owner requests that conversation's details,
   **Then** they receive the complete message history in
   chronological order.

4. **Given** the persistent storage becomes temporarily unavailable,
   **When** a customer sends a message,
   **Then** the system continues operating with reduced
   functionality (responses still work but are not persisted) rather
   than crashing.

---

### User Story 3 — Resilient AI Responses (Priority: P1)

When a customer asks a question, the AI responds using the tenant's
configured language model. If that model is temporarily unavailable
(rate-limited, down, or timing out), the system automatically tries
alternative models in a configured sequence. If all models fail, the
customer receives a polite fallback message rather than an error.

Each AI call has a time limit. If the primary model doesn't respond
within the budget, the system moves to the next model without the
customer waiting indefinitely.

**Why this priority**: AI model APIs are unreliable by nature — rate
limits, outages, and latency spikes are daily occurrences. Without
resilience, every outage directly impacts every customer.

**Independent Test**: Configure a tenant with a primary model that
rejects requests (simulated outage) and a secondary model that works.
Send a message and verify the response comes from the secondary model
within the time budget.

**Acceptance Scenarios**:

1. **Given** a tenant with a primary and secondary language model,
   **When** the primary model returns a rate-limit error,
   **Then** the system retries with exponential backoff, then falls
   back to the secondary model transparently.

2. **Given** all configured models are unavailable,
   **When** a customer sends a message,
   **Then** the customer receives a graceful fallback message (e.g.,
   "I'm temporarily unable to help, please try again shortly") and
   the failure is logged with full context.

3. **Given** a model that takes longer than the configured timeout,
   **When** the timeout is reached,
   **Then** the system cancels that attempt and moves to the next
   model without blocking other conversations.

4. **Given** a tenant's configuration is requested,
   **When** it was recently loaded,
   **Then** the cached version is used without an additional network
   call to the database.

---

### User Story 4 — Human Escalation (Priority: P2)

During a conversation, the AI determines it cannot confidently answer
a question or the customer explicitly requests a human agent. The AI
pauses the conversation and notifies a human supervisor. The supervisor
sees the pending conversation in a review queue, reads the full
context, and provides an answer. That answer is delivered back to the
customer and the AI resumes normal operation.

Separately, a supervisor can fully take over a conversation (handoff),
sending messages directly to the customer without AI involvement, and
later return control to the AI.

**Why this priority**: Human escalation is table stakes for customer
service. Without it, businesses cannot trust the AI with real
customers.

**Independent Test**: Trigger an escalation via a test message ("I
want to talk to a human"), verify the conversation appears in the
pending queue, submit a supervisor response, and confirm the customer
receives it.

**Acceptance Scenarios**:

1. **Given** a customer who says "let me talk to a human",
   **When** the AI processes that message,
   **Then** the conversation is paused, the customer receives an
   acknowledgment ("Connecting you with a team member..."), and the
   conversation appears in the supervisor review queue.

2. **Given** a paused conversation in the review queue,
   **When** a supervisor views it,
   **Then** they see the full conversation history, the reason for
   escalation, and the AI's confidence assessment.

3. **Given** a supervisor who submits a response to a paused
   conversation,
   **When** the response is submitted,
   **Then** the customer receives the supervisor's answer and the AI
   resumes handling subsequent messages.

4. **Given** a supervisor who initiates a full handoff,
   **When** they send messages,
   **Then** those messages go directly to the customer without AI
   involvement, and the supervisor can return control to the AI at
   any time.

5. **Given** a paginated review queue,
   **When** a supervisor requests pending conversations for their
   agent,
   **Then** conversations are listed with escalation reason,
   customer identifier, wait time, and last message preview.

---

### User Story 5 — WhatsApp Customer Interactions (Priority: P1)

A customer sends a WhatsApp message to a business's number. The
system receives the message via webhook, identifies which tenant
(business) owns that number, invokes the AI agent with the correct
tenant configuration, and sends the AI's reply back through WhatsApp.

Returning customers are recognized by their phone number and continue
their existing conversation thread. The AI can send text replies,
and product images are delivered as WhatsApp media messages.

While the AI is processing, the customer sees a typing indicator.
Messages from WhatsApp are properly validated (webhook signature
verification) to prevent spoofing.

**Why this priority**: WhatsApp is the primary customer channel.
Without it, the platform has no production-grade customer-facing
interface.

**Independent Test**: Send a WhatsApp message to the configured
number, verify the AI responds with relevant content, send a second
message and verify conversation continuity, and confirm webhook
signature validation rejects unsigned payloads.

**Acceptance Scenarios**:

1. **Given** a WhatsApp number linked to a tenant,
   **When** a customer sends a text message to that number,
   **Then** the system identifies the tenant, processes the message
   through the AI agent, and sends a reply via WhatsApp within 10
   seconds.

2. **Given** a customer who previously messaged the business,
   **When** they send a new message,
   **Then** the AI has access to the full prior conversation and
   responds with context from previous exchanges.

3. **Given** an incoming webhook without a valid signature,
   **When** the system receives it,
   **Then** the request is rejected immediately and logged as a
   security event.

4. **Given** the AI's response includes product information,
   **When** the product has an image,
   **Then** the image is delivered as a WhatsApp media message (not
   as a URL in text).

5. **Given** the system is processing a customer's message,
   **When** the AI is generating a response,
   **Then** the customer sees a typing indicator in WhatsApp.

6. **Given** a WhatsApp phone number that is not linked to any
   tenant,
   **When** a message arrives for that number,
   **Then** the system logs a warning and does not crash.

---

### User Story 6 — Request Protection (Priority: P2)

The system limits how many requests each customer or tenant can make
within a time window. When a customer exceeds the limit, they receive
a polite message asking them to wait. When a tenant exceeds their plan
limit, their admin is notified.

All incoming user text is sanitized before processing to prevent
injection of harmful content into AI prompts or database queries.

**Why this priority**: Without rate limiting, a single abusive
customer can exhaust the AI budget for an entire tenant. Without
sanitization, prompt injection attacks can compromise AI behavior.

**Independent Test**: Send requests exceeding the configured limit
from a single IP and verify the system returns a rate-limit response
after the threshold is crossed.

**Acceptance Scenarios**:

1. **Given** a configured rate limit of N requests per hour,
   **When** a customer exceeds N requests,
   **Then** subsequent requests receive a rate-limit response with
   a retry-after indicator.

2. **Given** a tenant with a subscription plan limit,
   **When** total usage across all their customers approaches the
   limit,
   **Then** the tenant admin receives a notification.

3. **Given** user input containing potentially harmful content,
   **When** the input is processed,
   **Then** it is sanitized before reaching the AI or database.

---

### User Story 7 — Structured Observability (Priority: P2)

Every request flowing through the system generates structured log
entries with a unique correlation ID, tenant identifier, conversation
identifier, and channel. A developer debugging a customer issue can
search logs by correlation ID and trace the complete request path.

In development, logs are human-readable in the console. In production,
logs are machine-readable and written to rotating files.

**Why this priority**: Without structured logging, debugging
multi-tenant issues is a guessing game. Correlation IDs are essential
when multiple tenants share the same infrastructure.

**Independent Test**: Send a request, extract the correlation ID from
the response headers, and search logs for that ID — confirm every
processing step appears with consistent context.

**Acceptance Scenarios**:

1. **Given** any incoming request,
   **When** the system processes it,
   **Then** every log entry includes a unique correlation ID, tenant
   ID, and timestamp.

2. **Given** a developer investigating a specific request,
   **When** they search logs by correlation ID,
   **Then** they see every processing step from receipt to response.

3. **Given** the system is running in production mode,
   **When** logs are written,
   **Then** they are in machine-readable format with daily file
   rotation.

---

### User Story 8 — Production Deployment (Priority: P2)

The system can be packaged and deployed as a container. It starts
up with full health checking — verifying database connectivity and
required environment variables before accepting traffic. It shuts
down gracefully, completing in-flight requests and closing all
connections before exiting.

A health check endpoint reports the system's status, including
database connectivity.

**Why this priority**: Without containerized deployment and health
checks, the system cannot run in any production environment.

**Independent Test**: Build the container, start it, query the health
endpoint and verify database connectivity status, then send SIGTERM
and confirm graceful shutdown completes within 30 seconds.

**Acceptance Scenarios**:

1. **Given** a container build command,
   **When** the build completes,
   **Then** the resulting image starts and responds to health checks
   within 15 seconds.

2. **Given** a required environment variable is missing,
   **When** the system starts,
   **Then** it fails immediately with a clear error message naming
   the missing variable.

3. **Given** the system is running with active conversations,
   **When** a shutdown signal is received,
   **Then** in-flight requests complete, all connections are closed,
   and the process exits cleanly.

4. **Given** the health check endpoint,
   **When** the database is reachable,
   **Then** it returns a healthy status with database connectivity
   confirmed.

5. **Given** the health check endpoint,
   **When** the database is unreachable,
   **Then** it returns a degraded status indicating the specific
   failure.

---

### Edge Cases

- What happens when a WhatsApp webhook delivers a non-text message
  (image, location, voice note, sticker) that the AI cannot process?
  The system MUST acknowledge receipt, log the message type, and
  respond with a polite message explaining it currently supports text.

- What happens when a tenant's subscription expires or is
  deactivated? The system MUST stop processing new messages for that
  tenant and return an appropriate status.

- What happens when two messages arrive for the same conversation
  simultaneously? The system MUST process them sequentially per
  conversation to prevent state corruption.

- What happens when the WhatsApp Cloud API is down but the system
  receives a webhook? The system MUST queue the outbound reply and
  retry delivery, or log the failure for manual follow-up.

- What happens when a conversation's message history grows extremely
  large (1000+ messages)? The system MUST truncate or summarize older
  messages before sending them to the AI to stay within token limits.

- What happens when a supervisor never responds to a paused
  conversation? The system MUST track escalation age and allow
  configuration of auto-timeout behavior.

## Requirements *(mandatory)*

### Functional Requirements

#### Phase 0 — Codebase Stabilization

- **FR-001**: The system MUST NOT contain unused state fields that
  are never written to during normal operation.
- **FR-002**: The system MUST NOT contain dead code — modules,
  classes, or functions that are unreachable from any active code path.
- **FR-003**: All configuration model names MUST be unambiguous —
  no two models may share the same class name within the project.
- **FR-004**: All network I/O operations MUST be non-blocking —
  no synchronous network calls within the asynchronous request path.
- **FR-005**: Tenant-specific instructions stored in the database
  MUST be injected into the AI agent's behavior context.
- **FR-006**: Tool names MUST accurately describe their behavior —
  a tool named "send product image" MUST actually send an image, or
  be renamed to reflect what it actually does.
- **FR-007**: Tenant configuration MUST be cached in memory with a
  configurable time-to-live to avoid redundant database calls.
- **FR-008**: No single source file MUST exceed 300 lines of code
  (excluding migration files). Files approaching this limit MUST
  be split into smaller, cohesive modules.

#### Phase 1 — Conversation Persistence

- **FR-009**: All conversation state MUST be persisted to a durable
  database store, not held only in process memory.
- **FR-010**: Conversations MUST survive server restarts without
  data loss.
- **FR-011**: The system MUST provide an endpoint to list all
  conversations for a given agent, with pagination support.
- **FR-012**: The system MUST provide an endpoint to retrieve a
  single conversation's complete message history.
- **FR-013**: Database connection pools MUST be opened on application
  startup and closed on application shutdown.
- **FR-014**: If the persistent store is temporarily unavailable, the
  system MUST continue operating in a degraded mode rather than
  crashing.

#### Phase 2 — AI Resilience & Context

- **FR-015**: AI model calls MUST include retry logic with
  exponential backoff and jitter.
- **FR-016**: When the primary model fails beyond retry limits, the
  system MUST automatically attempt fallback models in a configured
  sequence.
- **FR-017**: All AI model calls MUST have an explicit timeout. No
  unbounded waits.
- **FR-018**: When all models are exhausted, the system MUST return
  a graceful fallback message to the customer.
- **FR-019**: Each AI interaction MUST have access to a conversation
  context summary that includes: customer preferences, discussed
  products, and pending actions.
- **FR-020**: Tenant configuration (agent personality, rules, model
  settings) MUST be loaded from the database and cached.
- **FR-021**: The system MUST support multiple AI providers (at
  minimum: OpenAI, Anthropic, Google) with per-tenant configuration.

#### Phase 3 — Human-in-the-Loop

- **FR-022**: The AI MUST be able to pause a conversation and request
  human supervisor input.
- **FR-023**: The system MUST provide an endpoint listing conversations
  waiting for human review, with pagination.
- **FR-024**: The system MUST provide an endpoint for a supervisor to
  submit a response that resumes the paused conversation.
- **FR-025**: The system MUST support full conversation handoff to a
  human supervisor, bypassing the AI entirely.
- **FR-026**: The system MUST provide an endpoint for a supervisor to
  send messages directly to a customer during handoff.
- **FR-027**: Paused conversations MUST include metadata about why
  escalation occurred (customer request, low AI confidence, or
  complex issue).
- **FR-057**: Every conversation MUST have an explicit lifecycle
  state drawn from exactly this set: `active` (AI is handling),
  `escalated` (waiting for business owner input), `handed_off`
  (owner controls messaging directly), `resolved` (conversation
  completed). Allowed transitions: `active ↔ escalated`,
  `escalated → handed_off`, `handed_off → active`,
  `any → resolved`.

#### Phase 4 — WhatsApp Channel

- **FR-028**: The system MUST receive and process WhatsApp webhooks
  containing customer messages.
- **FR-029**: Incoming webhooks MUST be validated via signature
  verification. Unsigned payloads MUST be rejected.
- **FR-030**: The system MUST map incoming WhatsApp phone numbers to
  the correct tenant using stored phone-number-to-agent associations.
- **FR-031**: Each WhatsApp customer MUST be mapped to a persistent
  conversation thread based on their phone number.
- **FR-032**: AI responses MUST be delivered back to customers via the
  WhatsApp messaging API.
- **FR-033**: The system MUST send a typing indicator while processing
  a customer's message.
- **FR-034**: The system MUST support sending media messages (images)
  through WhatsApp when the AI's response includes product visuals.
- **FR-035**: The WhatsApp channel MUST conform to the same adapter
  interface used by other channels, ensuring core business logic
  remains channel-agnostic.

#### Phase 5 — Rate Limiting & Input Safety

- **FR-036**: The system MUST enforce configurable rate limits per
  client IP address.
- **FR-037**: Rate limiting MUST support per-tenant limits based on
  subscription plan.
- **FR-038**: Rate-limited requests MUST receive an appropriate
  response with a retry-after indicator.
- **FR-039**: All user-provided text MUST be sanitized before
  processing to prevent prompt injection and data corruption.
- **FR-040**: The system MUST correctly identify client IP addresses
  when operating behind a reverse proxy.

#### Phase 6 — Structured Logging

- **FR-041**: Every log entry MUST include a unique correlation ID
  that traces a request through the entire processing pipeline.
- **FR-042**: Every log entry MUST include the tenant identifier and
  conversation identifier when available.
- **FR-043**: Log output MUST be configurable between human-readable
  (development) and machine-readable (production) formats.
- **FR-044**: Production log files MUST rotate daily to prevent
  unbounded disk usage.
- **FR-045**: Log entries MUST NOT contain personally identifiable
  information in free-text fields.

#### Phase 7 — Production Readiness

- **FR-046**: The system MUST be deployable as a container.
- **FR-047**: The system MUST validate all required environment
  variables at startup and fail immediately with a clear error if
  any are missing.
- **FR-048**: The system MUST provide a health check endpoint that
  reports service status and database connectivity.
- **FR-049**: The system MUST shut down gracefully — completing
  in-flight requests and closing all connections.
- **FR-050**: The container image MUST use a multi-stage build to
  minimize production image size.

#### Cross-Cutting

- **FR-051**: Every database query MUST include tenant isolation.
  Data from one tenant MUST never be accessible to another.
- **FR-052**: User authentication is handled by the Next.js frontend
  via Supabase Auth. The Python backend is an internal service that
  trusts the frontend as the authentication gatekeeper. Third-party
  authentication providers are forbidden at the frontend layer.
- **FR-053**: All channels (WhatsApp, web, future Telegram/Instagram)
  MUST implement a unified adapter interface. Core business logic
  MUST NOT import channel-specific modules.
- **FR-054**: All AI conversation orchestration MUST flow through a
  single graph-based orchestration system. No direct AI model calls
  bypassing the orchestration graph.
- **FR-055**: All external tools invoked by the AI MUST execute
  concurrently when independent, not sequentially.
- **FR-056**: The Python backend is an internal AI core service.
  Admin and supervisor endpoints (conversation listing, pending
  reviews, resume, handoff, human-message) are called exclusively
  by the Next.js frontend, which is the authentication gatekeeper.
  The backend MUST NOT implement its own user authentication
  validation on these endpoints in v1. Tenant isolation is enforced
  by passing `tenant_id` from the frontend on every request.
- **FR-058**: There is a single operator role in v1. The business
  owner IS the supervisor — they are the same person. No
  fine-grained role separation exists. All admin endpoints serve
  this single owner persona.
- **FR-059**: Messages are retained indefinitely in v1. No
  automatic purge or retention policy is implemented.

### Key Entities

- **Tenant**: A subscribing business. Has a unique slug, business
  name, subscription plan, and configuration. Owns agents,
  products, and conversations.

- **Agent**: An AI assistant belonging to a tenant. Has a name,
  role, personality, rules, language, model configuration, and
  custom instructions. A tenant may have multiple agents.

- **Conversation**: An ongoing dialogue between a customer and an
  agent. Tied to a specific channel and customer identifier.
  Contains messages and state checkpoints. Has an explicit lifecycle
  state: `active`, `escalated`, `handed_off`, or `resolved`.

- **Message**: A single utterance in a conversation. Has a sender
  role (customer, AI, supervisor), content, timestamp, and optional
  media attachments.

- **Product**: A catalog item belonging to an agent. Has a name,
  description, price, currency, category, image, tags, and
  promotion status. Searchable by keyword.

- **Instruction**: A custom directive for an agent, stored in the
  database. Active instructions are injected into the AI's behavior
  context.

- **WhatsApp Connection**: A mapping between a WhatsApp phone number
  and an agent. Used to route incoming webhooks to the correct
  tenant.

- **Escalation**: A paused conversation waiting for human
  supervisor input. Includes the reason for escalation, timestamp,
  and the supervisor's response when provided.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Customers can have multi-turn conversations that
  persist across server restarts and continue with full history
  recall.

- **SC-002**: When the primary AI model is unavailable, the system
  automatically falls back to alternative models and responds to the
  customer within 30 seconds.

- **SC-003**: A WhatsApp customer receives an AI-generated reply
  within 10 seconds of sending a message under normal load.

- **SC-004**: Conversations requiring human escalation appear in
  the supervisor queue within 2 seconds of the AI's escalation
  decision.

- **SC-005**: The system handles 50 concurrent conversations across
  multiple tenants without performance degradation (measured by
  response time remaining under 10 seconds).

- **SC-006**: Zero data leakage between tenants — any conversation,
  product, or configuration query for tenant A returns exclusively
  tenant A's data.

- **SC-007**: The system starts and passes health checks within 15
  seconds of container launch.

- **SC-008**: Graceful shutdown completes within 30 seconds,
  including in-flight request completion and connection cleanup.

- **SC-009**: Every request can be traced end-to-end using a single
  correlation ID across all log entries.

- **SC-010**: The codebase passes all linting checks with zero
  violations, and no source file exceeds 300 lines.

## Assumptions

- Businesses (tenants) are pre-configured by platform administrators.
  Self-service tenant onboarding is out of scope for this version.

- The database (Supabase PostgreSQL with Row Level Security) is
  already provisioned with the required schema (11 tables). Schema
  creation is not part of this specification.

- WhatsApp Business Cloud API access is pre-configured (phone number
  verified, access token provisioned). WhatsApp business verification
  is out of scope.

- The reference template repository provides proven patterns that
  will be adapted — not copied verbatim — to fit Nova's multi-tenant
  architecture.

- Only text-based customer messages are fully supported in v1.
  Non-text messages (images, voice, location) are acknowledged but
  not processed by the AI.

- Telegram and Instagram channel adapters are out of scope for this
  version. The adapter interface is designed for future extension.

- There is no frontend dashboard in this specification. API endpoints
  for supervisor review and tenant management are provided for
  integration by a separate frontend. The Next.js frontend is the
  authentication gatekeeper — the Python backend is an internal
  service that trusts the frontend to authenticate users.

- The AI's knowledge base comes from the tenant's product catalog
  stored in the database. External knowledge ingestion (PDF upload,
  website scraping) is out of scope for this version.

- Messages are retained indefinitely in v1. No automatic purge or
  retention policy is implemented.

- WhatsApp 24-hour session window handling and template messages
  for re-engagement are out of scope for v1.

## Clarifications

### Session 2026-04-28

- Q: How are admin/supervisor endpoints protected from unauthorized access? → A: They are not — the Python backend is an internal AI core service. The Next.js frontend handles all authentication and acts as the gatekeeper. No auth validation on backend admin endpoints in v1.
- Q: What are the explicit conversation lifecycle states and allowed transitions? → A: 4 states: `active`, `escalated`, `handed_off`, `resolved`. Transitions: active↔escalated, escalated→handed_off, handed_off→active, any→resolved.
- Q: Are "business owner" and "supervisor" the same person or separate roles? → A: Same person. The business owner IS the supervisor. No separate permissions in v1.
- Q: Is there a message retention/purge policy? → A: No. Messages retained indefinitely in v1.
- Q: Does the spec need to handle WhatsApp 24-hour session windows and template messages? → A: Out of scope for v1.
