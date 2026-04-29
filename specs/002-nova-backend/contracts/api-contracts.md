# API Contracts: Nova Backend

**Feature**: 002-nova-backend | **Date**: 2026-04-28

The Python backend is an **internal service** — all endpoints are called by
the Next.js frontend (authentication gatekeeper) or by external webhooks
(WhatsApp). No user-facing authentication on admin endpoints.

## Health & System

### GET /health
Health check endpoint for monitoring and load balancer probes.

**Response** `200 OK`:
```json
{
  "status": "ok",
  "service": "nova-backend",
  "database": "connected",
  "uptime_seconds": 3600
}
```

**Response** `503 Service Unavailable`:
```json
{
  "status": "degraded",
  "service": "nova-backend",
  "database": "disconnected"
}
```

## Conversation Management (called by frontend)

### GET /api/conversations?agent_id={uuid}&page={int}&limit={int}
List conversations for an agent with pagination.

**Query Parameters**:
- `agent_id` (required): UUID of the agent
- `page` (optional, default 1): Page number
- `limit` (optional, default 20, max 100): Items per page
- `status` (optional): Filter by lifecycle status

**Response** `200 OK`:
```json
{
  "conversations": [
    {
      "id": "uuid",
      "session_id": "string",
      "channel": "whatsapp",
      "customer_phone": "+1234567890",
      "status": "active",
      "message_count": 15,
      "started_at": "2026-04-28T10:00:00Z",
      "last_message_at": "2026-04-28T14:30:00Z"
    }
  ],
  "total": 42,
  "page": 1,
  "limit": 20
}
```

### GET /api/conversations/{conversation_id}/messages
Retrieve complete message history for a conversation.

**Response** `200 OK`:
```json
{
  "conversation_id": "uuid",
  "messages": [
    {
      "id": "uuid",
      "role": "customer",
      "content": "Hello, I need help with...",
      "created_at": "2026-04-28T10:00:00Z"
    },
    {
      "id": "uuid",
      "role": "assistant",
      "content": "I'd be happy to help!",
      "created_at": "2026-04-28T10:00:02Z"
    }
  ]
}
```

## HITL / Supervisor Endpoints (called by frontend)

### GET /api/escalations?agent_id={uuid}&page={int}&limit={int}
List conversations waiting for supervisor input.

**Query Parameters**:
- `agent_id` (required): UUID of the agent
- `page` (optional, default 1): Page number
- `limit` (optional, default 20): Items per page

**Response** `200 OK`:
```json
{
  "escalations": [
    {
      "conversation_id": "uuid",
      "session_id": "string",
      "status": "escalated",
      "reason": "customer_request",
      "customer_phone": "+1234567890",
      "escalated_at": "2026-04-28T14:00:00Z",
      "last_message": "I want to speak with a human"
    }
  ],
  "total": 3,
  "page": 1,
  "limit": 20
}
```

### POST /api/escalations/{conversation_id}/resume
Supervisor provides input that resumes AI processing.

**Request Body**:
```json
{
  "supervisor_response": "The customer is eligible for a 20% discount"
}
```

**Response** `200 OK`:
```json
{
  "conversation_id": "uuid",
  "status": "active",
  "ai_response": "Great news! I've confirmed you're eligible for a 20% discount..."
}
```

### POST /api/escalations/{conversation_id}/handoff
Supervisor takes full control of the conversation.

**Request Body**:
```json
{
  "reason": "Complex billing issue requiring manual resolution"
}
```

**Response** `200 OK`:
```json
{
  "conversation_id": "uuid",
  "status": "handed_off"
}
```

### POST /api/conversations/{conversation_id}/message
Supervisor sends a message directly to the customer during handoff.

**Request Body**:
```json
{
  "content": "Hi, I'm the business owner. Let me help you with this..."
}
```

**Response** `200 OK`:
```json
{
  "message_id": "uuid",
  "delivered": true
}
```

### POST /api/conversations/{conversation_id}/resolve
Mark a conversation as resolved.

**Response** `200 OK`:
```json
{
  "conversation_id": "uuid",
  "status": "resolved"
}
```

## WhatsApp Webhooks (called by Meta)

### GET /api/webhooks/whatsapp
Webhook verification (challenge-response).

**Query Parameters**:
- `hub.mode` (required): Must be "subscribe"
- `hub.verify_token` (required): Must match stored verify_token
- `hub.challenge` (required): Echo back on success

**Response** `200 OK`: Raw challenge string
**Response** `403 Forbidden`: Token mismatch

### POST /api/webhooks/whatsapp
Receive inbound WhatsApp messages.

**Headers**:
- `X-Hub-Signature-256` (required): HMAC-SHA256 signature of request body

**Request Body**: Meta webhook payload (varies by event type)

**Response** `200 OK`: Always acknowledge receipt immediately
**Response** `403 Forbidden`: Invalid signature

## Web Chat (existing, extended)

### POST /chat
Process a web chat message through the AI agent.

**Request Body**:
```json
{
  "message": "What products do you have?",
  "tenant_slug": "flower-shop",
  "session_id": "web-session-abc123"
}
```

**Response** `200 OK`:
```json
{
  "response": "We have several beautiful arrangements...",
  "session_id": "web-session-abc123"
}
```

## Error Responses (all endpoints)

### 400 Bad Request
```json
{
  "detail": "Invalid request: {specific validation error}"
}
```

### 404 Not Found
```json
{
  "detail": "Conversation not found"
}
```

### 429 Too Many Requests
```json
{
  "detail": "Rate limit exceeded",
  "retry_after": 60
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal error",
  "correlation_id": "req-abc123"
}
```
