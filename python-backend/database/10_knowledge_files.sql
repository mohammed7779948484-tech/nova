-- ============================================================================
-- TABLE: knowledge_files
-- ============================================================================
-- Uploaded knowledge files associated with an agent for RAG (Retrieval
-- Augmented Generation). Files are stored with metadata for processing.
--
-- Source: Extracted directly from the live Supabase database.
-- ============================================================================

-- ── DDL ──────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.knowledge_files (
    id                  uuid                        NOT NULL DEFAULT gen_random_uuid(),
    agent_id            uuid                        NOT NULL,
    file_name           text                        NOT NULL,
    file_path           text                        NOT NULL,
    file_type           text                        NOT NULL,
    file_size           integer                     NOT NULL,
    uploaded_at         timestamp with time zone     NOT NULL DEFAULT now(),

    CONSTRAINT knowledge_files_pkey PRIMARY KEY (id),
    CONSTRAINT knowledge_files_agent_id_agents_id_fk
        FOREIGN KEY (agent_id) REFERENCES public.agents(id) ON DELETE CASCADE
);

-- ── ROW LEVEL SECURITY ───────────────────────────────────────────────────────

ALTER TABLE public.knowledge_files ENABLE ROW LEVEL SECURITY;

-- Users can view knowledge files for agents in their own tenant
CREATE POLICY "Users can view own knowledge files" ON public.knowledge_files
    AS PERMISSIVE
    FOR SELECT
    USING ((agent_id IN (
        SELECT agents.id FROM agents
        WHERE (agents.tenant_id IN (
            SELECT tenants.id FROM tenants
            WHERE (tenants.user_id = auth.uid())
        ))
    )));

-- Users can insert knowledge files for agents in their own tenant
CREATE POLICY "Users can insert own knowledge files" ON public.knowledge_files
    AS PERMISSIVE
    FOR INSERT
    WITH CHECK ((agent_id IN (
        SELECT agents.id FROM agents
        WHERE (agents.tenant_id IN (
            SELECT tenants.id FROM tenants
            WHERE (tenants.user_id = auth.uid())
        ))
    )));

-- Users can delete knowledge files for agents in their own tenant
CREATE POLICY "Users can delete own knowledge files" ON public.knowledge_files
    AS PERMISSIVE
    FOR DELETE
    USING ((agent_id IN (
        SELECT agents.id FROM agents
        WHERE (agents.tenant_id IN (
            SELECT tenants.id FROM tenants
            WHERE (tenants.user_id = auth.uid())
        ))
    )));
