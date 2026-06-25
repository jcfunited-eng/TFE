-- =============================================================================
-- Rollback: D1_rollback.sql
-- Reverses: D1_add_s_n_to_runtime_decisions_history.sql
-- Warning:  Drops s_n data from all rows. Only run if D1 must be reverted.
--           Requires explicit confirmation that s_n backfill data is expendable.
-- =============================================================================

DROP INDEX IF EXISTS idx_rdh_s_n;
ALTER TABLE runtime_decisions_history DROP COLUMN IF EXISTS s_n;

DO $$
BEGIN
  RAISE NOTICE 'D1 rollback OK: s_n column removed from runtime_decisions_history';
END $$;
