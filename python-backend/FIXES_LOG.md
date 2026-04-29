# Fixes Log — PHASE 1

## [Step 3.1] src/channels/web/router.py — Fixed UTF-8 encoding
- **File**: `src/channels/web/router.py` line 31
- **Change**: `(WEB_DIR / "index.html").read_text()` → `(WEB_DIR / "index.html").read_text(encoding="utf-8")`
- **Why**: On Windows, `Path.read_text()` defaults to `cp1252` encoding which cannot decode UTF-8 characters in `index.html` (Cyrillic, special chars). This caused HTTP 500 errors when accessing the root page.

## [Step 2.2] src/config/llm_provider.py — Added Google Gemini support
- **File**: `src/config/llm_provider.py`
- **Change**: Added `google` provider branch using `langchain_google_genai.ChatGoogleGenerativeAI`
- **Why**: User provided a Google Gemini API key. The original code only supported OpenAI and Anthropic.

## [Step 2.2] src/config/tenant_config.py — Updated provider comment
- **File**: `src/config/tenant_config.py` line 36
- **Change**: Updated `LLMConfig.provider` comment from `"openai" or "anthropic"` to `"openai", "anthropic", or "google"`
- **Why**: Documentation update to reflect the new Google provider.

## [Step 4.5] tenants/flower_shop/config.yaml — Changed LLM provider
- **File**: `tenants/flower_shop/config.yaml`
- **Change**: `llm.provider: "openai"` → `"google"`, `llm.model: "gpt-4o-mini"` → `"gemini-2.0-flash"`
- **Why**: User provided a Gemini API key, not an OpenAI key.

## [Step 4.5] tenants/tech_store/config.yaml — Changed LLM provider
- **File**: `tenants/tech_store/config.yaml`
- **Change**: `llm.provider: "openai"` → `"google"`, `llm.model: "gpt-4o-mini"` → `"gemini-2.0-flash"`
- **Why**: User provided a Gemini API key, not an OpenAI key.

## [Step 2.6] .env — Created with all documented variables
- **File**: `.env`
- **Change**: Created from `.env.example`, added `GOOGLE_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `WHATSAPP_TOKEN`, `WHATSAPP_VERIFY_TOKEN`
- **Why**: Needed environment variables for Google Gemini and future Supabase/WhatsApp integration.

## [Step 5] pyproject.toml — Added new dependencies
- **File**: `pyproject.toml`
- **Change**: Added `langchain-google-genai>=4.0` and `httpx>=0.26`
- **Why**: Required for Google Gemini support and Supabase REST API calls.

## [Step 5] src/config/db_tenant_config.py — Created Supabase DB loader
- **File**: `src/config/db_tenant_config.py` (NEW)
- **Change**: Created module that uses `httpx` to call Supabase PostgREST API directly
- **Why**: Replaces the `supabase-py` package dependency (which requires C++ build tools via pyiceberg) with lightweight `httpx` REST calls. Both the YAML system and DB system work in parallel.

## [LLM Retest] .env — Configured LongChat OpenAI-compatible provider
- **File**: `.env`
- **Change**: Set `OPENAI_API_KEY=ak_2NW1Uk94A07b7R04sd08Z6KV0Xw3Q`, `OPENAI_API_BASE=https://api.longcat.chat/openai`
- **Why**: Original Gemini API key had zero quota (429 RESOURCE_EXHAUSTED). Switched to user-provided LongChat endpoint.

## [LLM Retest] src/config/llm_provider.py — Added custom base URL support
- **File**: `src/config/llm_provider.py`
- **Change**: OpenAI provider now reads `OPENAI_API_BASE` env var and passes `base_url` to `ChatOpenAI`. Also reads `OPENAI_API_KEY` explicitly.
- **Why**: Required to support OpenAI-compatible endpoints like LongChat.

## [LLM Retest] src/config/settings.py — Added openai_api_key and openai_api_base
- **File**: `src/config/settings.py`
- **Change**: Added `openai_api_key` and `openai_api_base` fields to `Settings` model
- **Why**: Making these settings explicit rather than relying only on env var auto-detection.

## [LLM Retest] tenants/*.yaml — Switched to openai/LongCat-Flash-Chat
- **Files**: `tenants/flower_shop/config.yaml`, `tenants/tech_store/config.yaml`, `tenants/restaurant_test/config.yaml`
- **Change**: All tenants switched from `provider: "google"` / `model: "gemini-2.0-flash"` to `provider: "openai"` / `model: "LongCat-Flash-Chat"`
- **Why**: Using the LongChat OpenAI-compatible endpoint which has available quota.