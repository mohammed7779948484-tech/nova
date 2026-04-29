-- ============================================================================
-- TABLE: invitations
-- ============================================================================
-- Invite-only system for adding new members to a tenant. Each invitation
-- is linked to a tenant and has an expiry time.
--
-- Source: Extracted directly from the live Supabase database.
-- ============================================================================

-- ── DDL ──────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.invitations (
    id                  uuid                        NOT NULL DEFAULT gen_random_uuid(),
    tenant_id           uuid                        NOT NULL,
    email               text                        NOT NULL,
    invited_by          uuid                        NOT NULL,
    role                text                        DEFAULT 'member'::text,
    status              text                        DEFAULT 'pending'::text,
    created_at          timestamp with time zone     NOT NULL DEFAULT now(),
    expires_at          timestamp with time zone     NOT NULL,

    CONSTRAINT invitations_pkey PRIMARY KEY (id),
    CONSTRAINT invitations_tenant_id_tenants_id_fk
        FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE
);

-- ── ROW LEVEL SECURITY ───────────────────────────────────────────────────────

ALTER TABLE public.invitations ENABLE ROW LEVEL SECURITY;

-- Users can view invitations for their own tenant
CREATE POLICY "Users can view own invitations" ON public.invitations
    AS PERMISSIVE
    FOR SELECT
    USING ((tenant_id IN (
        SELECT tenants.id FROM tenants
        WHERE (tenants.user_id = auth.uid())
    )));

-- Users can insert invitations for their own tenant
CREATE POLICY "Users can insert own invitations" ON public.invitations
    AS PERMISSIVE
    FOR INSERT
    WITH CHECK ((tenant_id IN (
        SELECT tenants.id FROM tenants
        WHERE (tenants.user_id = auth.uid())
    )));

-- Users can update invitations for their own tenant
CREATE POLICY "Users can update own invitations" ON public.invitations
    AS PERMISSIVE
    FOR UPDATE
    USING ((tenant_id IN (
        SELECT tenants.id FROM tenants
        WHERE (tenants.user_id = auth.uid())
    )));

-- Users can delete invitations for their own tenant
CREATE POLICY "Users can delete own invitations" ON public.invitations
    AS PERMISSIVE
    FOR DELETE
    USING ((tenant_id IN (
        SELECT tenants.id FROM tenants
        WHERE (tenants.user_id = auth.uid())
    )));
