# Backend Migration Documentation

## Supabase DB Integration — Changelog & Architecture

**Date:** 2025-01-28  
**Author:** AI Development Agent  
**Scope:** Migrate tenant configuration and product data from local YAML/JSON files to Supabase PostgreSQL database

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture Before & After](#architecture-before--after)
3. [Files Modified](#files-modified)
4. [Files Created](#files-created)
5. [Bug Fixes & Improvements](#bug-fixes--improvements)
6. [Configuration](#configuration)
7. [Database Schema](#database-schema)
8. [API Reference](#api-reference)
9. [Testing](#testing)
10. [Migration Guide](#migration-guide)

---

## Overview

The backend was originally designed to read tenant configuration from local YAML files (`tenants/*/config.yaml`) and product catalogs from JSON files (`tenants/*/products.json`). This worked for development but limited the system to pre-configured tenants only.

The migration replaces file-based data loading with **Supabase PostgREST API** queries, enabling:

- **Dynamic tenant creation** — New tenants can be added via database inserts without code changes or file deployments
- **Centralized data** — All tenant configs and products stored in a single PostgreSQL database
- **Multi-language support** — Arabic, Russian, and English search with proper tokenization
- **Production readiness** — Proper lifecycle management, error handling, logging, and caching

---

## Architecture Before & After

### Before (YAML-based)

```
Request → Router → tenant_config.get_tenant(slug)
                        ↓
                   Read YAML file from disk
                   Read products.json from disk
                        ↓
                   Return TenantConfig
```

### After (Supabase DB-based)

```
Request → Router → tenant_config.async_get_tenant(slug)
                        ↓
                   DBTenantConfig.get_agent_by_slug(slug)
                        ↓
                   httpx → Supabase PostgREST API
                        ↓
                   Convert AgentConfig → TenantConfig
                        ↓
                   (Fallback to YAML if DB fails)
```

---

## Files Modified

### 1. `src/app.py` — FastAPI Application Entry Point

**Changes:**
- Added `lifespan` async context manager for proper resource lifecycle management
- Startup: Initialize logging configuration
- Shutdown: Close `httpx.AsyncClient` (DBTenantConfig) and `httpx.Client` (DBProductRepository)
- This follows the [FastAPI lifespan best practice](https://fastapi.tiangolo.com/advanced/events/) for managing HTTP clients

**Why:** httpx clients must be explicitly closed to avoid resource leaks. The FastAPI lifespan pattern is the recommended way to manage these resources.

### 2. `src/config/db_tenant_config.py` — Supabase DB Reader for Tenant Config

**Changes:**
- Added `load_dotenv()` call — ensures `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` are loaded even if this module is imported directly
- Added `aclose()` method — allows proper shutdown of the httpx.AsyncClient
- Added validation — raises `ValueError` if SUPABASE_URL or SUPABASE_SERVICE_KEY are not set
- Added logging — debug/info/warning messages for troubleshooting
- Fixed default values — `llm_provider` default changed from `"google"` to `"openai"`, `llm_model` default from `"gemini-2.0-flash"` to `"LongCat-Flash-Chat"` to match the actual production model
- Added `list_all_agents()` method — queries all active agents from the `agents` table for the `/api/tenants` endpoint

**Key Methods:**
| Method | Purpose |
|--------|---------|
| `get_agent_by_slug(slug)` | Find agent by tenant_slug (e.g. "flower_shop") |
| `get_agent_config(agent_id)` | Load full agent config by UUID |
| `get_agent_by_whatsapp_phone(phone)` | Route WhatsApp messages to correct agent |
| `list_all_agents()` | List all active agents for /api/tenants |
| `agent_config_to_tenant_config()` | Convert DB format to TenantConfig format |
| `aclose()` | Close httpx client (call on shutdown) |

### 3. `src/config/tenant_config.py` — Tenant Configuration Loader

**Changes:**
- Added `async_get_tenant(tenant_id)` — async DB-first tenant loader with YAML fallback
- Added `async_list_tenants()` — async DB-first tenant lister with YAML fallback
- Added proper error handling — wraps DB calls in try/except, falls back to YAML on any exception (network error, auth error, etc.)
- Added logging — warnings when falling back, debug info on success
- Fixed fallback logic in `async_list_tenants()` — if DB fails, returns YAML-based list in the same format

**Fallback Strategy:**
```
DB query succeeds → Use DB result
DB query returns None → Fall back to YAML
DB query throws exception → Fall back to YAML (with warning log)
```

### 4. `src/repositories/db_repo.py` — Supabase DB Product Repository

**Changes:**
- **NEW FILE** — Replaces `json_repo.py` as the primary product repository
- Added Arabic text support in `_tokenize()` — regex now includes `\u0600-\u06FF` (Arabic Unicode block)
- Added Arabic stemming in `_stem()` — strips common Arabic prefixes (ال، وال، بال) and suffixes (ها، هم، ي، ان، ين، ة)
- Added `_slug_to_agent_id` cache — avoids extra HTTP round trips for slug→agent_id lookups
- Added `close()` method — allows proper shutdown of the sync httpx.Client
- Added validation — raises `ValueError` if SUPABASE_URL or SUPABASE_SERVICE_KEY are not set
- Added safe price parsing — handles ValueError/TypeError when converting decimal strings to float
- Added logging — debug/info/warning messages for troubleshooting
- Changed to lazy singleton pattern — `_db_repo` is created on first call to `get_repository()`, not at module import time

**Cache Strategy:**
- Products are cached per tenant_slug with 5-minute TTL
- Agent ID lookups are cached for the repository's lifetime
- `invalidate_cache(tenant_id)` clears both product cache and agent ID cache

**Multi-language Search:**
| Language | Tokenization | Stemming |
|----------|-------------|----------|
| English | `[a-zA-Z0-9]+` | Strip suffixes (-ing, -tion, -es, -ed, -er, -s) |
| Russian | `[а-яА-ЯёЁ0-9]+` | Strip suffixes (-ами, -ов, -ый, -и, -а, etc.) |
| Arabic | `[\u0600-\u06FF]+` | Strip prefixes (ال-, وال-) and suffixes (-ها, -ون, -ة, etc.) |

### 5. `src/nodes/assistant.py` — LLM Assistant Node

**Changes:**
- Changed `_build_system_prompt()` from async to sync — it no longer needs to be async since it receives the already-loaded TenantConfig
- Fixed double DB call — previously called `async_get_tenant()` twice (once in `assistant_node`, once in `_build_system_prompt`). Now loads once and passes the config.
- Changed import from `get_tenant` to `async_get_tenant`
- Added logging — debug messages for tracing

### 6. `src/channels/web/router.py` — Web Channel Router

**Changes:**
- Changed imports from `get_tenant, list_tenants` to `async_list_tenants, async_get_tenant`
- `/api/tenants` endpoint now delegates to `async_list_tenants()` directly
- `/api/chat` endpoint now uses DB-loaded tenant config (via assistant_node)

### 7. `src/repositories/__init__.py` — Repository Exports

**Changes:**
- Changed `get_repository` import from `json_repo` to `db_repo`

---

## Files Created

| File | Purpose |
|------|---------|
| `src/repositories/db_repo.py` | Supabase DB-backed product repository |
| `src/config/db_tenant_config.py` | Supabase DB reader for tenant config (existed, enhanced) |

---

## Bug Fixes & Improvements

### Critical Fixes

| # | Issue | Fix |
|---|-------|-----|
| 1 | `load_dotenv()` missing in `db_tenant_config.py` — env vars could be empty if module imported directly | Added `load_dotenv()` at module level |
| 2 | Arabic tokenization missing — `_tokenize()` regex only matched Latin and Cyrillic | Added `\u0600-\u06FF` (Arabic Unicode block) to regex, added Arabic stemming rules |
| 3 | Double DB call per chat message — `async_get_tenant()` called twice | Changed `_build_system_prompt()` to receive TenantConfig instead of tenant_id, load config once in `assistant_node()` |
| 4 | No error handling in `async_get_tenant()` — DB errors propagated instead of falling back | Wrapped DB calls in try/except with YAML fallback |
| 5 | httpx clients never closed — resource leak on shutdown | Added `aclose()`/`close()` methods, FastAPI lifespan manages cleanup |

### Improvements

| # | Improvement | Details |
|---|------------|---------|
| 6 | Lazy singleton for DBProductRepository | Created on first `get_repository()` call instead of at import time |
| 7 | Agent ID cache in DBProductRepository | Avoids extra HTTP round trip for slug→agent_id lookups |
| 8 | Logging added | All DB operations log at appropriate levels (debug/info/warning) |
| 9 | Environment variable validation | Raises clear `ValueError` if SUPABASE_URL or SUPABASE_SERVICE_KEY not set |
| 10 | Safe price parsing | Handles invalid decimal values gracefully |
| 11 | Default model values corrected | Changed from "google/gemini-2.0-flash" to "openai/LongCat-Flash-Chat" to match production |

---

## Configuration

### Environment Variables (`.env`)

```env
# ═══ LLM Configuration ═══
OPENAI_API_KEY=ak_xxxxx                    # LongCat OpenAI-compatible key
OPENAI_API_BASE=https://api.longcat.chat/openai

# ═══ Supabase (Database) ═══
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJhbGci...              # Public anon key
SUPABASE_SERVICE_KEY=eyJhbGci...           # Service role key (bypasses RLS)

# ═══ Tenant Configuration ═══
TENANTS_DIR=./tenants                      # YAML fallback directory
```

### Important Security Notes

- **SUPABASE_SERVICE_KEY** bypasses Row Level Security (RLS). Never expose it in client-side code.
- **SUPABASE_ANON_KEY** respects RLS policies. Safe for client-side use.
- Both keys are read from `.env` via `dotenv` — never hardcode them.

---

## Database Schema

The backend uses 7 tables in Supabase:

```
tenants
  └── agents (tenant_id → tenants.id)
        ├── agent_instructions (agent_id → agents.id)
        ├── agent_products (agent_id → agents.id)
        └── whatsapp_connections (agent_id → agents.id)
  └── conversations (agent_id → agents.id)
        └── messages (conversation_id → conversations.id)
```

### Key Columns for Agent Lookup

| Table | Column | Purpose |
|-------|--------|---------|
| `agents` | `tenant_slug` | Human-readable ID (e.g. "flower_shop") — used for lookup |
| `agents` | `is_active` | Soft delete — only active agents are loaded |
| `agents` | `rules` | JSONB array of behavioral rules |
| `agents` | `llm_provider` | LLM provider name (e.g. "openai") |
| `agents` | `llm_model` | Model name (e.g. "LongCat-Flash-Chat") |
| `agent_products` | `product_slug` | Human-readable product ID |
| `agent_products` | `is_available` | Soft delete for products |
| `agent_products` | `is_promoted` | Flag for promotional items |
| `agent_products` | `tags` | JSONB array of search tags (multi-language) |

---

## API Reference

### GET /api/tenants

Returns all active tenants/agents from the database.

**Response:**
```json
[
  {
    "id": "flower_shop",
    "business_name": "Розы & Букеты",
    "agent_name": "Айгуль",
    "agent_role": "Flower Consultant",
    "language": "ru",
    "provider": "openai/LongCat-Flash-Chat"
  }
]
```

### POST /api/chat

Send a message to an agent and receive a streaming SSE response.

**Request:**
```json
{
  "tenant_id": "flower_shop",
  "message": "Какие розы у вас есть?",
  "thread_id": null,
  "image_url": null
}
```

**Response:** Server-Sent Events (SSE) stream with events:
- `meta` — Thread ID for conversation continuity
- `node_start` / `node_end` — Graph node execution
- `token` — Streaming text tokens
- `llm_end` — Usage stats and tool calls
- `tool_start` / `tool_end` — Tool execution
- `error` — Error messages
- `done` — Stream complete

---

## Testing

### Test Results Summary

| Test | Result |
|------|--------|
| GET /api/tenants — 4 tenants from DB | ✅ Pass |
| Chat: tech_store (English) | ✅ Pass |
| Chat: flower_shop (Russian) | ✅ Pass |
| Chat: restaurant_test (Arabic) | ✅ Pass |
| Chat: coffee_shop (DB-only, no YAML) | ✅ Pass |
| Arabic product search: "برجر" → برجر كلاسيك | ✅ Pass |
| Arabic product search: "شاورما" → شاورما دجاج | ✅ Pass |
| Error handling: nonexistent tenant → YAML fallback | ✅ Pass |
| Error handling: DB failure → YAML fallback | ✅ Pass |
| httpx client cleanup on shutdown | ✅ Pass |

### Adding a New Tenant (DB-only)

1. Create a seed script (see `drizzle/seed-new-tenant.ts`)
2. Insert into `tenants` table
3. Insert into `agents` table with `tenant_slug`
4. Insert into `agent_products` table
5. Insert into `agent_instructions` table (optional)
6. The tenant appears immediately — no server restart needed (after cache TTL)

---

## Migration Guide

### From YAML to DB

1. **Keep YAML files as fallback** — The system falls back to YAML if DB is unavailable
2. **Match tenant_slug to YAML folder name** — e.g., `flower_shop` slug → `tenants/flower_shop/`
3. **Tags must include multiple languages** — Products should have tags in both the native language AND English for best search results
4. **Cache TTL is 5 minutes** — New products/tenants may take up to 5 minutes to appear. Call `invalidate_cache()` for immediate refresh.

### Running the Server

```bash
cd backend/langgraph-sales-agent
source venv/bin/activate
python -m uvicorn src.app:app --host 0.0.0.0 --port 8000
```

### Seeding the Database

```bash
# From the Next.js project root
npx tsx drizzle/seed.ts           # Original 3 tenants
npx tsx drizzle/seed-new-tenant.ts # Coffee shop (DB-only test)
```
