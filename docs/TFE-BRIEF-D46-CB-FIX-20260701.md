# TFE-BRIEF-D46-CB-FIX-20260701

**Deploy:** D4.6 — Circuit breaker session-open equity fix + liquidation write-path hardening
**Branch:** `codex/persistent-etl-update-20260326`
**Parent SHA:** `784b194`
**Owner:** Eve (wC), engineering authority
**Coordinator:** Joe

---

## SUMMARY

Two audit findings from the 2026-07-01 execution-layer audit — CB-1 and CB-2 — are blocking D7 (kill-switch flip). D4.6 fixes both, plus one collateral silent-catch and one previously-uncaught duplicate of CB-1 in `sentinel_monitor.mjs`.

Handoff summary said CB-1 was in one file. **Direct code read shows the same bug in two files.** The daily sentinel is as blind as the standalone fuse.

## FINDINGS RE-VERIFIED AGAINST 784b194

### CB-1 (both files) — Session-open equity fallback collapses drawdown to 0 on quiet days

- `circuit_breaker.mjs:200-206`
- `sentinel_monitor.mjs:514-522`

Both query the earliest `vault_equity_at_signal` from today's ledger rows to establish "session-open equity." If today has zero signals — which Wave 1 produces by design (avg ~1.5 signals/day, so ~30% of days are quiet) — the fallback is `equityNow`, drawdown math yields 0, breaker cannot fire.

If a position from yesterday is drawing down today, the breaker silently declines to save us.

**Fix:** Replace ledger-based session-open equity with Alpaca account `last_equity` (equity at previous close). This is exactly the right reference intraday. Alpaca updates `last_equity` once per day at market open. If missing or zero, skip the drawdown check with a warn log (fail closed on spurious fires).

Spec (`docs/tfe_pee1_signal_spec.tex:173`) says only "portfolio drawdown > max_dd_pct". No reference definition specified. `last_equity` is compatible.

### CB-2 — Silent ledger-write failure during emergency liquidation

- `circuit_breaker.mjs:150-167`

`liquidateAllPositions` market-sells on Alpaca BEFORE the ledger UPDATE. If the UPDATE fails (line 157 `.catch(e => console.error(...))` logs but doesn't recover), the position is closed on Alpaca but the ledger still shows OPEN. Same D4.5 anti-pattern.

Worse: the fallback rationale write at line 162-167 uses `.catch(() => {})` — completely silent. Both paths can fail with no operator-visible signal.

During a real drawdown event this is the highest-consequence failure mode in the codebase: emergency liquidation succeeds financially but leaves phantom-open ledger rows that will be re-adopted by orphan_sync as the CWAN/HTBK loop already demonstrates.

**Fix:** Extract `closePositionInLedgerWithRetry()` helper. Same shape as D4.5 `writeOrderIdsToLedger`:
- 3 primary attempts with 500ms backoff
- On all-fail: fallback UPDATE that appends recovery breadcrumbs to `rationale_json` (sell order ID, cb_reason, cb_fallback_write_at)
- On both-fail: CRITICAL log with all IDs so the row is manually recoverable from CloudWatch

Rationale-fallback carries enough state for downstream reconciliation (zombie check, trade_auditor) to identify the position as closed.

### CB-collateral — Cancel-queue silent catch

- `circuit_breaker.mjs:121`

`cancelStealthQueue` UPDATE has `.catch(() => {})`. Lower severity (a stuck 'pending' queue row is not a phantom position) but same anti-pattern. Fixed to log at ERROR level.

## OUT OF SCOPE FOR D4.6

- ET-1 EventBridge verification → D4.7
- D-1, D-3, CH2-3, CH2-4 → D4.8
- Cosmetic pass → D4.9
- CB-3 (race window), CB-4 (parseFloat validation) — rolled into D4.8 with the other hardening

## VERIFICATION

**Local:**
`node web/scripts/execution/tests/circuit_breaker_test.mjs`
Expected: 12/12 assertions PASS.

**Post-deploy (val env):**
1. Force a synthetic drawdown scenario in val env DB (insert a signal today, set vault_equity_at_signal to $110K, mock Alpaca account with equity=$103K and last_equity=$107K).
2. Invoke `runCircuitBreaker()`.
3. Assert: breaker fires (uses last_equity=$107K → drawdown 3.74% ≥ 3.0% threshold), ledger rows closed via retry helper, no phantom-open rows.
4. Repeat with quiet-day fixture (zero signals today, last_equity=$107K, equity=$103K).
5. Assert: breaker STILL fires. This is the case that was silently broken.

**Post-deploy (prod):**
Kill switch stays ON. Confirm `runCircuitBreaker()` on next EventBridge invocation logs `equityOpen=` from `last_equity` (visible in CloudWatch), not from a ledger row.

## DEPLOY POSTURE

Kill switch ON throughout. This deploy touches emergency-path code only; entry path unchanged. No expected behavior change on days with signals; corrected behavior on quiet days.

---

**End of brief.**
