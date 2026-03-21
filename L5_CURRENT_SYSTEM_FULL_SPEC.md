# L5 Current Layer + Oracle + Advisor Full Spec (Code Truth)

As-of: 2026-03-09 UTC

This spec is derived directly from the current code, not design intent. It covers:
- L5 policy learning and promotion
- Oracle short-cycle optimizer gate
- Refresh/runtime sync/validation flow
- Advisor surfaces (recommendations + portfolio allocator + quality/probe tooling)

## 1. Authoritative Entry Points

Primary orchestration path:
- `web/src/app/api/admin/refresh/route.ts` -> spawns `run_refresh_with_l5_learning.py`
- `run_refresh_with_l5_learning.py` -> refresh -> quote/profile cache refresh -> L5 learning -> oracle short-cycle (conditional) -> runtime postgres sync -> validation gate

Core L5 engine:
- `l5_policy_learning_pipeline.py`
- `l5_postgres_io.py`

Oracle controller:
- `tools/oracle_program/oracle_program.py`

Advisor/runtime consumption:
- `web/src/lib/runtime-postgres.ts`
- `web/src/lib/uf-snapshot.ts`
- `web/src/app/api/recommendations/list/route.ts`
- `web/src/app/api/portfolio/route.ts`
- `web/src/app/api/admin/recommendation-quality/route.ts`

Operational/probe utilities:
- `web/scripts/sync_runtime_postgres.mjs`
- `web/scripts/run_validation_gate_v1.mjs`
- `web/scripts/portfolio_advisor_confidence_probe.mjs`
- `tools/run_portfolio_advisor_confidence_probe_lane.sh`

## 2. End-to-End Refresh -> L5 -> Runtime Flow

### 2.1 Admin refresh API behavior

`web/src/app/api/admin/refresh/route.ts`:
- `mode=snapshot` maps to args:
  - `run_refresh_with_l5_learning.py --refresh-mode full_universe`
- `mode=universe_snapshot` maps to args:
  - `run_refresh_with_l5_learning.py --refresh-mode full_universe --force-refresh-universe`
- Writes run lifecycle into `runtime_refresh_runs` table (start row + terminal update).
- Exports env for downstream scripts (`TFE_REFRESH_*`).

### 2.2 Refresh wrapper execution order

`run_refresh_with_l5_learning.py` main sequence:
1. Run snapshot rebuild (`rebuild_snapshot`).
2. Run quote cache refresh (`web/scripts/build_screener_quote_cache.py`) unless disabled.
3. Run profile override refresh (`web/scripts/build_screener_profile_overrides.py`) unless disabled.
4. Run L5 policy learning (`run_l5_policy_learning`) unless skipped.
5. Resolve oracle short-cycle execution plan.
6. Optionally run oracle short-cycle (`tools/oracle_program/oracle_program.py short-cycle`).
7. Enforce oracle gates if short-cycle ran:
   - return-lift target met (default target 4.0)
   - epoch library schema == `v1`
8. Sync runtime data to Postgres (`web/scripts/sync_runtime_postgres.mjs`).
9. Run validation gate (`web/scripts/run_validation_gate_v1.mjs`) and require `status=pass`.

Resume support:
- Post-L5/pre-oracle checkpoint persisted locally and optionally S3-backed.
- Stage key: `post_l5_pre_oracle`.

## 3. L5 Policy Learning: Current Implementation

### 3.1 Data sources and modes

`l5_policy_learning_pipeline.py` supports:
- `POLICY_SOURCE_MODE`:
  - `replay` (default)
  - `rowtrace`
  - `hybrid` (merge rowtrace-first with replay fallback)
- `EVAL_MODE`:
  - `replay` (default)
  - `rowtrace`

I/O mode (`TFE_L5_POLICY_IO_MODE` via `l5_postgres_io.py`):
- `file`
- `hybrid` (try Postgres, fallback file)
- `postgres` (strict)

### 3.2 Structural keying (L4 -> L5 cell mapping)

Both policy generation and evaluation build PSCF cell keys from structural fields:
- regime
- D, M-sign, R_rev, U bucket
- C, P bucket, B-sign
- S bucket, R bucket
- optional CD bucket by regime mode
- optional stability bucket
- optional IRF phase suffix
- optional Spider Eyes suffix

