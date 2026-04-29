-- ============================================================================
-- TABLE: agent_products
-- ============================================================================
-- Products associated with an AI agent. Each agent can have multiple products
-- that are searchable via the LangGraph tools (search_products, search_by_image, etc.).
--
-- Source: Extracted directly from the live Supabase database.
-- ============================================================================

-- ── DDL ──────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.agent_products (
    id                  uuid                        NOT NULL DEFAULT gen_random_uuid(),
    agent_id            uuid,
    product_slug        text                        NOT NULL,
    name                text                        NOT NULL,
    description         text,
    price               numeric(10,2),
    currency            text                        DEFAULT 'USD'::text,
    category            text,
    image_url           text,
    tags                jsonb                       DEFAULT '[]'::jsonb,
    is_promoted         boolean                     DEFAULT false,
    promotion_text      text,
    is_available        boolean                     DEFAULT true,
    created_at          timestamp with time zone     NOT NULL DEFAULT now(),

    CONSTRAINT agent_products_pkey PRIMARY KEY (id),
    CONSTRAINT agent_products_agent_id_agents_id_fk
        FOREIGN KEY (agent_id) REFERENCES public.agents(id) ON DELETE CASCADE
);

-- ── INDEXES ──────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_agent_products_agent_id
    ON public.agent_products USING btree (agent_id);

CREATE INDEX IF NOT EXISTS idx_agent_products_category
    ON public.agent_products USING btree (category);

CREATE INDEX IF NOT EXISTS idx_agent_products_is_promoted
    ON public.agent_products USING btree (is_promoted);

-- ── ROW LEVEL SECURITY ───────────────────────────────────────────────────────

ALTER TABLE public.agent_products ENABLE ROW LEVEL SECURITY;

-- Users can view products for agents in their own tenant
CREATE POLICY "Users can view own products" ON public.agent_products
    AS PERMISSIVE
    FOR SELECT
    USING ((agent_id IN (
        SELECT agents.id FROM agents
        WHERE (agents.tenant_id IN (
            SELECT tenants.id FROM tenants
            WHERE (tenants.user_id = auth.uid())
        ))
    )));

-- Users can insert products for agents in their own tenant
CREATE POLICY "Users can insert own products" ON public.agent_products
    AS PERMISSIVE
    FOR INSERT
    WITH CHECK ((agent_id IN (
        SELECT agents.id FROM agents
        WHERE (agents.tenant_id IN (
            SELECT tenants.id FROM tenants
            WHERE (tenants.user_id = auth.uid())
        ))
    )));

-- Users can update products for agents in their own tenant
CREATE POLICY "Users can update own products" ON public.agent_products
    AS PERMISSIVE
    FOR UPDATE
    USING ((agent_id IN (
        SELECT agents.id FROM agents
        WHERE (agents.tenant_id IN (
            SELECT tenants.id FROM tenants
            WHERE (tenants.user_id = auth.uid())
        ))
    )));

-- Users can delete products for agents in their own tenant
CREATE POLICY "Users can delete products in own agents" ON public.agent_products
    AS PERMISSIVE
    FOR DELETE
    USING ((agent_id IN (
        SELECT agents.id FROM agents
        WHERE (agents.tenant_id IN (
            SELECT tenants.id FROM tenants
            WHERE (tenants.user_id = auth.uid())
        ))
    )));
