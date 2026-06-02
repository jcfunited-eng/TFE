# TFE Session Changelog

Append-only log. Every session writes what it changed, tested, concluded, and what it did NOT verify. Plain language. Read this before doing anything.

---

## 2026-06-02 (c1, Claude Opus 4.6)

### What was changed
- **S_UF band gate REMOVED** from CH2 entry. Tuple-proximity WR >= 0.65 is now the sole entry decision for established stocks. S_UF validated as primary alpha drag: with band -8.65pp vs SPY, without +2.73pp. 28/30 top SPY contributors were gate-rejected, 18 by S_UF.
- **HTBK kill loop fixed** (task 524, commit 7809c02). Idempotent stateful kills + delisted asset handling. HTBK was inactive on Alpaca, sell orders rejected 422 every cycle.

### What was tested
- Tuple-only entry validated leak-free on deep pool (2M daily snapshots, 8,774 tickers ≥30 resolved neighbors): +17.48% return, +2.73pp vs SPY, 75.9% WR, -9.04% max DD, 290 trades. First positive alpha configuration.
- SPY attribution: 28/30 top index movers structurally rejected by TFE gates (D_k!=1: 20, S_UF out of band: 18). Only 2 passed gates and were cap-blocked.
- Conviction-sourced deployment (block-removal + tuple-sized): +9.06%, -5.69pp vs SPY, -6.28% max DD. Better than baseline but not as good as tuple-only + flat sizing.

### What was NOT verified
- Tuple-only entry in falling market (validation window was rising-defensive, SPY +14.75%)
- D_k=1 gate removal (kept as validated per-ticker directional check, but never independently validated on production-equivalent data — original quarantine-based justification)
- Max drawdown behavior under correlated stress (9.04% in rising market → unknown in falling)

---

## 2026-06-01 (c1, Claude Opus 4.6)

### What was changed
- Cash-ceiling fix deployed (task 523, commit e369107). position cost <= available cash before order.
- Closed-market sell fix deployed (task 522, commit bc86579). Market-hours gate + fill confirmation.
- Ledger reconciliation: 20 diverged + 2 ghost positions fixed against Alpaca ground truth.
- Species profiles graceful degradation (task 521). Horse->tuple-proximity rename (commit 9313f78).

### What was tested
- Leak-free backtest (Apr 7-May 29, D_k=-1): +4.78%, -9.97pp vs SPY, 71.8% WR, -2.23% max DD
- Structural EXIT-H (floor-validated, NOT deployed): +6.10%, -8.65pp vs SPY
- Conviction-sourced deployment (NOT deployed): +4.93%, -9.83pp vs SPY, -2.06% max DD
- REGIME_DEFENSIVE_POSITION_MULT=0.5: arbitrary, no derivation

### What was NOT verified
- Structural EXIT-H in D_k=+1; conviction deployment in falling market; 3WA/1+3 tiers; species_profiles in prod RDS

---

## 2026-05-28/29 (c1, Claude Opus 4.6)

### What was changed
- **V3 basin DELETED** from runtime_decision_provenance.mjs and sync_runtime_postgres_impl.mjs (commit 048ab3c). 305 lines removed. computeV3Basins, primitiveReasonCodeFromInputs, stableTitanOverride, inferDecisionLabel, all V3 constants — gone.
- **Tuple-proximity engine deployed** as sole decision source. computeHorseDecision() in horse_decision_engine.mjs. 30 nearest neighbors, 7-dim tuple space, CS-only, bar_count >= 120.
- **History backfill** — 974,434 rows across 5,093 tickers in production runtime_decisions_history. Kernel at every 5th bar position.
- **All g32_* ML artifacts deleted** (5,011 lines). tfe_g32_coordinator.py renamed to tfe_epoch_mosaic_coordinator.py. BANNED ARTIFACTS section added to KERNEL_PHILOSOPHY.md.
- **G32 epoch mosaic populated** on production container (g32_state.json, 790 bytes).
- **Full repo inventory** at REPO_INVENTORY.csv (1,330 files catalogued).
- Production running task tfe-web-task:519, commit 048ab3c.

### What was tested
- Tuple-proximity backtest: 60.3% WR at ≥0.65, 61.2% at ≥0.70 (seed 42). Reproduced on seed 99 (56.1% / 57.9%).
- Portfolio simulation: $100K → $328K (≥0.65), $100K → $247K (≥0.70, Sharpe 1.92, 8.5% DD). Both beat SPY +62%.
- Production shadow: 5,407 CS-only tickers, 1,728 Accumulate (32%). With regime gate (SPY D_k=-1): 0 Accumulate.
- Full universe validation: 5,025 CS-only, 15.4% Accumulate, 62.2% Hold, 22.4% Avoid. 0 errors on 200-sample.
- V3 absent from deployed container: grep confirmed 0 hits.

