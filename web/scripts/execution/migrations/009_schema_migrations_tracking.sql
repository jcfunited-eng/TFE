-- =============================================================================
-- Migration: 009_schema_migrations_tracking
-- Purpose:   Track applied migrations to enable idempotent re-runs and audit.
--            Retroactively records migrations 001-008 with best-effort dates.
-- Run:       psql $DATABASE_URL -f 009_schema_migrations_tracking.sql
-- =============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_number    INTEGER      PRIMARY KEY,
    migration_name      TEXT         NOT NULL,
    applied_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    applied_by          TEXT         NOT NULL DEFAULT 'unknown',
    git_commit_sha      TEXT,
    notes               TEXT
);

-- Retroactive records for 001-008.
-- Exact apply dates unknown; using best-effort based on git log + handoff.
INSERT INTO schema_migrations (migration_number, migration_name, applied_at, applied_by, notes) VALUES
    (1, '001_personal_trade_ledger',           '2026-04-02 00:00:00+00', 'retroactive', 'Recorded retroactively; original date unknown'),
    (2, '002_pee1_config_and_circuit_breaker', '2026-04-02 00:00:00+00', 'retroactive', 'Recorded retroactively; original date unknown'),
    (3, '003_pee1_portfolio_config',           '2026-04-02 00:00:00+00', 'retroactive', 'Recorded retroactively; original date unknown'),
    (4, '004_pee1_stealth_queue',              '2026-04-02 00:00:00+00', 'retroactive', 'Recorded retroactively; original date unknown'),
    (5, '005_ui_asset_controls',               '2026-04-02 00:00:00+00', 'retroactive', 'Recorded retroactively; original date unknown'),
    (6, '006_daily_bars_cache',                '2026-04-02 00:00:00+00', 'retroactive', 'Recorded retroactively; original date unknown'),
    (7, '007_htbk_merger_ledger_correction',   '2026-06-24 00:00:00+00', 'retroactive', 'Applied via ECS Exec 2026-06-24 per handoff'),
    (8, '008_htbk_orphan_row_neutralize',      '2026-06-24 00:00:00+00', 'retroactive', 'Applied via ECS Exec 2026-06-24 per handoff')
ON CONFLICT (migration_number) DO NOTHING;

INSERT INTO schema_migrations (migration_number, migration_name, applied_by, notes) VALUES
    (9, '009_schema_migrations_tracking', 'd5', 'Creates tracking table and retroactive records for 001-008')
ON CONFLICT (migration_number) DO NOTHING;

DO $$
BEGIN
    ASSERT (SELECT COUNT(*) FROM schema_migrations) >= 9,
           'schema_migrations must have at least 9 rows post-migration';
    RAISE NOTICE 'schema_migrations rows: %', (SELECT COUNT(*) FROM schema_migrations);
END $$;

COMMIT;
