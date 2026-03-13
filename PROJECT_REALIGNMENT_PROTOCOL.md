# Project Realignment Protocol (Model-Technical)

Generated (UTC): 2026-02-23T02:55:07Z
Repository: `/workspaces/Tao_Financial_Engine`
Audience: ChatGPT/GPT-5.3 Codex runtime agent (not end-user)

## 1. Purpose
This protocol is the anti-drift canonical state document for future chats. Its role is to prevent repo hallucination, preserve verified constraints, and force evidence-backed execution.

## 2. Non-Negotiable Behavioral Rules
1. Do not infer project structure from memory.
2. Do not claim completion/deployment/performance without file evidence.
3. Use `TFE_TODO_LIST.md` as status source-of-truth.
4. Preserve approved exceptions unless user explicitly reverses.
5. Keep single-step execution focus; do not silently scope-creep.
6. Mark claims as VERIFIED/UNVERIFIED.

## 3. Canonical Project Context
### 3.1 Recommendation engine contract
- Policy-first decisioning is enforced.
- UF structural adapter is transport/display; policy logic stays in PSCF/L5.
- One explicit fallback decision is `Hold`.
- Full L4 completeness required for policy mapping: `D_k, M_k, R_rev_k, U_star_k, C_k, P_k, B_k`.

### 3.2 Live key schema (current)
The active key space in training/eval/live mapping includes:
- Base structural key: `reg + D + M_sign + R_rev + U_bucket + C + P_bucket + B_sign`
- Enrichment key parts: `S_bucket3`, `R_bucket3`, optional `CD_bucket_opt`
- Optional IRF segment: `|PH=...`
- Optional Spider-Eyes section-23 segment: `|SE=...`

Current SE tags in runtime keys:
- `NONE`
- `GU` (guard gate unlock)
- `HO` (hardening hysteresis overload)
- `GU_HO` (both)

### 3.3 Fallback/anomaly behavior
Fallback reasons are explicit and surfaced:
- insufficient bars
- structural incomplete
- policy missing
- key unavailable
- cell unmapped
- anomalous row

## 4. Verified Artifacts and Metrics (Current)
### 4.1 Item-10 completeness (C_k + IRF + Spider-Eyes)
VERIFIED by:
- `backups/item10_spider_eyes_enablement_latest.json`
- `backups/runtime/l5_policy_learning/l5-policy-learning-report-20260223T014140Z.json`

Runtime policy summary:
- `cells_total=1156`
- `cells_with_irf_phase_key=301`
- `cells_with_spider_eyes_key=163`

### 4.2 Strict conformance
VERIFIED by:
- `backups/recommendation_policy_conformance_latest.json`

Key values:
- `strict.pass=true`
- `mapped_decision_mismatch_count=0`
- `decision_counts={Hold:8002, Accumulate:2162, Avoid:655}`
- `coverage_rate=0.5974674184305389`
- `fallback_rate=0.40253258156946115`

### 4.3 Frozen 5-year backtest snapshot
VERIFIED by:
- `l5_backtest_vs_spy_5y.json`

Key values:
- `avg_outcome_over_index_pct=37.74658945922073`
- `goal_gt_65pct_met=false`
- `spy_5y_return_pct=75.07627618388331`

### 4.4 Oracle optimizer persistent state
VERIFIED by:
- `backups/runtime/oracle_program/last_heartbeat.json`
- `backups/runtime/oracle_program/sessions/short_25_20260223T015950Z.json`

Key values:
- `phase=short_cycle_complete`
- `completed=1024`
- `latest_run_id=1026`
- `latest_score=65.16585513368082`
- `best_score=65.84995589389956`
- `requested_additional_runs=25`
- `actual_additional_runs=26`

### 4.5 Recent constrained sweeps
VERIFIED by:
- `backups/g32_horse_race_mom_irf_win65_20260223T021350Z.json`
- `backups/g32_horse_race_mom_irf_plateau_probe_20260223T023437Z.json`

Results:
- Winrate-constrained run (`records_evaluated=1800`) best outcome score: `65.04705114897789`
- Plateau-probe run (`records_evaluated=864`) best outcome score: `65.16585513368082`
- Neither exceeded baseline plateau: `65.84995589389956`

## 5. Math/Scoring Canonicalization
### 5.1 Primary legacy optimizer score used in reports
- `legacy_outcome_score` = average of `outcome_over_index_pct` across configured horizons.
- In current MoM+IRF horse-race reports, horizon set used in summary is 5/20/60.

### 5.2 Objective metric in horse-race artifacts
- `objective_metric = avg_return_multiple_over_spy_pct_log_v2_mom_irf_v1`
- Reported as `g32_best_symbol_return_multiple_over_spy_pct`.

