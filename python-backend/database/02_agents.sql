-- ============================================================================
-- TABLE: agents
-- ============================================================================
-- AI sales agents belonging to a tenant. Each agent has its own LLM config,
-- personality, and feature flags. The tenant_slug is the unique identifier
-- used by the Python backend to resolve tenant context.
--
-- Source: Extracted directly from the live Supabase database.
-- ============================================================================

-- ── DDL ──────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.agents (
    id                  uuid                        NOT NULL DEFAULT gen_random_uuid(),
    tenant_id           uuid,
    tenant_slug         text                        NOT NULL,
    business_name       text                        NOT NULL,
    language            text                        DEFAULT 'en'::text,
    name                text                        NOT NULL,
    role                text                        DEFAULT 'customer_service'::text,
    personality         text,
    rules               jsonb                       DEFAULT '[]'::jsonb,
    llm_provider        text                        DEFAULT 'google'::text,
    llm_model           text                        DEFAULT 'gemini-2.0-flash'::text,
    llm_temperature     real                        DEFAULT 0.7,
    llm_max_tokens      integer                     DEFAULT 1024,
    image_search        boolean                     DEFAULT true,
    promotions          boolean                     DEFAULT true,
    upsell              boolean                     DEFAULT true,
    is_active           boolean                     DEFAULT true,
    display_name        text,
    avatar_emoji        text,
    greeting_message    text,
    created_at          timestamp with time zone     NOT NULL DEFAULT now(),
    updated_at          timestamp with time zone     NOT NULL DEFAULT now(),

    CONSTRAINT agents_pkey PRIMARY KEY (id),
    CONSTRAINT agents_tenant_slug_unique UNIQUE (tenant_slug),
    CONSTRAINT agents_tenant_id_tenants_id_fk
        FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE
);

-- ── INDEXES ──────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_agents_tenant_id
    ON public.agents USING btree (tenant_id);

CREATE INDEX IF NOT EXISTS idx_agents_tenant_slug
    ON public.agents USING btree (tenant_slug);

-- ── TRIGGERS ─────────────────────────────────────────────────────────────────

CREATE TRIGGER update_agents_updated_at
    ON public.agents
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

-- ── ROW LEVEL SECURITY ───────────────────────────────────────────────────────

ALTER TABLE public.agents ENABLE ROW LEVEL SECURITY;

-- Users can view agents belonging to their own tenant
CREATE POLICY "Users can view own agents" ON public.agents
    AS PERMISSIVE
    FOR SELECT
    USING ((tenant_id IN (
        SELECT tenants.id FROM tenants
        WHERE (tenants.user_id = auth.uid())
    )));

-- Users can insert agents for their own tenant
CREATE POLICY "Users can insert own agents" ON public.agents
    AS PERMISSIVE
    FOR INSERT
    WITH CHECK ((tenant_id IN (
        SELECT tenants.id FROM tenants
        WHERE (tenants.user_id = auth.uid())
    )));

-- Users can update agents belonging to their own tenant
CREATE POLICY "Users can update own agents" ON public.agents
    AS PERMISSIVE
    FOR UPDATE
    USING ((tenant_id IN (
        SELECT tenants.id FROM tenants
        WHERE (tenants.user_id = auth.uid())
    )));

-- Users can delete agents belonging to their own tenant
CREATE POLICY "Users can delete own agents" ON public.agents
    AS PERMISSIVE
    FOR DELETE
    USING ((tenant_id IN (
        SELECT tenants.id FROM tenants
        WHERE (tenants.user_id = auth.uid())
    )));
