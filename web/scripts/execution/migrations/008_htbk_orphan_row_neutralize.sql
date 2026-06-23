-- =============================================================================
-- Migration: 008_htbk_orphan_row_neutralize
-- Purpose:   Neutralize the duplicate/orphan HTBK ledger row so HTBK is not
--            double-counted after 007 closes the canonical merger row.
--
-- Background:
--   HTBK (67 sh, entry 2026-04-09, CH2) has TWO ledger rows for ONE position:
--     id=364  — created 2026-04-09, status='closed',
--               exit_reason='stale_position_cleanup', p_l NULL, exit_filled_at NULL
--               (a prior half-close that left no economics)  ← THIS ORPHAN
--     id=7532 — created 2026-05-16, status='filled' (the live phantom),
--               closed by migration 007 to p_l=-0.67 as the CANONICAL merger close.
--
--   Without this, the auditor would count HTBK as two closed positions.
--   Row 364 is retained for audit trail but neutralized: zero P&L, marked orphan.
--
-- Decision (Joe, tightened option (b)): do NOT backfill 364 with the merger
--   economics (that would double-count -0.67). Set p_l=0, annotate, leave
--   exit_filled_at NULL to mark it non-economic. Canonical economics stay on 7532.
--
-- Scope:   Exactly one row (id=364), verified by SELECT before authoring.
--          Belt-and-suspenders WHERE: id AND ticker AND exit_reason AND NULL guards.
--          Row 7532 (the canonical 007 close) is explicitly NOT touched.
--
-- Run:  AFTER 007.  psql $DATABASE_URL -f 008_htbk_orphan_row_neutralize.sql
-- =============================================================================

UPDATE personal_trade_ledger
SET p_l = 0,
    rationale_json = rationale_json || '{
      "orphan_note": "orphan: superseded by migration 007 canonical merger close (HTBK->CVBF, row id 7532); retained for audit trail, excluded from P&L"
    }'::jsonb
WHERE id = '364'
  AND UPPER(TRIM(ticker)) = 'HTBK'
  AND status = 'closed'
  AND exit_reason = 'stale_position_cleanup'
  AND exit_filled_at IS NULL
  AND p_l IS NULL;

-- Verify: exactly the orphan was neutralized, and the canonical row is intact.
DO $$
DECLARE
    orphan_pl   numeric;
    canon_pl    numeric;
    orphan_cnt  int;
BEGIN
    SELECT COUNT(*) INTO orphan_cnt FROM personal_trade_ledger
      WHERE id='364' AND p_l = 0
        AND rationale_json ? 'orphan_note';
    ASSERT orphan_cnt = 1, 'HTBK orphan (id=364) not neutralized as expected';

    -- canonical 007 row must remain at -0.67 (run order: 007 then 008)
    SELECT p_l INTO canon_pl FROM personal_trade_ledger WHERE id='7532';
    ASSERT canon_pl = -0.67, 'Canonical HTBK row (id=7532) p_l changed — expected -0.67';

    RAISE NOTICE 'HTBK orphan neutralized (id=364 p_l=0); canonical close intact (id=7532 p_l=-0.67)';
END $$;
