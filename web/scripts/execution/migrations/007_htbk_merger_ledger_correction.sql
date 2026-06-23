-- =============================================================================
-- Migration: 007_htbk_merger_ledger_correction
-- Purpose:   Close HTBK ledger row to reflect HTBK→CVBF merger outcome.
--
-- Background:
--   Heritage Commerce Corp (HTBK) merged into CVB Financial Corp (CVBF)
--   effective 2026-04-17. Each HTBK share converted to 0.65 CVBF shares.
--   CVBF closed at ~$20.68 on merger date → HTBK equivalent exit price
--   = $20.68 × 0.65 = $13.44 per original HTBK share.
--
--   Alpaca paper account retains 67 phantom HTBK shares (asset status:
--   inactive, tradable: false). No API path to clear them. Sentinel
--   marked the position exit_blocked after Alpaca rejected sell attempts.
--
--   This migration reflects the true economic outcome in the ledger.
--   Paper account phantom shares are unresolvable via Alpaca API.
--
-- Safety:
--   WHERE clause includes exit_filled_at IS NULL to prevent re-touching
--   any HTBK row that's already correctly closed.
--
-- Run:  psql $DATABASE_URL -f 007_htbk_merger_ledger_correction.sql
-- =============================================================================

UPDATE personal_trade_ledger
SET status            = 'closed',
    exit_reason       = 'delisted_merger_HTBK_to_CVBF',
    exit_filled_price = 13.44,
    exit_filled_at    = '2026-04-17T20:00:00Z',
    p_l               = -0.67,
    p_l_pct           = -0.07,
    rationale_json    = rationale_json || '{
      "merger_note": "HTBK merged into CVBF at 0.65 ratio on 2026-04-17. 67 shares x 0.65 = 43.55 CVBF shares. Exit price = CVBF $20.68 x 0.65 = $13.44/HTBK share equivalent. Paper account retains phantom shares."
    }'::jsonb
WHERE UPPER(TRIM(ticker)) = 'HTBK'
  AND status IN ('submitted', 'filled')
  AND exit_filled_at IS NULL;

-- Verify
DO $$
BEGIN
    ASSERT (
        SELECT COUNT(*) FROM personal_trade_ledger
        WHERE UPPER(TRIM(ticker)) = 'HTBK'
          AND status IN ('submitted', 'filled')
          AND exit_filled_at IS NULL
    ) = 0,
    'HTBK ledger correction failed — unclosed rows remain';
    RAISE NOTICE 'HTBK merger ledger correction OK';
END $$;
