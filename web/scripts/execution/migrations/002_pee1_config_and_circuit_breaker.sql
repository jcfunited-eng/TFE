-- =============================================================================
-- Migration: 002_pee1_config_and_circuit_breaker
-- Purpose:   PEE-1 runtime configuration and circuit breaker halt state.
-- Run:       psql $DATABASE_URL -f 002_pee1_config_and_circuit_breaker.sql
-- =============================================================================

-- ── Execution mode config ────────────────────────────────────────────────────
-- Controls whether PEE-1 places real orders or paper orders.
-- Changed via the admin UI toggle — persists across server restarts.
CREATE TABLE IF NOT EXISTS pee1_execution_config (
    key             TEXT        PRIMARY KEY,
    value           TEXT        NOT NULL,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by      TEXT        NOT NULL DEFAULT 'system'
);

-- Seed defaults (safe: paper mode, 5% max drawdown threshold)
INSERT INTO pee1_execution_config (key, value, updated_by) VALUES
    ('execution_mode',          'paper',  'migration'),
    ('max_drawdown_pct',        '5.0',    'migration'),
    ('circuit_breaker_hours',   '24',     'migration'),
    ('risk_per_trade_pct',      '1.5',    'migration')
ON CONFLICT (key) DO NOTHING;

-- ── Circuit breaker halt state ───────────────────────────────────────────────
-- Written by sentinel when max drawdown is breached.
-- PEE-1 runner checks this before processing any signals.
CREATE TABLE IF NOT EXISTS pee1_circuit_breaker (
    id                  BIGSERIAL       PRIMARY KEY,
    triggered_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    expires_at          TIMESTAMPTZ     NOT NULL,
    trigger_reason      TEXT            NOT NULL,
    -- 'max_drawdown'         — portfolio dropped > threshold in one session
    -- 'manual'               — operator-triggered halt
    vault_equity_open   DOUBLE PRECISION,   -- equity at session open
    vault_equity_low    DOUBLE PRECISION,   -- equity at trigger point
    drawdown_pct        DOUBLE PRECISION,   -- (open - low) / open * 100
    threshold_pct       DOUBLE PRECISION,   -- the limit that was breached
    cleared_at          TIMESTAMPTZ,        -- null = still active
    cleared_by          TEXT
);

CREATE INDEX IF NOT EXISTS idx_pcb_expires ON pee1_circuit_breaker (expires_at DESC);
CREATE INDEX IF NOT EXISTS idx_pcb_active  ON pee1_circuit_breaker (cleared_at)
    WHERE cleared_at IS NULL;

-- Auto-update trigger for pee1_execution_config
CREATE OR REPLACE FUNCTION _pee1_config_set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_pee1_config_updated_at ON pee1_execution_config;
CREATE TRIGGER trg_pee1_config_updated_at
    BEFORE UPDATE ON pee1_execution_config
    FOR EACH ROW EXECUTE FUNCTION _pee1_config_set_updated_at();

DO $$
BEGIN
    RAISE NOTICE 'pee1_execution_config and pee1_circuit_breaker migration OK';
END $$;
