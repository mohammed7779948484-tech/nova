-- ============================================================================
-- TABLE: agent_instructions
-- ============================================================================
-- Custom instructions/prompts that can be added to an agent to modify its
-- behavior. Multiple instructions can be active for a single agent.
--
-- Source: Extracted directly from the live Supabase database.
-- ============================================================================

-- ── DDL ──────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.agent_instructions (
    id                  uuid                        NOT NULL DEFAULT gen_random_uuid(),
    agent_id            uuid,
    instruction         text                        NOT NULL,
    is_active           boolean                     DEFAULT true,
    created_at          timestamp with time zone     NOT NULL DEFAULT now(),

    CONSTRAINT agent_instructions_pkey PRIMARY KEY (id),
    CONSTRAINT agent_instructions_agent_id_agents_id_fk
        FOREIGN KEY (agent_id) REFERENCES public.agents(id) ON DELETE CASCADE
);

-- ── INDEXES ──────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_agent_instructions_agent_id
    ON public.agent_instructions USING btree (agent_id);

-- ── ROW LEVEL SECURITY ───────────────────────────────────────────────────────

ALTER TABLE public.agent_instructions ENABLE ROW LEVEL SECURITY;

-- Users can view instructions for agents in their own tenant
CREATE POLICY "Users can view own instructions" ON public.agent_instructions
    AS PERMISSIVE
    FOR SELECT
    USING ((agent_id IN (
        SELECT agents.id FROM agents
        WHERE (agents.tenant_id IN (
            SELECT tenants.id FROM tenants
            WHERE (tenants.user_id = auth.uid())
        ))
    )));

-- Users can insert instructions for agents in their own tenant
CREATE POLICY "Users can insert own instructions" ON public.agent_instructions
    AS PERMISSIVE
    FOR INSERT
    WITH CHECK ((agent_id IN (
        SELECT agents.id FROM agents
        WHERE (agents.tenant_id IN (
            SELECT tenants.id FROM tenants
            WHERE (tenants.user_id = auth.uid())
        ))
    )));

-- Users can update instructions for agents in their own tenant
CREATE POLICY "Users can update own instructions" ON public.agent_instructions
    AS PERMISSIVE
    FOR UPDATE
    USING ((agent_id IN (
        SELECT agents.id FROM agents
        WHERE (agents.tenant_id IN (
            SELECT tenants.id FROM tenants
            WHERE (tenants.user_id = auth.uid())
        ))
    )));

-- Users can delete instructions for agents in their own tenant
CREATE POLICY "Users can delete own instructions" ON public.agent_instructions
    AS PERMISSIVE
    FOR DELETE
    USING ((agent_id IN (
        SELECT agents.id FROM agents
        WHERE (agents.tenant_id IN (
            SELECT tenants.id FROM tenants
            WHERE (tenants.user_id = auth.uid())
        ))
    )));