Key functions:
- Row-trace keying: `_row_trace_cell_key`, `_row_trace_cell_key_candidates`
- Runtime state keying: `_state_cell_key`, `_state_cell_key_candidates`

Key schema string embedded in artifacts:
- `regime + D + M_sign + R_rev + U_bucket + C + P_bucket + B_sign + S_bucket3 + R_bucket3 + CD_bucket_opt + PH_opt + SE_opt`

### 3.3 Decision selection and explicit optimization guards

Cell-level decision picks best among `{Accumulate, Hold, Avoid}` using:
- default objective: weighted mean excess vs SPY by horizon (`SELECTION_OBJECTIVE=excess`)
- optional objective: mean action return (`SELECTION_OBJECTIVE=action_return`)

Explicit hold guards for non-Hold outcomes:
- minimum action edge (`TFE_POLICY_MIN_ACTION_EDGE`)
- minimum margin to second-best (`TFE_POLICY_MIN_ACTION_MARGIN`)
- minimum winrate (`TFE_POLICY_MIN_ACTION_WINRATE_PCT`)

If a guard fails, decision is forced to `Hold` with reason markers in decision stats.

### 3.4 Replay generation specifics

Replay generation (`_generate_policy_from_replay_dataset`):
- Computes UF state per bar using `compute_uf_structural_state`.
- Tracks anomaly flags from decision guard/hardening.
- Scores with two tracks per cell:
  - clean samples (no anomaly)
  - all samples
- Selection policy:
  - use clean-sample stats if available
  - fallback to all-sample stats when clean empty

Includes symbol timeout and state-compute timeout controls.

### 3.5 Merge, anomaly overlay, eval, promotion

Merge behavior:
- Primary-first, secondary fallback (`_merge_policies`).
- Optional low-support filter for primary via `TFE_POLICY_MIN_PRIMARY_CELL_SAMPLES`.

Anomaly overlay:
- `_overlay_anomaly_profiles` fills missing anomaly profile from anomaly-watch policy.

Evaluation:
- `_evaluate_policy` on replay dataset
- `_evaluate_policy_rowtrace` on row-trace dataset
- Produces per-horizon summaries for 5/20/60 including:
  - excess vs SPY
  - outcome-over-index
  - mapping rates
  - anomaly-accounted variants

Promotion gate (`_compare_candidate_vs_current`):
- promote only if all true:
  - aggregate delta excess (anomaly-accounted mean) >= 0
  - delta outcome-over-index >= 0 for all horizons
  - mapping rate delta >= 0 for all horizons

Auto-promotion:
- requires gate pass + `TFE_POLICY_AUTO_PROMOTE=true`
- strict postgres mode promotes to Postgres runtime table only
- non-strict can atomically replace runtime policy file

## 4. Oracle Short-Cycle Gate

### 4.1 Invocation point and skip/run policy

`run_refresh_with_l5_learning.py` decides if oracle short-cycle runs:
- Skip rule for targeted refresh with no effective rows.
- Trigger policy (`TFE_REFRESH_ORACLE_TRIGGER_POLICY`):
  - `always`
  - `scheduled_only`
  - `explicit_only`
  - default `scheduled_or_explicit`
- Explicit override: `TFE_REFRESH_ORACLE_ALLOW_SHORT_CYCLE=1`

### 4.2 Oracle controller behavior

`tools/oracle_program/oracle_program.py short-cycle`:
- Preflight checks critical files/path alias.
- Launches runner process, polls progress, writes heartbeat.
- Recovery controls:
  - max runner restarts (`TFE_ORACLE_MAX_RUNNER_RESTARTS`, default 3)
  - deterministic failure signature repeat cap (`TFE_ORACLE_MAX_DETERMINISTIC_SIGNATURE_REPEATS`, default 2)
- Timeout controls:
  - cycle timeout
  - no-progress timeout (effective timeout >= runner timeout + 120 sec)

Output summary includes:
- target metric id
- requested/actual additional runs
- best score
- target met boolean
- latest epoch schema and status
- session log path + state snapshot path

### 4.3 Gate enforced in refresh wrapper

