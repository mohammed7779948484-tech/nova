-- ============================================================================
-- TABLE: conversations
-- ============================================================================
-- Tracks conversations between customers and AI agents across all channels.
-- Each conversation is linked to an agent and identified by a session_id.
-- The status field tracks the conversation lifecycle.
--
-- Source: Extracted directly from the live Supabase database.
-- ============================================================================

-- ── DDL ──────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.conversations (
    id                  uuid                        NOT NULL DEFAULT gen_random_uuid(),
    agent_id            uuid,
    session_id          text                        NOT NULL,
    channel             text                        DEFAULT 'whatsapp'::text,
    customer_phone      text,
    started_at          timestamp with time zone     NOT NULL DEFAULT now(),
    last_message_at     timestamp with time zone     NOT NULL DEFAULT now(),
    status              text                        DEFAULT 'active'::text,

    CONSTRAINT conversations_pkey PRIMARY KEY (id),
    CONSTRAINT conversations_agent_id_agents_id_fk
        FOREIGN KEY (agent_id) REFERENCES public.agents(id) ON DELETE CASCADE
);

-- ── INDEXES ──────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_conversations_agent_id
    ON public.conversations USING btree (agent_id);

CREATE INDEX IF NOT EXISTS idx_conversations_session_id
    ON public.conversations USING btree (session_id);

-- ── ROW LEVEL SECURITY ───────────────────────────────────────────────────────

ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;

-- Users can view conversations for agents in their own tenant
CREATE POLICY "Users can view own conversations" ON public.conversations
    AS PERMISSIVE
    FOR SELECT
    USING ((agent_id IN (
        SELECT agents.id FROM agents
        WHERE (agents.tenant_id IN (
            SELECT tenants.id FROM tenants
            WHERE (tenants.user_id = auth.uid())
        ))
    )));

-- System can insert conversations (backend Python service uses service_role key)
CREATE POLICY "System can insert conversations" ON public.conversations
    AS PERMISSIVE
    FOR INSERT
    WITH CHECK (true);

-- System can update conversations (backend Python service uses service_role key)
CREATE POLICY "System can update conversations" ON public.conversations
    AS PERMISSIVE
    FOR UPDATE
    USING (true);
