# Data Model: Nova Backend

**Feature**: 002-nova-backend | **Date**: 2026-04-28

## Existing Schema (11 tables — already provisioned in Supabase)

All tables below exist in the live database. The Python backend reads/writes
via Supabase REST API (service_role key) for business entities and via
`psycopg` async pool for LangGraph checkpoints.

### Core Business Entities

#### tenants
| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | uuid | PK, default gen_random_uuid() | |
| user_id | uuid | NOT NULL | FK to Supabase auth.users |
| name | text | NOT NULL | Business display name |
| stripe_customer_id | text | UNIQUE INDEX | Billing integration |
| stripe_subscription_id | text | | |
| stripe_price_id | text | | |
| stripe_subscription_status | text | | |
| stripe_subscription_current_period_end | timestamptz | | |
| created_at | timestamptz | NOT NULL, default now() | |
| updated_at | timestamptz | NOT NULL, default now() | Auto-updated via trigger |

**RLS**: user_id = auth.uid() for SELECT/UPDATE/DELETE. INSERT via service role.

#### agents
| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | uuid | PK | |
| tenant_id | uuid | FK → tenants.id ON DELETE CASCADE | |
| tenant_slug | text | UNIQUE | Used by backend for tenant resolution |
| business_name | text | NOT NULL | |
| language | text | default 'en' | |
| name | text | NOT NULL | Agent display name |
| role | text | default 'customer_service' | |
| personality | text | | System prompt personality |
| rules | jsonb | default '[]' | Agent behavior rules |
| llm_provider | text | default 'google' | openai, anthropic, google |
| llm_model | text | default 'gemini-2.0-flash' | |
| llm_temperature | real | default 0.7 | |
| llm_max_tokens | integer | default 1024 | |
| image_search | boolean | default true | Feature flag |
| promotions | boolean | default true | Feature flag |
| upsell | boolean | default true | Feature flag |
| is_active | boolean | default true | |
| display_name | text | | |
| avatar_emoji | text | | |
| greeting_message | text | | |
| created_at | timestamptz | NOT NULL | |
| updated_at | timestamptz | NOT NULL | Auto-updated via trigger |

**RLS**: tenant_id IN (user's tenants) for all operations.

#### agent_products
| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | uuid | PK | |
| agent_id | uuid | FK → agents.id ON DELETE CASCADE | |
| product_slug | text | NOT NULL | |
| name | text | NOT NULL | |
| description | text | | |
| price | numeric(10,2) | | |
| currency | text | default 'USD' | |
| category | text | | Indexed |
| image_url | text | | |
| tags | jsonb | default '[]' | |
| is_promoted | boolean | default false | Indexed |
| promotion_text | text | | |
| is_available | boolean | default true | |
| created_at | timestamptz | NOT NULL | |

#### agent_instructions
| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | uuid | PK | |
| agent_id | uuid | FK → agents.id ON DELETE CASCADE | |
| instruction | text | NOT NULL | Custom directive text |
| is_active | boolean | default true | Only active ones injected |
| created_at | timestamptz | NOT NULL | |

#### whatsapp_connections
| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | uuid | PK | |
| agent_id | uuid | FK → agents.id ON DELETE CASCADE | |
| phone_number_id | text | NOT NULL | Meta phone number ID |
| access_token | text | NOT NULL | Meta API access token |
| verify_token | text | NOT NULL | Webhook verification token |
| is_active | boolean | default true | |
| connected_at | timestamptz | default now() | |

#### conversations
| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | uuid | PK | |
| agent_id | uuid | FK → agents.id ON DELETE CASCADE | |
| session_id | text | NOT NULL, indexed | Thread ID for LangGraph |
| channel | text | default 'whatsapp' | |
| customer_phone | text | | Customer identifier |
| started_at | timestamptz | NOT NULL, default now() | |
| last_message_at | timestamptz | NOT NULL, default now() | |
| status | text | default 'active' | **Lifecycle: active, escalated, handed_off, resolved** |

**Schema change needed**: The `status` column needs a CHECK constraint for the
4 allowed values. This should be added as a migration in Phase 3.

#### messages
| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | uuid | PK | |
| conversation_id | uuid | FK → conversations.id ON DELETE CASCADE | |
| role | text | NOT NULL | customer, assistant, supervisor |
| content | text | NOT NULL | |
| created_at | timestamptz | NOT NULL, default now() | Indexed |

### LangGraph Checkpoint Tables (auto-managed)

- `checkpoints` — State snapshots (thread_id + checkpoint_ns + checkpoint_id)
- `checkpoint_blobs` — Large binary state values
- `checkpoint_writes` — Pending writes for recovery
- `checkpoint_migrations` — Schema version tracking

**RLS**: DISABLED — managed by LangGraph via service_role key.

## State Transitions

### Conversation Lifecycle

```
                  ┌──────────────┐
                  │    active    │
                  │  (AI chat)   │
                  └──────┬───────┘
                         │
              ┌──────────┼──────────┐
              │          │          │
              ▼          │          ▼
     ┌────────────┐      │   ┌───────────┐
     │  escalated  │      │   │  resolved  │
     │(wait owner) │      │   │  (done)    │
     └──────┬──────┘      │   └───────────┘
            │             │         ▲
            ▼             │         │
     ┌────────────┐       │         │
     │ handed_off  │──────┘─────────┘
     │(owner chat) │
     └────────────┘
```

**Transitions**:
- `active ↔ escalated` — AI requests help / owner resolves and returns to AI
- `escalated → handed_off` — Owner takes over direct messaging
- `handed_off → active` — Owner returns control to AI
- `any → resolved` — Conversation completed

## Validation Rules

| Entity | Field | Rule |
|--------|-------|------|
| Tenant | name | NOT NULL, non-empty |
| Agent | tenant_slug | UNIQUE across all agents |
| Agent | llm_provider | Must be one of: openai, anthropic, google |
| Agent | llm_temperature | 0.0 ≤ value ≤ 2.0 |
| Conversation | status | Must be one of: active, escalated, handed_off, resolved |
| Conversation | session_id | NOT NULL, used as LangGraph thread_id |
| Message | role | Must be one of: customer, assistant, supervisor |
| WhatsApp Connection | phone_number_id | NOT NULL, Meta phone number ID format |

## Pydantic Models (new — to be created)

```python
# src/models/enums.py
class ConversationStatus(str, Enum):
    ACTIVE = "active"
    ESCALATED = "escalated"
    HANDED_OFF = "handed_off"
    RESOLVED = "resolved"

class MessageRole(str, Enum):
    CUSTOMER = "customer"
    ASSISTANT = "assistant"
    SUPERVISOR = "supervisor"

class EscalationReason(str, Enum):
    CUSTOMER_REQUEST = "customer_request"
    LOW_CONFIDENCE = "low_confidence"
    COMPLEX_ISSUE = "complex_issue"
```
