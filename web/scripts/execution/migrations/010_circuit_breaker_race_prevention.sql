-- =============================================================================
-- Migration: 010_circuit_breaker_race_prevention
-- Purpose:   Prevent duplicate active circuit breaker rows from concurrent
--            runCircuitBreaker invocations racing between the "already active"
--            check and the INSERT. Partial unique index enforces at-most-one
--            uncleared row at the DB level. Second concurrent INSERT fails
--            with 23505 unique_violation, handled gracefully in code.
-- Run:       psql $DATABASE_URL -f 010_circuit_breaker_race_prevention.sql
-- =============================================================================

BEGIN;

-- If any prior duplicates exist, keep the earliest triggered row and clear the rest.
-- No-op in a clean state.
UPDATE pee1_circuit_breaker
   SET cleared_at = NOW(),
       trigger_reason = COALESCE(trigger_reason, '') || ' [auto-cleared by 010: duplicate active row]'
 WHERE id IN (
     SELECT id FROM (
         SELECT id, ROW_NUMBER() OVER (
             PARTITION BY (cleared_at IS NULL)
             ORDER BY triggered_at ASC
         ) AS rn
         FROM pee1_circuit_breaker
         WHERE cleared_at IS NULL
     ) t WHERE t.rn > 1
 );

-- Partial unique index: at most one row where cleared_at IS NULL.
-- Uses constant expression so all uncleared rows collide with each other.
CREATE UNIQUE INDEX IF NOT EXISTS idx_pee1_cb_at_most_one_active
    ON pee1_circuit_breaker ((1))
    WHERE cleared_at IS NULL;

INSERT INTO schema_migrations (migration_number, migration_name, applied_by, notes) VALUES
    (10, '010_circuit_breaker_race_prevention', 'd5', 'Partial unique index prevents duplicate uncleared breaker rows')
ON CONFLICT (migration_number) DO NOTHING;

DO $$
BEGIN
    ASSERT (SELECT COUNT(*) FROM pg_indexes
            WHERE indexname = 'idx_pee1_cb_at_most_one_active') = 1,
           'idx_pee1_cb_at_most_one_active must exist post-migration';
    ASSERT (SELECT COUNT(*) FROM pee1_circuit_breaker WHERE cleared_at IS NULL) <= 1,
           'at most one uncleared breaker row must exist post-migration';
END $$;

COMMIT;