If oracle ran, refresh wrapper hard-fails unless:
- `best_score >= target_return_lift_pct` (default target 4.0)
- `epoch_library_confidence_schema == "v1"`

## 5. Runtime Sync and Validation Contract

### 5.1 Runtime sync

`web/scripts/sync_runtime_postgres.mjs`:
- Reads `uf_snapshot.json` + `web/data/screener-quote-cache.json`.
- Dedupe snapshot rows by ticker (bar_count/price/stability tie-break ordering).
- Rebuilds runtime tables each run:
  - `runtime_decisions_latest`
  - `runtime_symbols`
  - `runtime_metrics_latest`
  - `runtime_bars_daily`
- Upserts `runtime_refresh_runs` row with optimizer and epoch fields from env.

### 5.2 Validation gate

`web/scripts/run_validation_gate_v1.mjs`:
- Performs runtime freshness and data checks.
- Optional API filter behavior checks with sign-in.
- Persists results to `runtime_validation_reports`.
- Refresh wrapper requires final validation `status=pass`.

## 6. Advisor Layer (Recommendations + Portfolio)

### 6.1 Runtime snapshot/quote load path

`web/src/lib/runtime-postgres.ts`:
- Source is Postgres when `TFE_RUNTIME_DATA_SOURCE=postgres`.
- Reads from:
  - `runtime_decisions_latest` (snapshot rows)
  - `runtime_symbols` (quote/profile rows)
- Has in-memory cache TTL and retry controls.
- If fresh read fails, stale cache fallback can be used within max-stale window.

### 6.2 Decisioning contract used by advisor APIs

`web/src/lib/uf-snapshot.ts`:
- Converts snapshot row to structural basis.
- Rebuilds candidate PSCF keys and matches against loaded runtime policy (`pscf_policy_runtime.json` or fallback).
- Returns one decision with provenance:
  - policy-matched decision (`PSCF_POLICY_DECISION`)
  - fallback hold reason codes:
    - `PSCF_FALLBACK_INSUFFICIENT_BARS`
    - `PSCF_FALLBACK_STRUCTURAL_INCOMPLETE`
    - `PSCF_FALLBACK_POLICY_MISSING`
    - `PSCF_FALLBACK_CELL_KEY_UNAVAILABLE`
    - `PSCF_FALLBACK_CELL_UNMAPPED`
    - `PSCF_FALLBACK_ANOMALOUS` (if anomaly fallback enabled)

### 6.3 Recommendations API behavior

`web/src/app/api/recommendations/list/route.ts`:
- Requires authenticated user.
- Hard 503 if snapshot load fails/unavailable/invalid timestamp or quote cache unavailable.
- Computes recommendation health gates:
  - coverage minimum (`TFE_RECOMMENDATIONS_POLICY_COVERAGE_MIN`)
  - fallback maximum (`TFE_RECOMMENDATIONS_POLICY_FALLBACK_MAX`)
- Computes freshness gate:
  - stale if age_minutes > `TFE_RECOMMENDATIONS_MAX_AGE_MINUTES`
- Serving policy is fail-closed for investor-facing recommendations:
  - freshness is a hard gate
  - `validation_status` must be `pass`
  - `snapshot_publication_id` and `quote_publication_id` are required
  - `quote_binding_status` must be `aligned`
  - runtime run mismatches are blocking (`run_mismatch`)
- If any serving-policy gate fails, API returns explicit blocking payload (`status="blocked"`, `blocked=true`, 503) and does not return recommendation lists.
- Quality-gate misses remain observable via health alerts; they do not override serving-policy hard gates.
- v2.6 governance adoption override: this fail-closed rule supersedes older v2.5 strict-mode-off/degraded-serving language for investor-facing outputs.

### 6.4 Portfolio advisor behavior

