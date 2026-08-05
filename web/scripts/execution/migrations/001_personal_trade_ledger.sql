-- =============================================================================
-- Migration: 001_personal_trade_ledger
-- Purpose:   Persistent audit ledger for every PEE-1 signal, execution,
--            and exit. Personal use only. Required for SQA.
-- Run:       psql $DATABASE_URL -f 001_personal_trade_ledger.sql
-- =============================================================================

CREATE TABLE IF NOT EXISTS personal_trade_ledger (

    -- ── Identity ────────────────────────────────────────────────────────────
    id                              BIGSERIAL       PRIMARY KEY,
    ticker                          TEXT            NOT NULL,
    run_id                          TEXT            NOT NULL,       -- TFE refresh run_id that produced the signal
    signal_class                    TEXT            NOT NULL,       -- must be '3WA' for execution

    -- ── 3WA Gate Fields (snapshotted at signal time) ────────────────────────
    spy_dk                          INTEGER,                        -- must be 1
    s_uf                            DOUBLE PRECISION,               -- must be > 0  (S_UF / s_n field)
    bar_count                       INTEGER,                        -- must be <= 20 for Wave 1
    f_n                             DOUBLE PRECISION,               -- structural energy at signal
    d_k                             INTEGER,                        -- ticker D_k at signal
    b_k                             DOUBLE PRECISION,               -- B_k at signal

    -- ── Capital Allocation ──────────────────────────────────────────────────
    vault_equity_at_signal          DOUBLE PRECISION,               -- account equity when signal fired
    risk_per_trade_pct              DOUBLE PRECISION    NOT NULL DEFAULT 1.5,
    dollar_allocation               DOUBLE PRECISION,               -- vault_equity * risk_pct / 100
    shares                          INTEGER,                        -- floor(dollar_allocation / entry_limit_price)
    atr_14                          DOUBLE PRECISION,               -- ATR-14 used for bracket sizing

    -- ── Order Details ───────────────────────────────────────────────────────
    alpaca_order_id                 TEXT            UNIQUE,
    alpaca_take_profit_order_id     TEXT,
    alpaca_stop_loss_order_id       TEXT,
    entry_limit_price               DOUBLE PRECISION,               -- limit price submitted
    take_profit_price               DOUBLE PRECISION,               -- entry + 1.2 * ATR
    stop_loss_price                 DOUBLE PRECISION,               -- entry - 1.0 * ATR
    time_in_force                   TEXT            NOT NULL DEFAULT 'day',

    -- ── Execution Fill ──────────────────────────────────────────────────────
    entry_filled_price              DOUBLE PRECISION,
    entry_filled_at                 TIMESTAMPTZ,
    exit_filled_price               DOUBLE PRECISION,
    exit_filled_at                  TIMESTAMPTZ,

    -- ── Outcome ─────────────────────────────────────────────────────────────
    p_l                             DOUBLE PRECISION,               -- (exit - entry) * shares
    p_l_pct                         DOUBLE PRECISION,               -- p_l / (entry * shares) * 100
    exit_reason                     TEXT,
    -- 'take_profit'        — TP leg filled
    -- 'stop_loss'          — SL leg filled (market)
    -- 'day_expired'        — unfilled at close, cancelled by DAY TIF
    -- 'sentinel_zombie'    — tau_in > 10 bars, sentinel forced market sell
    -- 'sentinel_spy_flip'  — SPY D_k flipped to 0/−1, full liquidation
    -- 'sentinel_calamity'  — R_rev_k > 0, calamity kill switch
    -- 'rejected_no_3wa'    — signal_class != '3WA', order never placed
    -- 'rejected_field'     — required field missing or invalid, order never placed
    -- 'manual'             — operator-initiated exit

    -- ── Status Lifecycle ────────────────────────────────────────────────────
    status                          TEXT            NOT NULL DEFAULT 'pending',
    -- pending → submitted → filled → closed | cancelled | rejected

    -- ── Full SQA Rationale ──────────────────────────────────────────────────
    rationale_json                  JSONB           NOT NULL DEFAULT '{}',
    -- Required keys: { wave1_active, wave3_active, spy_dk, s_uf,
    --                  bar_count, f_n, run_id, vault_equity, atr_14,
    --                  rejection_reason (if rejected) }

    -- ── Timestamps ──────────────────────────────────────────────────────────
    signal_detected_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    created_at                      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at                      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- ── Indexes ─────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_ptl_ticker
    ON personal_trade_ledger (ticker);

CREATE INDEX IF NOT EXISTS idx_ptl_run_id
    ON personal_trade_ledger (run_id);

CREATE INDEX IF NOT EXISTS idx_ptl_status
    ON personal_trade_ledger (status);

CREATE INDEX IF NOT EXISTS idx_ptl_signal_class
    ON personal_trade_ledger (signal_class);

CREATE INDEX IF NOT EXISTS idx_ptl_alpaca_order_id
    ON personal_trade_ledger (alpaca_order_id)
    WHERE alpaca_order_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_ptl_created_at
    ON personal_trade_ledger (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_ptl_status_open
    ON personal_trade_ledger (status, created_at DESC)
    WHERE status IN ('pending', 'submitted', 'filled');

-- ── Auto-update updated_at trigger ──────────────────────────────────────────
CREATE OR REPLACE FUNCTION _ptl_set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_ptl_updated_at ON personal_trade_ledger;
CREATE TRIGGER trg_ptl_updated_at
    BEFORE UPDATE ON personal_trade_ledger
    FOR EACH ROW EXECUTE FUNCTION _ptl_set_updated_at();

-- ── Verify ──────────────────────────────────────────────────────────────────
DO $$
BEGIN
    ASSERT (SELECT COUNT(*) FROM information_schema.tables
            WHERE table_name = 'personal_trade_ledger') = 1,
           'personal_trade_ledger table creation failed';
    RAISE NOTICE 'personal_trade_ledger migration OK';
END $$;
