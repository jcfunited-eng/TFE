-- =============================================================================
-- Migration: D1_add_s_n_to_runtime_decisions_history
-- Gate:      D1 — s_n Emission in Production Snapshot
-- Purpose:   Add s_n (structural surprise, raw L2 norm ||nu_core - z_n||)
--            as an explicit top-level column on runtime_decisions_history,
--            mirroring the value already emitted in snapshot_row_json.
--
-- Reference: TAO_FINANCIAL_ENGINE_PORTFOLIO_MANAGER_DESIGN_DOCUMENT (d1d9fd3),
--            §8 (Data Pipeline) and §12 (Gate D1).
--            Source formula: quarantine_historical_kernel.py line 376,
--            uf_mdg_snapshot.py compute_cognitive_scalars().
--
-- Rollback:  migrations/D1_rollback.sql
-- Test:      tools/d1_bit_equivalence_test.py  (must PASS before prod deploy)
--
-- Run:       psql $DATABASE_URL -f D1_add_s_n_to_runtime_decisions_history.sql
-- Idempotent: yes (ADD COLUMN IF NOT EXISTS + WHERE s_n IS NULL)
-- =============================================================================

-- Step 1: add the column (no-op if already present)
ALTER TABLE runtime_decisions_history
  ADD COLUMN IF NOT EXISTS s_n DOUBLE PRECISION;

-- Step 2: backfill from snapshot_row_json where the key is already present
UPDATE runtime_decisions_history
   SET s_n = (snapshot_row_json->>'s_n')::DOUBLE PRECISION
 WHERE snapshot_row_json ? 's_n'
   AND s_n IS NULL;

-- Step 3: add an index for range scans on s_n (Wave 1 band queries)
CREATE INDEX IF NOT EXISTS idx_rdh_s_n
  ON runtime_decisions_history (s_n)
  WHERE s_n IS NOT NULL;

-- Verify
DO $$
DECLARE
  col_exists boolean;
BEGIN
  SELECT EXISTS(
    SELECT 1 FROM information_schema.columns
     WHERE table_name='runtime_decisions_history' AND column_name='s_n'
  ) INTO col_exists;
  ASSERT col_exists, 'D1 migration failed: s_n column not found';
  RAISE NOTICE 'D1 migration OK: s_n column present on runtime_decisions_history';
END $$;
