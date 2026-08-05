-- =============================================================================
-- Migration: 003_pee1_portfolio_config
-- Purpose:   Add vault funding and auto-TFE toggle to execution config.
-- Run:       psql $DATABASE_URL -f 003_pee1_portfolio_config.sql
-- =============================================================================

INSERT INTO pee1_execution_config (key, value, updated_by) VALUES
    ('vault_funded_amount', '0',    'migration'),
    ('auto_tfe_enabled',    'true', 'migration')
ON CONFLICT (key) DO NOTHING;

DO $$
BEGIN
    RAISE NOTICE 'pee1 portfolio config keys added OK';
END $$;
