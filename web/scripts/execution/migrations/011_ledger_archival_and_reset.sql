-- =============================================================================
-- Migration: 011_ledger_archival_and_reset
-- Purpose:   Archive drain-period personal_trade_ledger to a dated archive
--            table, then TRUNCATE for fresh D6 paper trading window.
--            Also truncates pee1_stealth_queue (drain state).
--
-- SAFETY:    Migration is idempotent via schema_migrations check.
--            Aborts if archive table with today's date already exists but
--            migration is not recorded (prevents accidental overwrite of a
--            manually-created archive).
--
-- PRE-CONDITIONS (verified before dispatch):
--   - Kill switch ON (TFE_ENTRIES_HALTED=1) — no writes during migration
--   - Portfolio drained (0 open positions) — confirmed by wC + Joe
--   - No CH2/CH3 rows post-D2 — verified in D4.7 dispatch
-- Run:       psql $DATABASE_URL -f 011_ledger_archival_and_reset.sql
-- =============================================================================

BEGIN;

DO $migration_011$
DECLARE
    v_archive_name TEXT;
    v_row_count    BIGINT;
    v_archived     BIGINT;
BEGIN
    IF EXISTS (SELECT 1 FROM schema_migrations WHERE migration_number = 11) THEN
        RAISE NOTICE 'Migration 011 already applied — skipping';
        RETURN;
    END IF;

    v_archive_name := 'personal_trade_ledger_archive_' || to_char(NOW() AT TIME ZONE 'UTC', 'YYYYMMDD');

    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = v_archive_name) THEN
        RAISE EXCEPTION 'Archive table % already exists but migration 011 not recorded — aborting to prevent overwrite', v_archive_name;
    END IF;

    SELECT COUNT(*) INTO v_row_count FROM personal_trade_ledger;
    RAISE NOTICE 'Pre-archive: personal_trade_ledger has % rows', v_row_count;

    EXECUTE format('CREATE TABLE %I (LIKE personal_trade_ledger INCLUDING ALL)', v_archive_name);
    EXECUTE format('INSERT INTO %I SELECT * FROM personal_trade_ledger', v_archive_name);
    EXECUTE format('SELECT COUNT(*) FROM %I', v_archive_name) INTO v_archived;
    RAISE NOTICE 'Archive % created with % rows', v_archive_name, v_archived;

    ASSERT v_archived = v_row_count, 'archive row count must match source';

    TRUNCATE personal_trade_ledger RESTART IDENTITY;
    RAISE NOTICE 'personal_trade_ledger truncated, id sequence reset to 1';

    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'pee1_stealth_queue') THEN
        TRUNCATE pee1_stealth_queue RESTART IDENTITY;
        RAISE NOTICE 'pee1_stealth_queue truncated';
    END IF;

    INSERT INTO schema_migrations (migration_number, migration_name, applied_by, notes) VALUES
        (11, '011_ledger_archival_and_reset', 'd5',
         format('Archived %s rows to %s; personal_trade_ledger and pee1_stealth_queue truncated', v_archived, v_archive_name));
END $migration_011$;

COMMIT;