`web/src/app/api/portfolio/route.ts`:
- Uses runtime snapshot + quote cache + live price map.
- Applies the same canonical investor-serving policy gate used by Recommendations before any positions, benchmark, allocator, or rebalance outputs are built.
- If the canonical serving policy fails, API returns explicit blocking payload (`status="blocked"`, `blocked=true`, 503) and does not return portfolio analytics outputs.
- Builds position decisions from same `decisionInfoFromRow` contract.
- Allocator method: `PFSC_STRUCTURAL_ALLOCATOR_V1`.
- Action set: `BUY_MORE`, `TRIM`, `EXIT`, `HOLD`.
- Core rules:
  - `Avoid` -> target 0 -> `EXIT`
  - `Accumulate` score = confidence
  - `Hold` score = confidence * 0.5
  - fallback-unmapped hold suppresses buy-more
  - trim on accumulate is suppressed (`ALLOW_TRIM_WHEN_DECISION_IS_ACCUMULATE=false`)
  - rebalance threshold = 1.0 pct points drift

### 6.5 Advisor quality/probe tooling

- `web/src/app/api/admin/recommendation-quality/route.ts` exposes latest quality audit summary and winner gates.
- `web/scripts/portfolio_advisor_confidence_probe.mjs` runs browser/API checks for portfolio advisor contract and provenance fields.
- `tools/run_portfolio_advisor_confidence_probe_lane.sh` automates probe lane including temporary admin user creation/cleanup.

### 6.6 Admin command deck serving-policy alignment

`web/src/app/api/admin/system-status/route.ts`:
- Uses the same canonical investor-serving policy gate as Recommendations and Portfolio.
- `refreshPolicy.healthy` is anchored to canonical investor-serving-policy validity.
- Admin reports `Action Needed` for the same blocking reasons (`stale`, `validation_failed`, `missing_publication_ids`, `quote_binding_not_aligned`, `run_mismatch`) and does not remain red solely due stale file/log artifacts when live serving policy is valid.

## 7. Current Explicit Optimization/Control Knobs

### 7.1 Refresh + oracle wrapper knobs

Key env vars in `run_refresh_with_l5_learning.py`:
- Refresh resume/checkpoint:
  - `TFE_REFRESH_RESUME_FROM_CHECKPOINT`
  - `TFE_REFRESH_RESUME_CHECKPOINT_DIR`
  - `TFE_REFRESH_RESUME_S3_URI`
  - `TFE_REFRESH_RESUME_MAX_AGE_SECONDS`
- Quote/profile refresh:
  - `TFE_REFRESH_REBUILD_QUOTE_CACHE`
  - `TFE_QUOTE_CACHE_WORKERS`
  - `TFE_QUOTE_CACHE_TIMEOUT_SEC`
  - `TFE_QUOTE_CACHE_SAVE_EVERY`
  - `TFE_QUOTE_CACHE_MIN_NON_META_FIELDS`
  - `TFE_REFRESH_BUILD_PROFILE_OVERRIDES`
  - `TFE_PROFILE_OVERRIDE_WORKERS`
  - `TFE_PROFILE_OVERRIDE_TIMEOUT_SEC`
  - `TFE_PROFILE_OVERRIDE_SAVE_EVERY`
  - `TFE_PROFILE_OVERRIDE_LIMIT`
- Oracle short-cycle:
  - `TFE_REFRESH_ORACLE_TRIGGER_POLICY`
  - `TFE_REFRESH_ORACLE_ALLOW_SHORT_CYCLE`
  - `TFE_REFRESH_ORACLE_SHORT_CYCLE_RUNS`
  - `TFE_REFRESH_ORACLE_TIMEOUT_SECONDS`
  - `TFE_REFRESH_ORACLE_POLL_SECONDS`
  - `TFE_REFRESH_ORACLE_NO_PROGRESS_TIMEOUT_SECONDS`

### 7.2 L5 learning knobs

Key env vars in `l5_policy_learning_pipeline.py`:
- Mode/source:
  - `TFE_POLICY_SOURCE_MODE`
  - `TFE_POLICY_EVAL_MODE`
  - `TFE_L5_POLICY_IO_MODE`
- Cell/key behavior:
  - `TFE_POLICY_CD_BUCKET_EDGES`
  - `TFE_POLICY_CD_REGIME_MODE`
  - `TFE_POLICY_INCLUDE_STABILITY_BUCKET`
  - `TFE_POLICY_IRF_MODE`
  - `TFE_POLICY_SPIDER_EYES_MODE`
