# TFE Validation Issues Log

Issues discovered and fixed during the 60-day validation period (April 14 - ~July 7, 2026).

**Rule:** Only infrastructure bugs are fixed during validation. The kernel (L0-L4) is FROZEN.

---

## Issue 1: Provenance PK + Timezone-naive bar cache
- **Date found:** April 14, 2026 (pre-validation, fixed at start)
- **Commit:** 6337f9b
- **Problem:** Provenance primary key was wrong for `_latest` table; bar cache was timezone-naive
- **Fix:** PK changed to ticker-only; timestamps made UTC-aware
- **Impact:** Data pipeline was producing incorrect refresh results
- **Category:** Infrastructure (data pipeline)

## Issue 2: Sentinel sell qty mismatch — DB vs Alpaca
- **Date found:** April 21, 2026 (Day 6)
- **Problem:** Sentinel used share count from `personal_trade_ledger` database to submit sell orders. BKV had 33 shares in DB but only 32 in Alpaca (entry order for 33 expired, re-submitted for 32 filled). Sentinel tried to sell 33, Alpaca rejected with "insufficient qty available (requested: 33, available: 32)". Retried 28+ times over several hours without success.
- **Root cause:** When an entry order partially fills or expires and is re-submitted for fewer shares, the DB record isn't updated to match the actual filled quantity.
- **Fix:** Modified `killPosition()` in `sentinel_monitor.mjs` to use Alpaca's actual position qty (`alpacaQty` from `/v2/positions/{ticker}`) instead of the DB `shares` value. Added mismatch logging: `[SENTINEL] {ticker} — qty mismatch: DB={shares}, Alpaca={alpacaQty}. Using Alpaca qty.`
- **File changed:** `web/scripts/execution/sentinel_monitor.mjs` (lines 197-213, 243)
- **Impact:** BKV exit was blocked for 7+ hours. No financial loss (position was flat). The fix is infrastructure-only — no kernel change.
- **Category:** Infrastructure (execution pipeline)
- **Status:** Fixed in Codespace, needs deploy to ECS
- **Needs deploy:** YES — this fix must be deployed for BKV to exit

---

## Deployment Notes

After fixing infrastructure bugs, deploy with:
```
# From repo root
tools/deploy_to_prod_with_evidence.sh
# OR via GitHub Actions
```

Current production: tfe-web-task:406, commit 6337f9b, started April 14.

## Issue 3: Duplicate position entries — ALREADY FIXED (pre-validation)
- **Date originally fixed:** April 9, 2026 (commit 2e6ec58)
- **Rediscovered:** April 22, 2026 — future chats: DO NOT re-investigate, this is resolved
- **Problem:** Entry logic submitted duplicate buy orders for the same ticker. Caused 2x position sizes.
- **Root cause:** Strategists didn't check for existing open positions before submitting new orders.
- **Fix:** Commit 2e6ec58 — "strategists skip tickers with existing open positions — no duplicate orders"
- **Affected positions (all from April 8-9, BEFORE the fix):** BIRK (47 shares from 2-3 orders), CMDB (101), COPP (46), SOHU (120). These are pre-validation entries. No duplicates have occurred since the fix.
- **Impact on exits:** The Issue 2 fix (use Alpaca actual qty for sells) ensures these doubled positions exit cleanly at their actual size.
- **Category:** Infrastructure (execution pipeline)
- **Status:** CLOSED — fixed in commit 2e6ec58, no recurrence
