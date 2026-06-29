# TFE-BRIEF-D1-FULL-SYSTEM-AUDIT-WC-20260626

**Status:** PRE-COMMIT BLOCK on D1 Amendment 4
**Authority:** wC, Joe approval pending
**Reference:** D1 Amendment 4 consumer audit (c1 partial, only L4-tuple read sites)

## Context

c1's audit covered consumers that read L4 tuple fields (D_k, M_k, R_rev_k, U_star_k, C_k, P_k, B_k) from the snapshot row. That's the narrow surface. The wider surface — pipeline, bookkeeping, scheduling, execution — was not audited. wC approved "proceed" without that audit. Joe blocked. Correctly.

The frame shift from last-gate to second-to-last-gate is a contract change on the snapshot row. Every system that reads the snapshot row directly or indirectly may behave differently. Before D1 commits, the full consumer surface needs an audit at the same depth c1 gave the L4 fields.

## What needs auditing, by component

### 1. Pipeline (snapshot production and storage)

- `run_refresh_with_l5_learning.py` — nightly refresh runner. Calls `evaluate_symbol_snapshot` per ticker. Writes to `runtime_decisions_history`. Audit: which fields are written to which columns; does the write path encode any frame assumption (e.g., "the latest bar's D_k" vs "the prior bar's D_k").
- `tools/validation_env_refresh.py` — validation env mirror. Does it use the same evaluate_symbol_snapshot path or a separate one. If separate, does it have its own frame contract.
- `rebuild_uf_snapshot.py` — referenced by the inventory but role unclear. Audit: what it does, when it runs, what it writes.
- `web/scripts/evaluate_live_uf_row.py` — live evaluator. Audit: does it call compute_cognitive_scalars on each refresh, or read pre-computed snapshots; if the former, does the new emission contract apply.

### 2. Bookkeeping (ledger, P&L, provenance)

- `personal_trade_ledger` — production ledger. Audit: does any field in the ledger derive from a snapshot row's D_k/M_k/etc value? Specifically: signal_emission_id chain, entry kernel state captured at entry, exit kernel state captured at exit.
- F-001 through F-010 fixes (drain audit) — any of these introduce frame-aware logic that would need to re-validate against second-to-last-gate emission.
- `sentinel_exit_order_id` resolution (F-002) — does the exit-order reconciliation depend on the snapshot row's D_k at the time of exit decision.
- HTBK migrations 007+008 — any schema or ETL change that assumed last-gate D_k semantics.

### 3. Scheduling (when things run, in what order)

- Sentinel daemon: 60s loop during market hours. Reads from runtime_decisions_history. Audit: does the sentinel make decisions based on TODAY's D_k (last-gate) or the snapshot row's D_k (now second-to-last)? Under Amendment 4 these are different.
- PEE-1 runner: 15-min market-hours loop, submits new entries. Audit: which snapshot row's fields drive the entry decision; does the entry timestamp assume the snapshot's D_k is "for today" or "for yesterday."
- Nightly refresh: post-market. Refresh writes the snapshot row. Audit: at what time does the row become readable; is there a window where intraday sentinel reads a stale row.
- Pre-market kernel recompute (mentioned in design doc Section 8): does this exist as a separate path; if so, does it use the new emission contract.

### 4. Execution layer (Alpaca, order submission, monitoring)

- `web/scripts/execution/alpaca_bridge.mjs` — submits orders. Audit: does the bracket OCO setup depend on snapshot row D_k for sizing or strike calculation.
- `web/scripts/execution/sentinel_daemon.mjs` — exit monitoring. Already partially covered by c1's audit (EXIT-B, EXIT-C, SPY D_k). Confirm no other gates inside the daemon that read snapshot fields.
- `web/scripts/execution/pee1_runner.mjs` — entry submission loop. Audit: how it reads candidates from runtime_decisions_history; whether any field-level filtering uses D_k semantics.
- `web/scripts/execution/capital_allocator.mjs` — sizing. Audit: signal_class tagging depends on Wave 1 evaluation; under Amendment 4 the bar_count source changes (gate-emission index, not calendar days). Does the allocator's signal_class logic still produce the same tags.
- `web/scripts/execution/circuit_breaker.mjs`, `kill_cooldown` enforcement — any field reads that could be affected.
- `web/scripts/execution/entry_timing_watcher.mjs` — timing logic. Audit: does it depend on the snapshot row's D_k being "for today's bar" specifically.

### 5. Audit / monitoring / observability

- `web/scripts/execution/trade_auditor.mjs` — audits trades against signal provenance. Audit: does the audit assume the entry kernel state was captured under last-gate semantics; under Amendment 4, captured state is second-to-last-gate.
- `sentinel_monitor.mjs` — already in c1's audit. Confirm coverage.
- Any dashboard or UI surface that reads snapshot rows and displays "today's D_k" — under Amendment 4 those displays now show "yesterday's D_k."

## Output required from c1

`docs/d1_amend_4_full_system_audit.md` containing:

For each component above, c1 reports:

1. **Files and line numbers** of every read site that touches snapshot row fields or runtime_decisions_history columns affected by the emission contract change (s_n, F_n, raw_x_m, D_k, M_k, R_rev_k, U_star_k, C_k, P_k, B_k, bar_count, emission_frame).

2. **Frame sensitivity:** for each read site, one of:
   - `not-sensitive`: uses field as opaque value, no temporal semantics.
   - `intended-shift`: was already broken under old contract; new contract is correct (this is the W1 case).
   - `latency-only`: behavior shifts by one bar/cycle but logic still works (the SPY D_k Wave 3 case).
   - `breaks-under-new-frame`: existing logic assumes specific temporal semantics that the new frame violates.
   - `unknown`: c1 cannot determine without further review.

3. **Documented expected behavior change:** for each `latency-only` or `intended-shift` consumer, a one-line description of the visible behavior change in v1.0 deployment.

4. **Stop list:** every `breaks-under-new-frame` and `unknown` consumer. wC will review each individually; D1 does not commit while any item is on this list.

## Constraint

c1 does not propose fixes during the audit. The audit is descriptive only. Fix proposals come after wC reviews the audit output. This prevents the audit from sliding into a "I'll just fix it while I'm in there" pattern.

## Time budget

c1 estimates wall time for the audit. If > 4 hours, c1 reports and we scope down. Wider surface may need to be sequenced across multiple dispatches.

## Deliverables

- `docs/d1_amend_4_full_system_audit.md` (this audit's output)
- No code changes
- No commits to `compute_cognitive_scalars` or `evaluate_symbol_snapshot` until audit is reviewed

## Next step after audit

wC reads the audit. For each `breaks-under-new-frame` and `unknown` finding, wC makes a decision (in writing, as a brief, not in chat prose). Joe reviews. Then D1 either commits with documented exceptions or D1 amendment 4 is re-scoped.
