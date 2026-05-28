# TFE Session Changelog

Append-only log. Every session writes what it changed, tested, concluded, and what it did NOT verify. Plain language. Read this before doing anything.

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