- Selection and guards:
  - `TFE_POLICY_SELECTION_OBJECTIVE`
  - `TFE_POLICY_MIN_ACTION_EDGE`
  - `TFE_POLICY_MIN_ACTION_MARGIN`
  - `TFE_POLICY_MIN_ACTION_WINRATE_PCT`
  - `TFE_POLICY_HORIZON_WEIGHTS`
- Merge/promotion:
  - `TFE_POLICY_MIN_PRIMARY_CELL_SAMPLES`
  - `TFE_POLICY_AUTO_PROMOTE`
  - `TFE_POLICY_HORIZON_DECISION_OVERRIDES_PATH`
- Timeouts/sampling:
  - `TFE_POLICY_REPLAY_SYMBOL_TIMEOUT_SECONDS`
  - `TFE_POLICY_EVAL_SYMBOL_TIMEOUT_SECONDS`
  - `TFE_POLICY_SYMBOL_TIMEOUT_CHECK_INTERVAL_BARS`
  - `TFE_POLICY_STATE_COMPUTE_TIMEOUT_SECONDS`
  - `TFE_POLICY_REFRESH_CANDIDATE_SAMPLE_ON_TARGETED`
  - `TFE_POLICY_REFRESH_CANDIDATE_SAMPLE_SIZE`
  - `TFE_POLICY_REFRESH_CANDIDATE_SAMPLE_SEED`

### 7.3 Advisor/runtime knobs

- Runtime postgres loader:
  - `TFE_RUNTIME_DATA_SOURCE`
  - `TFE_RUNTIME_POSTGRES_CACHE_TTL_MS`
  - `TFE_RUNTIME_POSTGRES_CACHE_MAX_STALE_MS`
  - `TFE_RUNTIME_POSTGRES_READ_RETRY_ATTEMPTS`
  - `TFE_RUNTIME_POSTGRES_READ_RETRY_DELAY_MS`
- Decision fallback behavior:
  - `TFE_RECOMMENDATIONS_MIN_BARS`
  - `TFE_RECOMMENDATIONS_ANOMALY_FALLBACK`
  - `TFE_PSCF_POLICY_PATH`
- Recommendations endpoint gates:
  - `TFE_RECOMMENDATIONS_SNAPSHOT_TIMEOUT_MS`
  - `TFE_RECOMMENDATIONS_POLICY_COVERAGE_MIN`
  - `TFE_RECOMMENDATIONS_POLICY_FALLBACK_MAX`
  - `TFE_RECOMMENDATIONS_MAX_AGE_MINUTES`
- Portfolio endpoint:
  - `TFE_PORTFOLIO_SNAPSHOT_TIMEOUT_MS`

## 8. Practical Classification of Current L5 Path

Based on current implementation boundaries:
- L5 is currently a cell-mapped policy layer built from serialized structural features and evaluated against SPY-relative outcomes.
- Promotion is non-regression gated across horizons plus mapping-rate non-degradation.
- Advisor surfaces consume runtime snapshot rows + policy key matching with explicit fallback contract.

Operationally this is a pragmatic, productionized policy runtime with explicit gates and fallbacks, not an unconstrained heuristic path.

## 9. Strict Function-by-Function Lineage Appendix (L4 -> L5 -> Advisor)

This appendix is a strict runtime lineage map from UF structural outputs to L5 policy use and then advisor outputs.

### 9.1 Canonical replay lineage (refresh/runtime path)

1. UF-Core structural state is computed:
   - `uf_core/uf_structural_engine.py:245` `compute_uf_structural_state(close)`
   - Produces:
     - `level3.regime`
     - `level4.S_UF`, `level4.R_UF`, `level4.stability_score`, `level4.max_drawdown`
     - `level5.decision_vector`, `level5.D_k`, `level5.M_k`, `level5.R_rev_k`, `level5.U_star_k`, `level5.C_k`, `level5.P_k`, `level5.B_k`
     - `level5.decision_guard`, `level5.hardening`

2. UF state is flattened for snapshot row creation:
   - `uf_core/uf_structural_engine.py:431` `compute_structural_state(symbol, bars)`
   - Carries the same L3/L4/L5 fields into flat dict keys used by snapshot builders.

