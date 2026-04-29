-- ============================================================================
-- TABLE: whatsapp_connections
-- ============================================================================
-- WhatsApp Business API connection credentials for an agent.
-- Each agent can have one active WhatsApp connection.
--
-- Source: Extracted directly from the live Supabase database.
-- ============================================================================

-- ── DDL ──────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.whatsapp_connections (
    id                  uuid                        NOT NULL DEFAULT gen_random_uuid(),
    agent_id            uuid,
    phone_number_id     text                        NOT NULL,
    access_token        text                        NOT NULL,
    verify_token        text                        NOT NULL,
    is_active           boolean                     DEFAULT true,
    connected_at        timestamp with time zone     DEFAULT now(),

    CONSTRAINT whatsapp_connections_pkey PRIMARY KEY (id),
    CONSTRAINT whatsapp_connections_agent_id_agents_id_fk
        FOREIGN KEY (agent_id) REFERENCES public.agents(id) ON DELETE CASCADE
);

-- ── INDEXES ──────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_whatsapp_connections_agent_id
    ON public.whatsapp_connections USING btree (agent_id);

-- ── ROW LEVEL SECURITY ───────────────────────────────────────────────────────

ALTER TABLE public.whatsapp_connections ENABLE ROW LEVEL SECURITY;

-- Users can view WhatsApp connections for agents in their own tenant
CREATE POLICY "Users can view own whatsapp" ON public.whatsapp_connections
    AS PERMISSIVE
    FOR SELECT
    USING ((agent_id IN (
        SELECT agents.id FROM agents
        WHERE (agents.tenant_id IN (
            SELECT tenants.id FROM tenants
            WHERE (tenants.user_id = auth.uid())
        ))
    )));

-- Users can insert WhatsApp connections for agents in their own tenant
CREATE POLICY "Users can insert own whatsapp" ON public.whatsapp_connections
    AS PERMISSIVE
    FOR INSERT
    WITH CHECK ((agent_id IN (
        SELECT agents.id FROM agents
        WHERE (agents.tenant_id IN (
            SELECT tenants.id FROM tenants
            WHERE (tenants.user_id = auth.uid())
        ))
    )));

-- Users can update WhatsApp connections for agents in their own tenant
CREATE POLICY "Users can update own whatsapp" ON public.whatsapp_connections
    AS PERMISSIVE
    FOR UPDATE
    USING ((agent_id IN (
        SELECT agents.id FROM agents
        WHERE (agents.tenant_id IN (
            SELECT tenants.id FROM tenants
            WHERE (tenants.user_id = auth.uid())
        ))
    )));

-- Users can delete WhatsApp connections for agents in their own tenant
CREATE POLICY "Users can delete own whatsapp" ON public.whatsapp_connections
    AS PERMISSIVE
    FOR DELETE
    USING ((agent_id IN (
        SELECT agents.id FROM agents
        WHERE (agents.tenant_id IN (
            SELECT tenants.id FROM tenants
            WHERE (tenants.user_id = auth.uid())
        ))
    )));
