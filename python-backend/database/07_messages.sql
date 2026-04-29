-- ============================================================================
-- TABLE: messages
-- ============================================================================
-- Individual messages within a conversation. Each message has a role
-- (user, assistant, system) and text content.
--
-- Source: Extracted directly from the live Supabase database.
-- ============================================================================

-- ── DDL ──────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.messages (
    id                  uuid                        NOT NULL DEFAULT gen_random_uuid(),
    conversation_id     uuid,
    role                text                        NOT NULL,
    content             text                        NOT NULL,
    created_at          timestamp with time zone     NOT NULL DEFAULT now(),

    CONSTRAINT messages_pkey PRIMARY KEY (id),
    CONSTRAINT messages_conversation_id_conversations_id_fk
        FOREIGN KEY (conversation_id) REFERENCES public.conversations(id) ON DELETE CASCADE
);

-- ── INDEXES ──────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_messages_conversation_id
    ON public.messages USING btree (conversation_id);

CREATE INDEX IF NOT EXISTS idx_messages_created_at
    ON public.messages USING btree (created_at);

-- ── ROW LEVEL SECURITY ───────────────────────────────────────────────────────

ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;

-- Users can view messages for conversations belonging to their own tenant
CREATE POLICY "Users can view own messages" ON public.messages
    AS PERMISSIVE
    FOR SELECT
    USING ((conversation_id IN (
        SELECT conversations.id FROM conversations
        WHERE (conversations.agent_id IN (
            SELECT agents.id FROM agents
            WHERE (agents.tenant_id IN (
                SELECT tenants.id FROM tenants
                WHERE (tenants.user_id = auth.uid())
            ))
        ))
    )));

-- System can insert messages (backend Python service uses service_role key)
CREATE POLICY "System can insert messages" ON public.messages
    AS PERMISSIVE
    FOR INSERT
    WITH CHECK (true);