3. Snapshot row is materialized per symbol:
   - `uf_mdg_snapshot.py:202` `evaluate_symbol_snapshot(...)`
   - Calls `compute_structural_state` at `uf_mdg_snapshot.py:282`
   - Emits one row containing `regime`, `S_UF`, `R_UF`, `stability_score`, `decision_vector`, `D_k..B_k`, `decision_guard`, `bar_count`.

4. Snapshot rebuild writes the row-set to runtime snapshot artifact:
   - `rebuild_uf_snapshot.py:620` `rebuild_snapshot(...)`
   - Appends rows at `rebuild_uf_snapshot.py:754`
   - Writes SES envelope via `_save_snapshot_envelope` at `rebuild_uf_snapshot.py:787`

5. Runtime bridge sync pushes snapshot rows into Postgres runtime tables:
   - `web/scripts/sync_runtime_postgres.mjs:415` `main()`
   - Dedupe rows via `dedupeSnapshotRows` (`web/scripts/sync_runtime_postgres.mjs:243`)
   - Inserts `runtime_decisions_latest`, `runtime_symbols`, `runtime_metrics_latest`, `runtime_bars_daily`.

6. L5 replay policy generation recomputes UF state from validation dataset bars:
   - `l5_policy_learning_pipeline.py:273` `_compute_uf_state_guarded(...)` calls `compute_uf_structural_state`
   - `l5_policy_learning_pipeline.py:538` `_level5_l4_components(...)` extracts `D/M/R/U/C/P/B`
   - `l5_policy_learning_pipeline.py:601` `_state_cell_key(...)` and `:638` `_state_cell_key_candidates(...)` build cell keys
   - `l5_policy_learning_pipeline.py:1553` `_generate_policy_from_replay_dataset(...)` scores decisions per cell

7. L5 candidate assembly and gating:
   - `l5_policy_learning_pipeline.py:1773` `_merge_policies(...)`
   - `l5_policy_learning_pipeline.py:1867` `_overlay_anomaly_profiles(...)`
   - `l5_policy_learning_pipeline.py:2154` `_evaluate_policy(...)`
   - `l5_policy_learning_pipeline.py:2534` `_compare_candidate_vs_current(...)` promotion gates
   - `l5_policy_learning_pipeline.py:2876` `run_l5_policy_learning(...)` orchestrates full L5 cycle

8. Refresh wrapper executes gating and runtime publish:
   - `run_refresh_with_l5_learning.py:710` `_run_oracle_optimizer_short_cycle(...)`
   - `run_refresh_with_l5_learning.py:865` `_resolve_oracle_execution_plan(...)`
   - `run_refresh_with_l5_learning.py:593` `_run_runtime_postgres_sync(...)`
   - `run_refresh_with_l5_learning.py:655` `_run_validation_gate(...)`

9. Advisor APIs read runtime rows and derive user-visible decisions:
   - Runtime load: `web/src/lib/runtime-postgres.ts:596` `loadRuntimeSnapshotRowsFromPostgres()` and `:631` `loadRuntimeQuoteCacheFromPostgres()`
   - Decision mapping: `web/src/lib/uf-snapshot.ts:383` `resolveStructuralBasis(...)` -> `:550` `pscfCellKeyCandidatesFromRow(...)` -> `:671` `policyDecisionFromRow(...)`
   - Public decision surface: `web/src/lib/uf-snapshot.ts:921` `decisionInfoFromRow(...)`
   - Recommendations response shaping: `web/src/app/api/recommendations/list/route.ts:89` `toRecommendationRow(...)` and `:317` `GET(...)`
   - Portfolio advisor shaping: `web/src/app/api/portfolio/route.ts:344` `aggregatePositions(...)`, `:185` `buildAllocatorPlan(...)`, and `:470` `GET(...)`

### 9.2 Row-trace lineage (L4 snapshot export -> L5 row-trace policy path)

1. Row-trace exporter computes UF structural state per rolling window:
   - `real_world_cleaned_universe_l5_row_trace_export.py:404` calls `compute_uf_structural_state(close_series)`
   - Extracts `C_k` via `extract_c_k(...)` at `real_world_cleaned_universe_l5_row_trace_export.py:143` and call site `:415`
   - Writes `real_world_cleaned_universe_l5_row_trace_full.csv` at `:321` with `decision_timestamp`, `regime`, `D/M/R_rev/U_star/C_k/P/B`, `forward_return`.