### 5.3 Critical plateau observation
The h5 reconciliation changed the control rule:

- Treat eval_temporal_walkforward.py as the source of truth for gate status.
- Treat build_rowtrace_backfill_plan.py as advisory only until its math is unified with the evaluator.

Do not run any new model-family comparisons yet.

Next single task:
Discover and lock the provenance tuple needed for one raw-regeneration canary.

Build/execute:
discover_locked_provenance.py

Goal:
Recover, with evidence, the best candidate values for:
- market_data_version
- kernel_version
- adapter_config_hash
- lookback_window_rules

Search sources in this order:
1. existing row-trace manifests
2. temporal dataset manifests
3. runtime policy manifests / JSON metadata
4. archived snapshot manifests
5. historical config files
6. git tags / commit metadata / release notes
7. any provenance fields already embedded in prior artifacts

Output:
provenance_candidate_report_latest.json

Required contents:
- candidate value for each of the 4 fields
- source file/path for each candidate
- confidence level: exact / inferred / missing
- conflict list if multiple values disagree
- recommendation: canary-safe or not-canary-safe

Rules:
- Do NOT invent or guess missing provenance values.
- If any field is ambiguous, surface the ambiguity and stop.
- Only if all 4 fields are exact and consistent, prepare one path C canary command.

If canary-safe:
Run exactly one raw-regeneration canary on a contiguous historical block that adds multi-horizon timestamps (h5/h20/h60), not a random date sample.

Canary outputs:
- rowtrace_backfill_regenerated_raw_manifest_latest.json
- overlap_comparison_latest.json
- merge manifest
- rerun:
  - temporal_dataset_audit_latest.json
  - temporal_walkforward_eval_latest.json

Acceptance criteria:
1. overlap rows match existing converted/snapshot-derived rows exactly or within declared tolerances
2. no unexplained field drift
3. provenance manifest complete
4. timestamp depth improves as expected
5. denominator parity remains 0 failures

Also:
Patch the planner after the canary so its required_additional_timestamps calculation is derived from the evaluator’s exact split/gate logic. We should not keep two inconsistent gate calculators.

## 6. Plateau Diagnosis State
VERIFIED:
- Historical best run config from `/tmp/g32_mom_irf_loop/results.jsonl`:
  - `run_id=10`, `best_score=65.84995589389956`
  - config: `min_samples=1`, `min_s_uf=0.1`, `min_decision_edge=0.0005`, `min_action_winrate_pct=0`, `uncertainty_penalty=0.0`, `hold_bias=0.0005`
- Best-run horizon profile from `/tmp/g32_mom_irf_loop/runs/momirf_0010_20260220T050755Z/report.json`:
  - h5 outcome ≈ `96.7992`
  - h20 outcome ≈ `98.6299`
  - h60 outcome ≈ `2.1207`

Interpretation (VERIFIED+INFERENCE):
- h60 underperformance is the dominant bottleneck preventing break above `65.84995589389956`.

## 7. TODO Alignment (Current)
Source of truth: `TFE_TODO_LIST.md`.

Recommendation corrections list status:
- Items 1-10: `DONE`.

Broader active queue still contains open/partial work outside recommendation-correction closure.

## 8. Approved Exceptions (Do Not Revoke Implicitly)
From `TFE_TODO_LIST.md`:
- Section-23 enforcement activation in TFE runtime: EXCEPTION (monitor-only accepted).
- SafeMode forced enforcement in live runtime: EXCEPTION (monitor-only accepted).
- SCE KAT/NIST/Dieharder runtime gating in TFE path: EXCEPTION (out-of-scope unless reversed).

## 9. Incomplete Critical Technical Tasks
1. Run a dedicated horizon-60-targeted optimizer pass.
2. Measure whether horizon-60 uplift can raise aggregate score above `65.84995589389956`.
3. Re-run the frozen 5-year summary after adopting any better config.
4. Keep prod hold until optimizer plateau is either broken or explicitly accepted by user.

## 10. Next Chat Re-Entry Procedure
1. Load files in `LOAD_DIRECTIVE_NEXT_CHAT.md` order.
2. Recompute/verify the three key numbers first:
- best optimizer score
- latest optimizer score
- 5-year aggregate outcome-over-index
3. Continue with only one execution item at a time.
4. If any metric differs from this protocol, immediately mark prior claim stale and refresh protocol.

## 11. Hard Anti-Hallucination Clause
If a needed fact is not in loaded files, do not infer it.
- Ask for permission to gather missing evidence, then gather it.
- Do not make schema assumptions.
- Do not claim any deploy readiness without explicit evidence artifact.
