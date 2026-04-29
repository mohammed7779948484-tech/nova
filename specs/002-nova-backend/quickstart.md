# Quickstart: Nova Backend

**Feature**: 002-nova-backend | **Date**: 2026-04-28

## Prerequisites

- Python 3.12+
- A Supabase project with the 11-table schema provisioned
- WhatsApp Business Cloud API access (phone number verified)
- At least one LLM API key (OpenAI, Anthropic, or Google)

## Environment Setup

```bash
# Clone and enter the project
cd python-backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or: .venv\Scripts\activate  # Windows

# Install dependencies
pip install -e ".[dev]"

# Copy environment template
cp .env.example .env
```

## Required Environment Variables

```env
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=eyJ...  # service_role key (bypasses RLS)
DATABASE_URL=postgresql://postgres:password@db.your-project.supabase.co:5432/postgres

# LLM Providers (at least one required)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AI...

# WhatsApp (Phase 4+)
WHATSAPP_APP_SECRET=your_app_secret  # For webhook signature verification

# Application
ENVIRONMENT=development  # development | staging | production
LOG_FORMAT=console  # console | json
```

## Running Locally

```bash
# Start the development server
uvicorn src.app:app --host 0.0.0.0 --port 8000 --reload

# Health check
curl http://localhost:8000/health

# Send a test message (web channel)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!", "tenant_slug": "flower-shop", "session_id": "test-1"}'
```

## Running Tests

```bash
# All tests
pytest

# Unit tests only
pytest tests/unit/

# Integration tests (requires Supabase connection)
pytest tests/integration/

# With coverage
pytest --cov=src --cov-report=term-missing
```

## Docker

```bash
# Build
docker build -t nova-backend .

# Run
docker run -p 8000:8000 --env-file .env nova-backend
```

## Phase-by-Phase Verification

| Phase | What to Test | Command |
|-------|-------------|---------|
| 0 | Linter passes, web chat works | `ruff check src/ && pytest tests/unit/` |
| 1 | Conversations persist across restarts | `pytest tests/integration/test_persistence.py` |
| 2 | AI responds with fallback on provider failure | `pytest tests/integration/test_llm_fallback.py` |
| 3 | Escalation pauses/resumes conversation | `pytest tests/integration/test_hitl.py` |
| 4 | WhatsApp webhook round-trip | `pytest tests/integration/test_whatsapp.py` |
| 5 | Rate limiter blocks excessive requests | `pytest tests/unit/test_rate_limiter.py` |
| 6 | Logs include correlation ID + tenant ID | `pytest tests/unit/test_logging.py` |
| 7 | Container builds and starts clean | `docker build . && docker run --rm nova-backend python -c "from src.app import app"` |