2. L5 row-trace policy generation consumes that CSV:
   - `l5_policy_learning_pipeline.py:1400` `_generate_policy_from_row_trace(...)`
   - Cell key construction from CSV row via `_row_trace_cell_key(...)` (`:462`) and candidate variants (`:490`)
   - SPY benchmark alignment via `_spy_forward_return(...)`

3. Row-trace evaluation path uses same candidate matching mechanics:
   - `l5_policy_learning_pipeline.py:2374` `_evaluate_policy_rowtrace(...)`

### 9.3 Field-level lineage map (strict)

UF structural output fields -> L5/advisor consumption boundaries:

- `regime`
  - produced: `uf_core/uf_structural_engine.py:380`/`:431`
  - used for keying: `l5_policy_learning_pipeline.py:462`, `:601`, `web/src/lib/uf-snapshot.ts:383`

- `S_UF`, `R_UF`, `stability_score`
  - produced: `uf_core/uf_structural_engine.py:380-384`/`:431`
  - used for key enrichment/buckets: `l5_policy_learning_pipeline.py:474-476`, `:616-618`
  - used for advisor confidence: `web/src/app/api/recommendations/list/route.ts:95`, `web/src/app/api/portfolio/route.ts:214`

- `decision_vector`, `D_k`, `M_k`, `R_rev_k`, `U_star_k`, `C_k`, `P_k`, `B_k`
  - produced: `uf_core/uf_structural_engine.py:387-395`/`:431`
  - flattened in snapshot row: `uf_mdg_snapshot.py:333-340`
  - consumed by L5 key extractor: `l5_policy_learning_pipeline.py:538-594`
  - consumed by advisor key extractor: `web/src/lib/uf-snapshot.ts:383-548`

- `decision_guard`, `hardening` flags
  - produced: `uf_core/uf_structural_engine.py:398-410`
  - used in L5 anomaly accounting: `l5_policy_learning_pipeline.py:1921-1947`
  - used in advisor anomaly fallback path: `web/src/lib/uf-snapshot.ts:611-669`, `:751-771`

### 9.4 L5 -> advisor publication boundaries

1. Runtime policy artifact publication:
   - file promotion path: `l5_policy_learning_pipeline.py:2848` `_atomic_promote(...)`
   - postgres persistence path: `l5_policy_learning_pipeline.py:2756` `_persist_l5_outputs_to_postgres(...)`

2. Advisor policy read path:
   - policy load bootstrap: `web/src/lib/uf-snapshot.ts:262` `loadPscfPolicyRuntime()`
   - decision fallback reason codes emitted in `policyDecisionFromRow(...)` (`web/src/lib/uf-snapshot.ts:671`)

3. Advisor response outputs:
   - Recommendations list includes:
     - `decision`, `decisionReason`, `decisionReasonCode`, `fallbackUsed`, `fallbackReason`, policy key provenance
     - built in `web/src/app/api/recommendations/list/route.ts:89`
   - Portfolio API includes:
     - position decision fields + allocator action/reason rows
     - built by `aggregatePositions(...)` (`web/src/app/api/portfolio/route.ts:344`) and `buildAllocatorPlan(...)` (`:185`)

### 9.5 Explicit current loss/transform points (for conformance diagnosis)

1. Snapshot runtime bridge currently inserts null decision-provenance columns in `runtime_decisions_latest` and keeps full snapshot row in `snapshot_row_json`:
   - `web/scripts/sync_runtime_postgres.mjs` insert block starting near `:470`
   - advisor decision provenance is recomputed at request time from `snapshot_row_json` + runtime policy, not read from precomputed DB reason fields.

2. Row-trace path stores forward outcomes in CSV and rebuilds policy cells from serialized rows:
   - exporter write path `real_world_cleaned_universe_l5_row_trace_export.py:321-522`
   - learner ingest path `l5_policy_learning_pipeline.py:1400-1549`

3. Runtime policy matching uses candidate-key fallback chains (multiple key variants), not a single exact key:
   - L5: `l5_policy_learning_pipeline.py:490`, `:638`
   - advisor: `web/src/lib/uf-snapshot.ts:550`