### What was concluded
- Tuple-proximity engine discriminates: WR range 0.000-1.000, sensible stock-level decisions.
- SPY D_k=-1 regime gate correctly blocks all entries — system in defensive posture.
- V3 basin is permanently removed. Tuple-proximity is the sole decision path.
- Six plumbing bugs surfaced during production integration (column names, field names, Date handling, schema mismatches). All fixed.

### What was NOT verified
- **First production sync has NOT run yet** — next at 13:00 UTC May 30. DB still has V3 decisions from task 518.
- **computeSizing NOT WIRED** to alpaca_bridge.mjs (code exists in l5_unified_shadow.mjs)
- **assessExit NOT WIRED** to sentinel_monitor.mjs
- **computeRegimeExposure NOT WIRED** to CH2/CH3 execution
- **Species profile (Wave 2) NOT BUILT** — 3WA detector skips species classification
- **3WA Wave 1 conditions incomplete** — missing s_n [0.954,0.969] and Δs_n [0.67,0.72] bands
- Sector pressures in epoch governance degrade to no-op until fundamentals backfill populates sector data

---

## 2026-05-28/29 (c1, Claude Opus 4.6)

### What was changed
- **V3 basin DELETED** from runtime_decision_provenance.mjs and sync_runtime_postgres_impl.mjs (commit 048ab3c). 305 lines removed.
- **Tuple-proximity engine deployed** as sole decision source. 30 nearest neighbors, 7-dim tuple space, CS-only, bar_count >= 120.
- **History backfill** — 974,434 rows across 5,093 tickers in production runtime_decisions_history.
- **All g32_* ML artifacts deleted** (5,011 lines). tfe_g32_coordinator.py renamed to tfe_epoch_mosaic_coordinator.py.
- **G32 epoch mosaic populated** on production container.
- Production running task tfe-web-task:519, commit 048ab3c.

### What was tested
- Tuple-proximity backtest: 60.3% WR at >=0.65 (seed 42), reproduced at 56.1% (seed 99).
- Portfolio sim: $100K->$328K (>=0.65, Sharpe 0.83), $100K->$247K (>=0.70, Sharpe 1.92, 8.5% DD). Both beat SPY +62%.
- Production shadow: 5,407 CS-only tickers. With regime gate (SPY D_k=-1): 0 Accumulate. Correct defensive posture.

### What was NOT verified
- First production sync not yet run (13:00 UTC May 30)
- computeSizing, assessExit, computeRegimeExposure NOT WIRED
- Species profile (Wave 2) NOT BUILT
- 3WA Wave 1 s_n/delta_s_n bands incomplete

---

## 2026-05-28 EVENING (c1, Claude Opus 4.6)

### Equivalence testing
- **Stale-bar comparison:** 72.5% match (11/40 mismatches including 4 D_k sign flips). Validation env loaded May 27-28, production refreshes daily. NOT equivalent when bars are stale.
- **Same-bar comparison:** 90.0% match (4/40 mismatches). Fresh Polygon bars through May 27 (same cutoff as production). 3 of 4 D_k flips resolved. 1 persists (BELFA). 2 S_UF divergences (FSS Δ=0.07, BDX Δ=0.1). Root cause: likely bar fetch differences (adjusted/unadjusted, timezone boundary).
- **Conclusion:** Validation env IS equivalent to production when bars match (36/40 = 90%), but 3 tickers show real divergence on same-day bars. Root cause unresolved. Validation env is CONDITIONALLY trustworthy — must refresh same-day before comparison, and ~10% of tickers may show small divergences from bar fetch differences.

### Equivalence root cause FOUND
- Production uses `bar_cache.py` which fetches bars incrementally and caches them. Polygon's adjusted prices change RETROACTIVELY when dividends are paid. Production's cached bars hold the adjustment values from the original fetch date. A fresh Polygon fetch gets today's adjusted values. For dividend-paying stocks, historical bar closes differ between cached and fresh — same bars, different adjustment vintages.
- Confirmed: `adjusted=true`, `limit=5000`, `YEARS_HISTORY=5` all match between production and validation. The divergence is stale adjustment values in production's bar cache, not a parameter mismatch.
- This is NOT fixable by matching fetch parameters. It requires either: (a) Mode B import of production's actual bar cache, or (b) accepting ~25% divergence on dividend-paying stocks as a property of adjusted-price staleness.
- D_k is HIGHLY sensitive to bar values — a few cents of dividend adjustment on one bar can flip D_k from +1 to -1. This is expected behavior, not a bug. The kernel is deterministic; different inputs produce different outputs.

