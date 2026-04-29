-- ============================================================================
-- SHARED FUNCTIONS & EVENT TRIGGERS
-- ============================================================================
-- This file contains shared trigger functions and Supabase event triggers
-- that must be created BEFORE any tables (since tables reference these functions).
--
-- Source: Extracted directly from the live Supabase database.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. update_updated_at_column()
--    Automatically sets updated_at = NOW() on any row update.
--    Used by: tenants, agents (via triggers)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
    RETURNS trigger
    LANGUAGE plpgsql
AS $function$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$function$;

-- ----------------------------------------------------------------------------
-- 2. rls_auto_enable() — Supabase Event Trigger Function
--    Automatically enables RLS on any new table created in the public schema.
--    This is a Supabase built-in security mechanism.
--    DO NOT modify or drop this function.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.rls_auto_enable()
    RETURNS event_trigger
    LANGUAGE plpgsql
    SECURITY DEFINER
    SET search_path TO 'pgcatalog'
AS $function$
DECLARE
  cmd record;
BEGIN
  FOR cmd IN
    SELECT *
    FROM pg_event_trigger_ddl_commands()
    WHERE command_tag IN ('CREATE TABLE', 'CREATE TABLE AS', 'SELECT INTO')
      AND object_type IN ('table','partitioned table')
  LOOP
     IF cmd.schema_name IS NOT NULL
        AND cmd.schema_name IN ('public')
        AND cmd.schema_name NOT IN ('pg_catalog','information_schema')
        AND cmd.schema_name NOT LIKE 'pg_toast%'
        AND cmd.schema_name NOT LIKE 'pg_temp%'
     THEN
      BEGIN
        EXECUTE format('alter table if exists %s enable row level security', cmd.object_identity);
        RAISE LOG 'rls_auto_enable: enabled RLS on %', cmd.object_identity;
      EXCEPTION
        WHEN OTHERS THEN
          RAISE LOG 'rls_auto_enable: failed to enable RLS on %', cmd.object_identity;
      END;
     ELSE
        RAISE LOG 'rls_auto_enable: skip % (either system schema or not in enforced list: %.)', cmd.object_identity, cmd.schema_name;
     END IF;
  END LOOP;
END;
$function$;

-- ----------------------------------------------------------------------------
-- 3. Event Trigger: ensure_rls
--    Fires the rls_auto_enable() function after every DDL command.
--    This is a Supabase built-in event trigger.
--    DO NOT modify or drop this trigger.
-- ----------------------------------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_event_trigger WHERE evtname = 'ensure_rls'
    ) THEN
        CREATE EVENT TRIGGER ensure_rls
            ON ddl_command_end
            EXECUTE FUNCTION public.rls_auto_enable();
    END IF;
END
$$;
