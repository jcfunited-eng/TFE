---
name: tfe-research-run
description: Run the TFE research machinery — stores, law/ledger/harvest tools, sharding, where results file. Use when measuring any construction, extending stores, or reproducing audit numbers.
---

# Running the research machinery

## The kernel is canon
CH4 runs on the FULL UF kernel: uf_core/ (layer0-4, hardening,
safemode; pinned tau_D=0.20, alphas=1.0) per the spec PDF
"docs/UF_Spec_v1_4_0_skeleton 2026.pdf" and Joe's pasted L0-L4 canon
in docs/UF_DSF_KERNEL_CANON_20260804.md. Gates = quiet intervals
D(t)<=tau_D; kappa(t) needs bar t+1, so a boundary at tb is first
computable at the close of tb+1 — fills there, never earlier.
tools/ch4_canon_law.py runs the species law on uf_core gates
(Addendum 6: band>=0.75 predictions confirmed 58.6-77.9% EVERY year
2016-2026, 172,433 obs).

## Stores (parquet, repo root)
- `quarantine_12k_universe_ext.parquet` — daily 2016..2026-03-24,
  ~12k symbols, Massive adjusted. FROZEN research base; never mutate.
- `ch4_live_store.parquet` — the ext store + same-source daily appends
  (tools/ch4_store_refresh.py; grouped-daily endpoint; symbols with a
  >1.8x seam break across the append are DROPPED and logged — splits
  in the gap; they re-enter only via full re-fetch).
- `ch4_hourly_universe_full.parquet` — hourly 2016..2026-03-24, 5,016
  symbols, extended hours included (filter RTH by NY clock).
- `ch3_m15_watchlist.parquet` — 15-min 2016..2026-07, the 60-name
  watchlist (tools/ch3_m15_store.py to extend).
- Roster: artifacts/ch4_uf/ch4_field_cohorts.json — 5,219 eligible in
  174 liquidity cohorts of 30.

## Core tools (all env-parameterized)
- `tools/ch3_hourly_law.py` — species law + as-of-issue ledger + preds
  streams. Envs: CH3_RUNG=daily|hour|m15, CH3_STORE, CH3_LAW_OUT,
  CH3_PREDS_OUT, CH3_KEEP_ALL=1 (all n>=W preds), CH3_TRADE_DISP=1
  (null test), sharding CH3_OBS_SHARD=k/K + CH3_OBS_MERGE=1 +
  CH3_SHARD_DIR. Shard 8-way for full-field runs (20 cores, 32GB).
- `tools/ch4_kgate_herd.py` — herd-conditioned K-gate books.
  CH4_K, CH4_HERD_LAG=1 for intraday streams, CH3_PREDS, CH4_OUT.
- `tools/ch4_kgate_harvest.py` — quantile-shape harvest variant.
- `tools/ch3_hourly_harvest.py`, `tools/ch3_cycle_harvest.py`
  (CH3_MORPH=1) — falsified constructions, kept for reproduction.
- `tools/ch4_uf_spectrum_herd.py` — herd cells/weather;
  CH4_HERD_EXPORT=path writes the per-(sym,day) state table and exits.
- `tools/ch4_herd_kgate_live.py` — the live engine; CH4_ASOF for
  frozen-date tests, DRY for no-book runs.

## Time-key convention
12-digit YYYYMMDDHHMM everywhere new (daily -> YYYYMMDD0000). Legacy
hourly preds are 10-digit; tools auto-detect via magnitude.

## Where results go
JSON to artifacts/ch4_uf/ (gitignored) + an addendum in
docs/CH4_LIVE_TIMING_AUDIT_20260731.md (or a new dated doc) committed
AND pushed to origin. Misses filed as plainly as wins. Memory updated
for spec-level findings.

## Adversarial controls that exist
- Null test: CH3_TRADE_DISP=1 (tradable displacement -> binomial null).
- Mirror-world probe (Joe, 2026-08-06): invert every price series
  (c_inv[t] = c0^2/c[t], exactly negated log-returns, volumes kept),
  rebuild herd state on the inverted store, replay the untouched
  engine — tests whether decisions come from structure (mirrored
  decisions, long/short flipped) or from riding market drift
  (decisions collapse). Scripts in session scratchpad
  (build_inverted_store.py, mirror_driver.py); results filed in the
  audit doc.

## Heavy-run hygiene
Background long runs via the harness (they survive turn ends; nohup'd
processes may not). OOM killed a 30GB tuple materialization once —
stream over typed numpy arrays in chunks, never list() 50M rows.
Container rebuilds kill everything mid-flight; check partial logs
before assuming completion.