### Protection layer additions
- KERNEL_PHILOSOPHY.md sections 8.5 (data substrate rules), 8.6 (framing discipline), 8.7 (architecture approval), 8.8 (spec discipline)
- PROJECT_STATE.md section 3.4 (validation substrate binding rule) and section 7.1 (additional documented destruction patterns: quarantine drift, tuple decomposition, financial-frame collapse, sensitivity-as-defect, silent canonical change)
- These encode rules Joseph stated in conversation but were never written down. Now binding.

### Equivalence PROVEN
- Production bar cache exported via ECS execute-command → psql \COPY → S3 → validation env import
- 20-ticker proof run on production's exact bars: **100.0% match, 0 mismatches**
- BELFA, BLK, BSM, UVV D_k flips all resolved — root cause was dividend-vintage bar difference
- The validation environment is equivalent to production when using production's bar cache
- pg_dump version mismatch found (container has pg_dump 15.18, server is 17.6) — used psql \COPY as workaround

### What was NOT verified
- Universe filter still broken (CS-only not yet applied)
- L2 comparison still unresolved
- No WR claims validated on clean data

---

## 2026-05-28 (c1, Claude Opus 4.6)

### What was changed
- D_k=1 gate re-enabled in CH2 entry (commit 039ee72, task :507)
- Expired order status handling added to sentinel fill sync (commit 8c7b45c, task :508) — fixed REGN stuck as SUBMITTED for 8 days
- Structural exit assessment spec written (docs/structural_exit_assessment_spec.tex)
- Gate event detection spec written (docs/GATE_EVENT_DETECTION_SPEC.md)
- Validation environment built: local PostgreSQL, 12,016 tickers loaded, 10.4M bars cached
- Curated recommendations page with conviction scoring deployed (task :503)
- Computed NYSE holiday calendar deployed (task :504-505)
- PROJECT_STATE.md created as orientation anchor
- KERNEL_PHILOSOPHY.md updated with per-condition contribution data and 81% investigation status

### What was tested
- Mar 26 filter on validation env: 19 raw signals on 2,000-symbol sample, 17 with 20d returns, point estimate 64.7% WR
- L2 comparison (production vs quarantine): RAN BUT CONTAMINATED — shared CV-1.0 state between runs, signal matching by gate index instead of (ticker,date). Results cannot be trusted.
- Gate event detection concept verified: filter produces signals when run per-gate across history (the "full movie"), produces near-zero when run snapshot-only

### What was concluded
- The Mar 26 filter picks MOMENTS not STOCKS — needs per-gate event detection, not snapshot evaluation
- V3 basin has no edge over base rate (verified earlier this session)
- The 81% claim used a forward lookahead filter ("Rising 5d" = Return_5d > 0). STATUS: under investigation — the actual filter code was never found, only one interpretation matches the documented numbers

### What was NOT verified
- L2 comparison is UNRESOLVED — the contaminated test's conclusion ("quarantine extra signals are noise") cannot be trusted
- Universe filter was BROKEN — 56.3% of loaded tickers are non-CS (ETFs, warrants, preferreds, funds). Every signal count and WR number from this session was polluted
- 64.7% WR is NOT statistically significant — n=17, 95% CI is 41-83%, includes coin flip
- The structural exit assessment (horse/herd/topology) was prototyped on quarantine data but not verified on production-equivalent data
- YYAI at $29,276/share is real but untradeable (85 shares/day volume) — no liquidity filter applied

### What needs to happen next (in order)
1. Fix universe filter to CS-only (5,257 tickers)
2. Re-run Mar 26 filter on clean CS-only universe, full 5-year history
3. Clean L2 comparison — separate runs, match by (ticker,date)
4. Only then: resume gate event detector build and signal quality assessment

---

## 2026-05-27 (c1, Claude Opus 4.6)

### What was changed
- 3 sentinel bugs fixed: orphan adoption loop, stale overnight EXIT-F, premature phantom cleanup (task :500)
- EXIT-R9 7-day minimum hold deployed (task :501)
- Cross-process kill cooldown persisted to DB (task :502)
- Market holiday calendar: first hardcoded (task :504), then computed permanently (task :505)

### What was tested
- 3WA Waves 1+3 verified at 84.6% on 371 signals (backward-looking, production-achievable)
- Per-condition contribution: B_k > prev_B_k carries 13.4pp of edge
- Cognitive gate sensitivity: edge holds 63-65% across threshold range 0.40/1.50 to 0.70/2.00

### What was concluded
- Production and quarantine are different kernels (different L0, different L2)
- The 81% used a forward lookahead — only interpretation matching 3,674/75.0% is Return_5d > 0
- V3 basin formula has zero edge over base rate

### What was NOT verified
- EXIT-R9 effect on realized WR (only 5 trading days of data at the time)
- Whether log L0 is harmful specifically against the Mar 26 filter (tested only against V3 basin)

---

*Add new entries at the TOP of this file. Each entry: date, session ID, what changed / tested / concluded / NOT verified.*
