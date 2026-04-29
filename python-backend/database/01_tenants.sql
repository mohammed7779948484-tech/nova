-- ============================================================================
-- TABLE: tenants
-- ============================================================================
-- The root entity representing a business/customer in the SaaS platform.
-- Each tenant owns agents, products, invitations, and subscriptions.
--
-- Source: Extracted directly from the live Supabase database.
-- ============================================================================

-- ── DDL ──────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.tenants (
    id                  uuid                        NOT NULL DEFAULT gen_random_uuid(),
    user_id             uuid                        NOT NULL,
    name                text                        NOT NULL,
    stripe_customer_id  text,
    stripe_subscription_id text,
    stripe_price_id     text,
    stripe_subscription_status text,
    stripe_subscription_current_period_end timestamp with time zone,
    created_at          timestamp with time zone     NOT NULL DEFAULT now(),
    updated_at          timestamp with time zone     NOT NULL DEFAULT now(),

    CONSTRAINT tenants_pkey PRIMARY KEY (id)
);

-- ── INDEXES ──────────────────────────────────────────────────────────────────

CREATE UNIQUE INDEX IF NOT EXISTS stripe_customer_id_idx
    ON public.tenants USING btree (stripe_customer_id);

-- ── TRIGGERS ─────────────────────────────────────────────────────────────────

CREATE TRIGGER update_tenants_updated_at
    ON public.tenants
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

-- ── ROW LEVEL SECURITY ───────────────────────────────────────────────────────

ALTER TABLE public.tenants ENABLE ROW LEVEL SECURITY;

-- Service role can insert tenants (signup flow via Supabase Auth)
CREATE POLICY "Service role can insert tenants" ON public.tenants
    AS PERMISSIVE
    FOR INSERT
    WITH CHECK (true);

-- Users can only view their own tenant
CREATE POLICY "Users can view own tenant" ON public.tenants
    AS PERMISSIVE
    FOR SELECT
    USING ((user_id = auth.uid()));

-- Users can only update their own tenant
CREATE POLICY "Users can update own tenant" ON public.tenants
    AS PERMISSIVE
    FOR UPDATE
    USING ((user_id = auth.uid()));

-- Users can only delete their own tenant
CREATE POLICY "Users can delete own tenant" ON public.tenants
    AS PERMISSIVE
    FOR DELETE
    USING ((user_id = auth.uid()));
