-- ============================================================================
-- TABLE: subscriptions
-- ============================================================================
-- Stripe subscription tracking for tenant billing. Each tenant can have
-- one active subscription linked to a Stripe customer and price.
--
-- Source: Extracted directly from the live Supabase database.
-- ============================================================================

-- ── DDL ──────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.subscriptions (
    id                      uuid                        NOT NULL DEFAULT gen_random_uuid(),
    tenant_id               uuid                        NOT NULL,
    stripe_customer_id      text,
    stripe_subscription_id  text,
    stripe_price_id         text,
    status                  text                        DEFAULT 'inactive'::text,
    current_period_end      timestamp with time zone,
    created_at              timestamp with time zone     NOT NULL DEFAULT now(),
    updated_at              timestamp with time zone     NOT NULL DEFAULT now(),

    CONSTRAINT subscriptions_pkey PRIMARY KEY (id),
    CONSTRAINT subscriptions_tenant_id_tenants_id_fk
        FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE
);

-- ── ROW LEVEL SECURITY ───────────────────────────────────────────────────────

ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;

-- Users can view subscriptions for their own tenant
CREATE POLICY "Users can view own subscriptions" ON public.subscriptions
    AS PERMISSIVE
    FOR SELECT
    USING ((tenant_id IN (
        SELECT tenants.id FROM tenants
        WHERE (tenants.user_id = auth.uid())
    )));

-- Service role can insert subscriptions (Stripe webhook handler)
CREATE POLICY "Service role can insert subscriptions" ON public.subscriptions
    AS PERMISSIVE
    FOR INSERT
    WITH CHECK (true);

-- Service role can update subscriptions (Stripe webhook handler)
CREATE POLICY "Service role can update subscriptions" ON public.subscriptions
    AS PERMISSIVE
    FOR UPDATE
    USING (true);
