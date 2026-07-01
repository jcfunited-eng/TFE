-- =============================================================================
-- Migration: 012_config_cleanup
-- Purpose:   Remove deprecated circuit_breaker_threshold_pct config key.
--            D4.9 unified the drawdown threshold to max_drawdown_pct=5.0.
--            Ensures max_drawdown_pct=5.0 is present and entries_halted=true
--            (belt-and-suspenders — env var TFE_ENTRIES_HALTED is primary).
-- Run:       psql $DATABASE_URL -f 012_config_cleanup.sql
-- =============================================================================

BEGIN;

DELETE FROM pee1_execution_config WHERE key = 'circuit_breaker_threshold_pct';

INSERT INTO pee1_execution_config (key, value, updated_by)
VALUES ('max_drawdown_pct', '5.0', 'migration_012')
ON CONFLICT (key) DO UPDATE SET value = '5.0', updated_at = NOW(), updated_by = 'migration_012';

INSERT INTO pee1_execution_config (key, value, updated_by)
VALUES ('entries_halted', 'true', 'migration_012')
ON CONFLICT (key) DO UPDATE SET value = 'true', updated_at = NOW(), updated_by = 'migration_012';

INSERT INTO schema_migrations (migration_number, migration_name, applied_by, notes) VALUES
    (12, '012_config_cleanup', 'd5', 'Removed circuit_breaker_threshold_pct; canonicalized max_drawdown_pct=5.0; entries_halted=true (safeguard)')
ON CONFLICT (migration_number) DO NOTHING;

DO $$
BEGIN
    ASSERT NOT EXISTS (SELECT 1 FROM pee1_execution_config WHERE key = 'circuit_breaker_threshold_pct'),
           'circuit_breaker_threshold_pct must be absent';
    ASSERT (SELECT value FROM pee1_execution_config WHERE key = 'max_drawdown_pct') = '5.0',
           'max_drawdown_pct must be 5.0';
    ASSERT (SELECT value FROM pee1_execution_config WHERE key = 'entries_halted') = 'true',
           'entries_halted must be true';
END $$;

COMMIT;
