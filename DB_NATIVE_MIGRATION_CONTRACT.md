# DB-Native Migration Contract (L5 First)

Generated (UTC): 2026-03-03T14:40:30Z  
Workspace: /workspaces/Tao_Financial_Engine

## 1) Purpose
This is the operating contract for moving TFE from file-first to database-centric execution, starting at L5 input/eval/promotion.

This contract is resume-safe. If a chat freezes, a new chat can continue from this document plus `LOAD_DIRECTIVE_NEXT_CHAT.md`.

## 2) Scope Order (Do Not Reorder)
1. L5 policy runtime/eval path (`l5_policy_learning_pipeline.py`) to DB-native IO.
2. L5 input datasets (row trace + validation datasets) to DB tables.
3. Upstream refresh artifacts to DB-native history and diagnostics.
4. Runtime/UI confidence and visual acceptance checks.

## 3) Current vs Target Map (L5 First)

### L5 Phase-1 (Now)
1. Current artifact: `pscf_policy_runtime.json`  
   Target table: `l5_policy_runtime_current.policy_json`  
   Status: Implemented (strict ECS postgres preflight passes; forced-bad-file-path runtime policy resolution returns Postgres source; runtime policy write/readback proof passes)

2. Current artifact: `backups/runtime/l5_policy_learning/l5-policy-learning-report-*.json`, `l5_policy_learning_latest.json`  
   Target table: `l5_policy_eval_runs` (`comparison_json`, `promotion_json`, `coverage_json`, `notes_json`, `artifact_paths_json`)  
   Status: Implemented (eval run summary persistence and readback proof pass in strict `postgres` mode with bounded ECS evidence)

3. Current artifact: `policy_horizon_overrides.json`  
   Target table: `l5_policy_horizon_overrides` + `l5_policy_horizon_override_cells`  
   Status: Implemented (Postgres-first resolver in `hybrid/postgres` with strict fail-closed behavior, and forced-bad-file-path DB resolution proof is passing)

### L5 Phase-2
4. Current artifact: `real_world_cleaned_universe_l5_row_trace_full.csv`  
   Target table: `l5_rowtrace_events`  
   Status: Implemented (resolver is Postgres-first in `hybrid/postgres` with strict fail-closed behavior; strict ECS postgres preflight confirms non-empty rowtrace dataset and forced-bad-file-path DB-only resolution proof passes)

5. Current artifact: `backups/strict-ab-frozen-dataset-*.json`  
   Target table: `l5_validation_datasets` + `l5_validation_dataset_rows`  
   Status: Implemented (L5 pipeline resolves validation + SPY benchmark from Postgres in `hybrid/postgres`; strict mode fails closed if DB preflight/read fails; strict ECS preflight and forced-bad-file-path DB-only proof are passing)

6. Current artifact: `backups/pscf-policy-anomaly-watch-*.json`  
   Target table: `l5_anomaly_watch_policies` + `l5_anomaly_watch_cells`  
   Status: Implemented (sync tool and strict Postgres resolver are active; deterministic fail was repaired in bounded cycle; forced-bad-file-path DB-only proof is passing)

Phase-2 sync command (bounded, no refresh run):
- `python3 tools/l5_phase2_sync_postgres.py`

### Upstream / Runtime Phase
7. Current artifact: `uf_snapshot.json`  
   Target tables: `runtime_decisions_latest`, `runtime_symbols`, `runtime_metrics_latest`, `runtime_bars_daily`  
   Status: Implemented via `web/scripts/sync_runtime_postgres.mjs`

8. Current artifact: `web/data/screener-quote-cache.json`  
   Target tables: `runtime_symbols.profile_json`, `runtime_metrics_latest.metrics_json`, `runtime_bars_daily`  
   Status: Implemented via runtime sync bridge

9. Current artifact: `uf_snapshot_rebuild_report.json`, refresh lifecycle metadata  
   Target table: `runtime_refresh_runs`  
   Status: Implemented

10. Current artifact: `validation-report-v1.json`  
    Target: keep file for deploy gate + add DB history table `runtime_validation_reports`  
    Status: Implemented (validation gate now writes per-run history rows in `runtime_validation_reports`, and deploy/refresh validation executions persist with strict fail-closed behavior on history write)

## 4) Mandatory Controls (Blocking)
1. No blind reruns.
2. One long refresh run per code change.
3. Deterministic failure signature stop rule.
4. Preflight must pass before any long run.
5. Resume checkpoints must be used for safe restart.
6. No closure claims without fresh evidence artifacts.

## 5) Deterministic Failure Stop Rules
Stop immediately and patch code first if any repeats on unchanged code:
1. `short cycle no-progress timeout`
2. `FileNotFoundError: Missing runner`
3. `PermissionError` on known deterministic paths
4. missing/invalid validation report contract
5. monitor loop condition bug (for example null run-id query loop)

## 6) Safe Restart Rules
Use wrapper resume checkpoints; do not restart from zero by default.

Required behavior:
1. Resume from `post_l5_pre_oracle` checkpoint when present and fresh.
2. Archive/clear checkpoint only on terminal success or explicit abort reason.
3. If restart loop exceeds bounded attempts, stop and report exact blocker.

## 7) Preflight Protocols (Before Long Run)
Run both:
1. `python3 tools/refresh_failure_protocol.py --validation-probe-mode ecs`
2. `python3 tools/l5_db_native_preflight.py --mode ${TFE_L5_POLICY_IO_MODE:-file}`
3. `python3 tools/run_l5_db_native_preflight_in_ecs_network.py --cluster tfe-web-cluster --service tfe-web-service-lb --mode postgres`

Both must pass, or execution is blocked.

## 8) Diagnostic Rules for Long-Run/Time-Consuming Work
1. Every monitor loop must have bounded `max_polls`.
2. Fail fast when required identifiers are missing (for example `run_id`).
3. Record terminal reason explicitly (`success`, `deterministic_failure`, `max_polls_exhausted`, `invalid_input`).
4. Never continue polling after terminal state is known.

## 9) Validation Gates (Technical)
Required pass set for promotion/deploy:
1. L5 preflight pass (`tools/l5_db_native_preflight.py`).
2. Refresh failure protocol pass (`tools/refresh_failure_protocol.py`).
3. Runtime validation gate pass (`web/scripts/run_validation_gate_v1.mjs` or ECS probe wrapper).
4. Deploy strict gate pass (`tools/deploy_to_prod_with_evidence.sh`).

## 10) Validation Gates (Visual / Page Confidence)
Manual authenticated checks are required before any “confidence complete” claim:
1. Recommendations: freshness + provenance sanity.
2. Screener: tab/filter/view behavior + latency sanity.
3. Watchlist: correctness parity.
4. Portfolio/Advisor: metric integrity and advisor explainability.
5. Admin Refresh Log: lifecycle clarity and readability.
6. Home page: UX acceptance for layout/timing/color/content coherence.

Minimum evidence per page:
1. One screenshot.
2. One API payload sample or route response snippet.
3. One explicit pass/fail judgment.

## 11) L5 DB-Native Execution Modes (Contract)
`TFE_L5_POLICY_IO_MODE` values:
1. `file`: file read/write only.
2. `hybrid`: prefer Postgres; fallback to file when Postgres is unavailable/empty.
3. `postgres`: strict Postgres only; fail if preflight or runtime policy row is missing.

## 12) Resume Procedure If Chat Freezes
1. Confirm workspace and latest artifacts:
   - `pwd`
   - `ls -la backups/runtime | tail -n 40`
2. Read:
   - `AGENTS.md`
   - `LOAD_DIRECTIVE_NEXT_CHAT.md`
   - `DB_NATIVE_MIGRATION_CONTRACT.md`
   - `TFE_TODO_LIST.md`
3. Run preflights:
   - `python3 tools/refresh_failure_protocol.py --validation-probe-mode ecs`
   - `python3 tools/l5_db_native_preflight.py --mode ${TFE_L5_POLICY_IO_MODE:-file}`
4. If preflight fails: patch and rerun preflight only.
5. If preflight passes: run exactly one long run per code change.
6. Record evidence path updates in TODO + load directive.

## 13) Current Phase Exit Criteria
Current phase (L5 DB-native input/eval first) is complete only when:
1. L5 policy read path supports strict Postgres mode with fail-fast preflight.
2. L5 promotion and eval summaries persist to Postgres tables with evidence.
3. Preflight protocol passes in strict `postgres` mode.
4. One bounded refresh + validation + deploy path passes with no loop behavior regressions.

Current phase completion evidence (2026-03-03 UTC):
1. Strict ECS postgres preflight pass: `backups/runtime/l5-db-native-contract-evidence-20260303T020339Z/preflight-ecs-result.json`
2. Phase-2 artifact sync pass in ECS: `backups/runtime/l5-db-native-contract-evidence-20260303T020339Z/phase2-sync-ecs-result.json`
3. Runtime policy + eval summary DB persistence probe pass in ECS: `backups/runtime/l5-db-native-contract-evidence-20260303T020339Z/fast-persistence-ecs-result.json`
4. Anti-loop protocol pass (no long refresh run): `backups/runtime/l5-db-native-contract-evidence-20260303T020339Z/failure-protocol-summary.json`
5. Deploy gate pass on latest rollout: `backups/deploy-evidence-20260303T012411Z/deploy-report.tsv`
6. Consolidated phase status: `backups/runtime/l5-db-native-contract-evidence-20260303T020339Z/contract-summary.json` (`status=pass`)

Upstream hardening evidence (2026-03-03 UTC):
1. Deploy gate pass with anomaly-lane fix patch: `backups/deploy-evidence-20260303T031814Z/deploy-report.tsv` (`taskdef=tfe-web-task:162`) with rollout completion verification in `backups/deploy-evidence-20260303T031814Z/ecs-rollout-verify.json`
2. Deterministic strict-preflight fail captured for anomaly cells contract: `backups/runtime/l5-db-native-upstream-anomaly-fix-20260303T033929Z/preflight-ecs-before-fix-fail.json`
3. Bounded Phase-2 anomaly repair pass in ECS: `backups/runtime/l5-db-native-upstream-anomaly-fix-20260303T033929Z/phase2-anomaly-repair-ecs-result.json`
4. Strict ECS postgres preflight pass after repair: `backups/runtime/l5-db-native-upstream-anomaly-fix-20260303T033929Z/preflight-ecs-after-fix-pass.json`
5. Forced-bad anomaly-policy file path DB-only proof pass with non-empty cells: `backups/runtime/l5-db-native-upstream-anomaly-fix-20260303T033929Z/anomaly-dbproof-ecs-after-fix-pass.json`
6. Consolidated upstream anomaly-fix summary: `backups/runtime/l5-db-native-upstream-anomaly-fix-20260303T033929Z/summary.json`
7. Deploy gate pass with horizon-overrides lane fix patch: `backups/deploy-evidence-20260303T044613Z/deploy-report.tsv` (`taskdef=tfe-web-task:165`) with rollout completion verification in `backups/runtime/l5-db-native-upstream-horizon-fix-20260303T043214Z/ecs-rollout-verify.json`
8. Deterministic strict-preflight fail captured for missing horizon overrides row: `backups/runtime/l5-db-native-upstream-horizon-fix-20260303T043214Z/preflight-ecs-before-fix-fail-taskdef165.json`
9. Bounded Phase-2 horizon-overrides repair pass in ECS: `backups/runtime/l5-db-native-upstream-horizon-fix-20260303T043214Z/phase2-horizon-repair-ecs-result-taskdef165.json`
10. Strict ECS postgres preflight pass after horizon repair: `backups/runtime/l5-db-native-upstream-horizon-fix-20260303T043214Z/preflight-ecs-after-fix-pass-taskdef165.json`
11. Forced-bad horizon-overrides file path DB-only proof pass with non-empty cells: `backups/runtime/l5-db-native-upstream-horizon-fix-20260303T043214Z/horizon-dbproof-ecs-after-fix-pass-taskdef165.json`
12. Consolidated upstream horizon-fix summary: `backups/runtime/l5-db-native-upstream-horizon-fix-20260303T043214Z/summary.json`
13. Deploy gate pass with runtime-validation-history lane patch: `backups/deploy-evidence-20260303T051418Z/deploy-report.tsv` (`taskdef=tfe-web-task:166`) with rollout completion verification in `backups/runtime/validation-history-lane-20260303T052920Z-ecs-rollout-verify.json`
14. Live ECS validation probe pass with DB history persistence check: `backups/runtime/validation-history-lane-20260303T052920Z-ecs-validation.json` (`validation_report_history_persisted=pass`, `table=runtime_validation_reports`)
15. Fresh bounded anti-loop failure protocol pass on taskdef 166: `backups/runtime/failure-protocol-20260303T053124Z/summary.json`
16. Consolidated runtime-validation-history lane summary: `backups/runtime/validation-history-lane-20260303T052920Z-summary.json`
17. Strict ECS postgres preflight pass with non-empty rowtrace dataset (`rowtrace_dataset.row_count=15879`): `backups/runtime/l5-db-native-upstream-rowtrace-fix-20260303T110024Z/preflight-ecs-pass-taskdef166.json`
18. Forced-bad-file-path rowtrace + SPY DB-only proof pass (`rowtrace.source=postgres`, `resolved_row_count=15879`, `spy.source=postgres_validation_dataset`): `backups/runtime/l5-db-native-upstream-rowtrace-fix-20260303T110024Z/rowtrace-spy-dbproof-ecs-pass-taskdef166.json`
19. Active rollout remains completed on task definition `tfe-web-task:166`: `backups/runtime/l5-db-native-upstream-rowtrace-fix-20260303T110024Z/ecs-rollout-verify.json`
20. Fresh bounded anti-loop protocol re-pass after rowtrace proof lane: `backups/runtime/failure-protocol-20260303T110359Z/summary.json`
21. Consolidated rowtrace lane summary: `backups/runtime/l5-db-native-upstream-rowtrace-fix-20260303T110024Z/summary.json` (`status=pass`)
22. Strict ECS postgres preflight pass with non-empty validation dataset (`symbols_count=30`, `spy_points=1254`): `backups/runtime/l5-db-native-upstream-validation-fix-20260303T113505Z/preflight-ecs-pass-taskdef166.json`
23. Forced-bad-file-path validation + SPY DB-only proof pass (`validation.source=postgres`, `symbols_count=30`, `spy.source=postgres_validation_dataset`): `backups/runtime/l5-db-native-upstream-validation-fix-20260303T113505Z/validation-spy-dbproof-ecs-pass-taskdef166.json`
24. Active rollout remains completed on task definition `tfe-web-task:166`: `backups/runtime/l5-db-native-upstream-validation-fix-20260303T113505Z/ecs-rollout-verify.json`
25. Fresh bounded anti-loop protocol re-pass after validation proof lane: `backups/runtime/failure-protocol-20260303T113843Z/summary.json`
26. Consolidated validation-dataset lane summary: `backups/runtime/l5-db-native-upstream-validation-fix-20260303T113505Z/summary.json` (`status=pass`)
27. Strict ECS postgres preflight pass on active task definition before Phase-1 runtime/eval proof: `backups/runtime/l5-db-native-phase1-runtime-eval-fix-20260303T114502Z/preflight-ecs-pass-taskdef166.json`
28. Forced-bad-file-path runtime policy resolve + runtime/eval persistence + readback proof pass (`runtime_policy_resolve.source=postgres`, `runtime_policy_write.status=ok`, `eval_run_write.status=ok`, `eval_readback.row_count=1`): `backups/runtime/l5-db-native-phase1-runtime-eval-fix-20260303T114502Z/runtime-eval-dbproof-ecs-pass-taskdef166.json`
29. Active rollout remains completed on task definition `tfe-web-task:166`: `backups/runtime/l5-db-native-phase1-runtime-eval-fix-20260303T114502Z/ecs-rollout-verify.json`
30. Fresh bounded anti-loop protocol re-pass after Phase-1 runtime/eval proof lane: `backups/runtime/failure-protocol-20260303T115316Z/summary.json`
31. Consolidated Phase-1 runtime/eval lane summary: `backups/runtime/l5-db-native-phase1-runtime-eval-fix-20260303T114502Z/summary.json` (`status=pass`)
32. Strict ECS postgres preflight pass on active task definition before L0 seed/universe proof: `backups/runtime/l0-db-native-universe-lane-20260303T115850Z/preflight-ecs-pass-taskdef166.json`
33. Bounded L0 seed+universe DB ingestion proof pass (`pass=true`, `seed_table_count=3`, `universe_table_total=17042`) on ECS: `backups/runtime/l0-db-native-universe-lane-20260303T115850Z/l0-universe-dbproof-ecs-pass-taskdef166-v7.json`
34. Active rollout remains completed on task definition `tfe-web-task:166`: `backups/runtime/l0-db-native-universe-lane-20260303T115850Z/ecs-rollout-verify.json`
35. Fresh bounded anti-loop protocol re-pass after L0 lane: `backups/runtime/failure-protocol-20260303T121625Z/summary.json`
36. Consolidated L0 seed/universe lane summary: `backups/runtime/l0-db-native-universe-lane-20260303T115850Z/summary.json` (`status=pass`)
37. Strict ECS postgres preflight pass on active task definition before L0 raw/clean bars proof: `backups/runtime/l0-db-native-bars-lane-20260303T122100Z/preflight-ecs-pass-taskdef166.json`
38. Bounded ECS bars-fetch probe pass (`symbol=AAPL`, `bar_count=29`) to verify in-container provider path before bars sync: `backups/runtime/l0-db-native-universe-lane-20260303T115850Z/l0-bars-fetch-probe-ecs.json`
39. Bounded L0 raw/clean bars DB ingestion proof pass (`provider=massive`, `raw_input_rows=762`, `clean_input_rows=762`, `raw_table_total=762`, `clean_table_total=762`) on ECS: `backups/runtime/l0-db-native-bars-lane-20260303T122100Z/l0-bars-dbproof-ecs-pass-taskdef166-v2.json`
40. Active rollout remains completed on task definition `tfe-web-task:166`: `backups/runtime/l0-db-native-bars-lane-20260303T122100Z/ecs-rollout-verify.json`
41. Fresh bounded anti-loop protocol re-pass after L0 raw/clean bars lane: `backups/runtime/failure-protocol-20260303T122758Z/summary.json`
42. Consolidated L0 raw/clean bars lane summary: `backups/runtime/l0-db-native-bars-lane-20260303T122100Z/summary.json` (`status=pass`)
43. Strict ECS postgres preflight pass on active task definition before L1 SEV-series proof: `backups/runtime/l1-db-native-sev-lane-20260303T123100Z/preflight-ecs-pass-taskdef166.json`
44. Bounded ECS SEV dependency probe pass (`compute_sev_series` runnable in-container): `backups/runtime/l1-db-native-sev-lane-20260303T123100Z/l1-sev-probe-ecs.json`
45. Bounded L1 SEV DB ingestion proof pass (`symbols=AAPL/MSFT/SPY`, `sev_input_rows=762`, `sev_table_total=762`) on ECS: `backups/runtime/l1-db-native-sev-lane-20260303T123100Z/l1-sev-dbproof-ecs-pass-taskdef166-v2.json`
46. Active rollout remains completed on task definition `tfe-web-task:166`: `backups/runtime/l1-db-native-sev-lane-20260303T123100Z/ecs-rollout-verify.json`
47. Fresh bounded anti-loop protocol re-pass after L1 SEV lane: `backups/runtime/failure-protocol-20260303T123906Z/summary.json`
48. Consolidated L1 SEV-series lane summary: `backups/runtime/l1-db-native-sev-lane-20260303T123100Z/summary.json` (`status=pass`)
49. Strict ECS postgres preflight pass on active task definition before L2 gate-segmentation proof: `backups/runtime/l2-db-native-gates-lane-20260303T124646Z/preflight-ecs-pass.json`
50. Bounded ECS L2 dependency probe pass (`segment_gates` + `interpret_gates` runnable in-container): `backups/runtime/l2-db-native-gates-lane-20260303T124646Z/l2-gates-probe-ecs.json`
51. Bounded L2 gate-segmentation DB ingestion proof pass (`symbols=AAPL/MSFT/SPY`, `l2_gate_table_total=8`, `l2_interpretation_table_total=8`, `fk_missing_count=0`, `label_invalid_count=0`) on ECS: `backups/runtime/l2-db-native-gates-lane-20260303T124646Z/l2-gates-dbproof-ecs-pass-taskdef166-v3.json`
52. Active rollout remains completed on task definition `tfe-web-task:166`: `backups/runtime/l2-db-native-gates-lane-20260303T124646Z/ecs-rollout-verify.json`
53. Fresh bounded anti-loop protocol re-pass after L2 gate-segmentation lane: `backups/runtime/failure-protocol-20260303T125452Z/summary.json`
54. Consolidated L2 gate-segmentation lane summary: `backups/runtime/l2-db-native-gates-lane-20260303T124646Z/summary.json` (`status=pass`)
55. Strict ECS postgres preflight pass on active task definition before L3 resonance/regime proof: `backups/runtime/l3-db-native-lane-20260303T130018Z/preflight-ecs-pass.json`
56. Bounded ECS L3 dependency probe pass (`compute_resonance` runnable in-container): `backups/runtime/l3-db-native-lane-20260303T130018Z/l3-resonance-probe-ecs.json`
57. Bounded L3 resonance/regime DB ingestion proof pass (`symbols=AAPL/MSFT/SPY`, `l3_resonance_table_total=8`, `l3_regime_table_total=3`, `resonance_fk_missing_count=0`, `regime_enum_invalid_count=0`) on ECS: `backups/runtime/l3-db-native-lane-20260303T130018Z/l3-dbproof-ecs-pass-taskdef166-v1.json`
58. Active rollout remains completed on task definition `tfe-web-task:166`: `backups/runtime/l3-db-native-lane-20260303T130018Z/ecs-rollout-verify.json`
59. Fresh bounded anti-loop protocol re-pass after L3 resonance/regime lane: `backups/runtime/failure-protocol-20260303T130613Z/summary.json`
60. Consolidated L3 resonance/regime lane summary: `backups/runtime/l3-db-native-lane-20260303T130018Z/summary.json` (`status=pass`)
61. Strict ECS postgres preflight pass before L4 decision/DSF lane: `backups/runtime/l4-db-native-lane-20260303T131042Z/preflight-ecs-pass.json`
62. Bounded ECS L4 dependency probe pass (`compute_directional_signal` + `compute_dsf` runnable in-container): `backups/runtime/l4-db-native-lane-20260303T131042Z/l4-decision-probe-ecs.json`
63. Bounded L4 decision/DSF DB ingestion proof pass (`l4_decision_table_total=3`, `l4_dsf_table_total=3`, `missing_required_fields_count=0`) on ECS: `backups/runtime/l4-db-native-lane-20260303T131042Z/l4-dbproof-ecs-pass-taskdef166-v1.json`
64. Fresh bounded anti-loop protocol re-pass after L4 decision/DSF lane: `backups/runtime/failure-protocol-20260303T131614Z/summary.json`
65. Consolidated L4 decision/DSF lane summary: `backups/runtime/l4-db-native-lane-20260303T131042Z/summary.json` (`status=pass`)
66. Deploy gate pass with L4 phase-2 packaging/sanitation/dedupe patches (`taskdef=tfe-web-task:169`): `backups/deploy-evidence-20260303T141227Z/deploy-report.tsv`
67. Strict ECS postgres preflight pass before L4 structural/snapshot lane proof on taskdef169: `backups/runtime/l4-db-native-phase2-lane-20260303T132335Z/preflight-ecs-pass-taskdef169.json`
68. Bounded ECS structural/snapshot source probe pass on taskdef169: `backups/runtime/l4-db-native-phase2-lane-20260303T132335Z/l4-phase2-probe-ecs-pass-taskdef169-v3.json`
69. Bounded L4 structural/snapshot DB ingestion proof pass on taskdef169 (`l4_structural_episodes_total=1820`, `l4_structural_cache_total=12074`, `l4_snapshot_runs_total=2`, `l4_snapshot_rows_total=21640`, `l4_snapshot_rebuild_reports_total=1`, `snapshot_rows_duplicates_dropped=2`): `backups/runtime/l4-db-native-phase2-lane-20260303T132335Z/l4-phase2-dbproof-ecs-pass-taskdef169-v3.json`
70. Active rollout remains completed on task definition `tfe-web-task:169`: `backups/runtime/l4-db-native-phase2-lane-20260303T132335Z/ecs-rollout-verify-taskdef169.json`
71. Fresh bounded anti-loop protocol re-pass after L4 structural/snapshot lane: `backups/runtime/failure-protocol-20260303T143709Z/summary.json`
72. Consolidated L4 structural/snapshot lane summary: `backups/runtime/l4-db-native-phase2-lane-20260303T132335Z/summary.json` (`status=pass`)

## 14) Recommended Next Single Step
Run the first runtime/UI confidence gate from section 10 (recommended: Recommendations page confidence lane) and capture the required visual evidence set (screenshot + API payload snippet + explicit pass/fail), then proceed page-by-page.

Current implementation status update:
- L5 Phase-2 artifact sync tool exists: `tools/l5_phase2_sync_postgres.py`.
- L5 validation dataset resolver now supports Postgres-first behavior in `l5_policy_learning_pipeline.py`.
- L5 horizon decision overrides resolver now supports Postgres-first behavior in `l5_policy_learning_pipeline.py`.
- L5 rowtrace resolver is now contract-closed in Postgres-first mode with strict ECS preflight and forced-bad-file-path DB-only proof evidence.
- L5 validation + SPY benchmark dataset resolution is now contract-closed in Postgres-first mode with strict ECS preflight and forced-bad-file-path DB-only proof evidence.
- L5 Phase-1 runtime/eval DB-authority proof is now contract-closed with strict ECS preflight + forced-bad-file-path runtime resolve + runtime/eval write/readback evidence.
- L5 anomaly policy resolver lane is contract-closed (deterministic repair + strict preflight + DB-only proof evidence).
- Runtime validation gate now persists DB history rows in `runtime_validation_reports` from `web/scripts/run_validation_gate_v1.mjs`.
- L0 seed/universe ingestion lane (`sp500.csv` + `massive_universe_*.json` -> `l0_universe_seed_symbols` + `l0_universe_symbols`) is contract-closed with strict ECS preflight, bounded DB-proof pass, and fresh anti-loop protocol evidence (`backups/runtime/l0-db-native-universe-lane-20260303T115850Z/summary.json`).
- L0 raw/clean bars lane (`get_unified_market_data().get_history(...)` payload path -> `l0_market_bars_daily_raw` + `l0_market_bars_daily_clean`) is contract-closed with strict ECS preflight, bounded DB-proof pass, and fresh anti-loop protocol evidence (`backups/runtime/l0-db-native-bars-lane-20260303T122100Z/summary.json`).
- L0 bars sync production script now exists in repo: `tools/l0_phase2_bars_sync_postgres.py`.
- L1 SEV-series lane (`uf_core.layer0.compute_sev_series` -> `l1_sev_series`) is contract-closed with strict ECS preflight, bounded DB-proof pass, and fresh anti-loop protocol evidence (`backups/runtime/l1-db-native-sev-lane-20260303T123100Z/summary.json`).
- L1 SEV sync production script now exists in repo: `tools/l1_phase1_sync_postgres.py`.
- L2 gate-segmentation lane (`uf_core.layer1.segment_gates` + `uf_core.layer2.interpret_gates` -> `l2_gate_segments` + `l2_gate_interpretations`) is contract-closed with strict ECS preflight, bounded DB-proof pass, and fresh anti-loop protocol evidence (`backups/runtime/l2-db-native-gates-lane-20260303T124646Z/summary.json`).
- L2 gate sync production script now exists in repo: `tools/l2_phase1_sync_postgres.py`.
- L3 resonance/regime lane (`uf_core.layer3.compute_resonance` + regime aggregation -> `l3_resonance_results` + `l3_regime_states`) is contract-closed with strict ECS preflight, bounded DB-proof pass, and fresh anti-loop protocol evidence (`backups/runtime/l3-db-native-lane-20260303T130018Z/summary.json`).
- L3 sync production script now exists in repo: `tools/l3_phase1_sync_postgres.py`.
- L4 decision/DSF lane (`compute_directional_signal` + `compute_dsf` -> `l4_decision_states` + `l4_dsf_series`) is contract-closed with strict ECS preflight, bounded DB-proof pass, and fresh anti-loop protocol evidence (`backups/runtime/l4-db-native-lane-20260303T131042Z/summary.json`).
- L4 structural/snapshot lane (`structural_episodes.csv`, `uf_structural_cache.json`, `uf_snapshot*.ses/json`, `uf_snapshot_rebuild_report.json` -> `l4_structural_episodes`, `l4_structural_cache`, `l4_snapshot_runs`, `l4_snapshot_rows`, `l4_snapshot_rebuild_reports`) is contract-closed with strict ECS preflight/probe, bounded DB-proof pass, and fresh anti-loop protocol evidence (`backups/runtime/l4-db-native-phase2-lane-20260303T132335Z/summary.json`).
- L4 phase-2 sync production script now exists in repo: `tools/l4_phase2_structural_snapshot_sync_postgres.py`.

## 15) L0-L4 DB-Native Contract Extension (Required Next Architecture Phase)

### 15.1 Exact Current Artifact -> Target Table Mappings

L0 (Universe + Bars ingestion)
1. `sp500.csv` -> `l0_universe_seed_symbols`  
   Columns contract: `seed_id`, `symbol`, `source_path`, `ingested_at_utc`, `active`.
   Status: Implemented (bounded ECS DB-proof pass on taskdef 166 with non-empty table counts).
2. `massive_universe_stocks.json`, `massive_universe_etf.json`, `massive_universe_index.json`, `massive_universe_crypto.json`  
   (generated/used by `massive_universe_cache.py`, `massive_universe_cache_etf.py`, `massive_universe_index.py`, `massive_universe_crypto.py`)  
   -> `l0_universe_symbols`  
   Columns contract: `symbol`, `asset_type`, `source_path`, `source_hash`, `ingested_at_utc`, `meta_json`.
   Status: Implemented (bounded ECS DB-proof pass confirms non-empty rows for `stocks/etf/index/crypto`).
3. In-memory raw provider history payloads from `get_unified_market_data().get_history(...)`  
   (call sites: `uf_mdg_snapshot.py:_fetch_history`, `uf_structural_episodes_log.py:_fetch_history`)  
   -> `l0_market_bars_daily_raw`  
   Columns contract: `symbol`, `bar_ts`, `open`, `high`, `low`, `close`, `volume`, `provider`, `request_window_start`, `request_window_end`, `ingested_at_utc`.
   Status: Implemented (bounded ECS DB-proof pass confirms non-empty raw bars persisted for sample symbols).
4. In-memory cleaned bars produced by `sanitize_daily_bars(...)` in `uf_mdg_snapshot.py`  
   -> `l0_market_bars_daily_clean`  
   Columns contract: `symbol`, `bar_ts`, `open`, `high`, `low`, `close`, `volume`, `clean_rule_version`, `dropped_reason_json`, `ingested_at_utc`.
   Status: Implemented (bounded ECS DB-proof pass confirms non-empty cleaned bars persisted for sample symbols).

L1 (SEV series)
5. In-memory `SEV` sequence from `uf_core.layer0.compute_sev_series`  
   (invoked in `uf_structural_episodes_log.py:compute_raw_uf_state`)  
   -> `l1_sev_series`  
   Columns contract: `symbol`, `bar_ts`, `sev_u`, `sev_d`, `sev_l`, `sev_meta_json`, `computed_at_utc`.
   Status: Implemented (bounded ECS DB-proof pass confirms non-empty `l1_sev_series` rows for sample symbols). Mapping used: `sev_u<-F_norm`, `sev_d<-dF`, `sev_l<-sigma` (full SEV extras retained in `sev_meta_json`).

L2 (Gate segmentation + interpretation)
6. In-memory gate segments from `uf_core.layer1.segment_gates`  
   -> `l2_gate_segments`  
   Columns contract: `symbol`, `gate_id`, `start_ts`, `end_ts`, `gate_type`, `gate_strength`, `gate_json`, `computed_at_utc`.
   Status: Implemented (bounded ECS DB-proof pass confirms non-empty `l2_gate_segments` rows with per-symbol gate presence and zero FK-label contract violations).
7. In-memory gate interpretations from `uf_core.layer2.interpret_gates`  
   -> `l2_gate_interpretations`  
   Columns contract: `symbol`, `gate_id`, `interpretation_id`, `interpretation_label`, `score`, `interpretation_json`, `computed_at_utc`.
   Status: Implemented (bounded ECS DB-proof pass confirms non-empty `l2_gate_interpretations` rows, `l2_interpretation_fk_integrity` pass, and enum label contract pass).

L3 (Resonance + regime)
8. In-memory resonance outputs from `uf_core.layer3.compute_resonance`  
   -> `l3_resonance_results`  
   Columns contract: `symbol`, `gate_id`, `resonance_id`, `resonance_score`, `resonance_json`, `computed_at_utc`.
   Status: Implemented (bounded ECS DB-proof pass confirms non-empty `l3_resonance_results` rows with zero FK violations against `l2_gate_segments`).
9. In-memory aggregated regime state from UF structural engine aggregation  
   (`_aggregate_gate_regime` path used by `uf_structural_episodes_log.py` / `uf_mdg_snapshot.py`)  
   -> `l3_regime_states`  
   Columns contract: `symbol`, `bar_ts`, `regime`, `stability_score`, `max_drawdown`, `regime_json`, `computed_at_utc`.
   Status: Implemented (bounded ECS DB-proof pass confirms non-empty per-symbol latest regime rows with enum contract pass).

L4 (Directional decision + structural episodes + snapshot)
10. In-memory decision states from `uf_core.layer4.compute_directional_signal` and DSF from `uf_core.layer4.compute_dsf`  
    -> `l4_decision_states`, `l4_dsf_series`  
    Columns contract:  
    `l4_decision_states`: `symbol`, `bar_ts`, `d_k`, `m_k`, `r_rev_k`, `u_star_k`, `c_k`, `p_k`, `b_k`, `decision_vector_json`, `computed_at_utc`.  
    `l4_dsf_series`: `symbol`, `bar_ts`, `s_uf`, `r_uf`, `dsf_json`, `computed_at_utc`.
    Status: Implemented (bounded ECS DB-proof pass confirms non-empty `l4_decision_states` + `l4_dsf_series` rows and `missing_required_fields_count=0`).
11. `structural_episodes.csv` (from `uf_structural_episodes_log.py`)  
    -> `l4_structural_episodes`  
    Columns contract: `symbol`, `side`, `entry_time`, `exit_time`, `entry_price`, `exit_price`, `forward_return`, `holding_bars`, `entry_regime`, `exit_regime`, `entry_s_uf`, `exit_s_uf`, `entry_d`, `exit_d`.
    Status: Implemented (bounded ECS DB-proof pass confirms non-empty `l4_structural_episodes` rows and zero invalid parsed rows).
12. `uf_structural_cache.json` -> `l4_structural_cache`.
    Status: Implemented (bounded ECS DB-proof pass confirms non-empty `l4_structural_cache` rows and zero invalid parsed rows).
13. `uf_snapshot.ses.json`, `uf_snapshot_old_backup.ses.json` -> `l4_snapshot_runs`, `l4_snapshot_rows`.
    Status: Implemented (bounded ECS DB-proof pass confirms non-empty run+row tables and deterministic duplicate collapse via `snapshot_rows_duplicates_dropped=2`).
14. `uf_snapshot_rebuild_report.json` -> `l4_snapshot_rebuild_reports`.
    Status: Implemented (bounded ECS DB-proof pass confirms non-empty rebuild report rows).

### 15.2 Per-Layer Validation Gates (Blocking)

L0 gates
1. `l0_seed_non_empty`: seed symbol count > 0.
2. `l0_universe_non_empty_by_asset_type`: stock/etf/index/crypto each has >= 1 row.
3. `l0_raw_bar_integrity`: OHLC finite and `low <= min(open,close) <= high`, `volume >= 0`.
4. `l0_clean_bar_retention`: clean bars are non-empty for each symbol selected for downstream evaluation.

L1 gates
1. `l1_sev_row_presence`: SEV rows exist for every symbol/bar required by L2.
2. `l1_sev_finite`: SEV numeric fields are finite and non-null where required.
3. `l1_symbol_bar_fk_integrity`: all L1 rows map to L0 clean bars.

L2 gates
1. `l2_gate_presence`: at least one gate/segment exists per evaluated symbol window.
2. `l2_interpretation_fk_integrity`: every interpretation row maps to an existing gate.
3. `l2_label_contract`: interpretation labels match approved enum set.

L3 gates
1. `l3_resonance_fk_integrity`: resonance rows map to L2 gate ids.
2. `l3_regime_enum_contract`: regime values restricted to approved enum set.
3. `l3_state_non_empty`: one latest regime row per active symbol.

L4 gates
1. `l4_decision_vector_contract`: `D_k,M_k,R_rev_k,U_star_k,C_k,P_k,B_k` present per active symbol.
2. `l4_snapshot_row_contract`: snapshot rows include required keys used by runtime consumers.
3. `l4_episode_contract`: structural episode row counts and numeric fields parse correctly.

### 15.3 Safe-Restart Rules for L0-L4

1. Persist checkpoint after each layer in sequence:
   `l0_complete` -> `l1_complete` -> `l2_complete` -> `l3_complete` -> `l4_complete`.
2. Resume from latest completed checkpoint; never restart from L0 unless requested.
3. On resume, verify prior-layer gate still passes before starting next layer.
4. Store checkpoint state with: code hash, task definition, start/end timestamps, terminal reason.
5. Abort restart loop when attempts exceed configured bound and emit explicit blocker reason.

### 15.4 Deterministic Fail-Stop Rules for L0-L4

Stop immediately on unchanged code if any repeats:
1. `missing_seed_file:sp500.csv`
2. `universe_source_missing:<artifact_path>`
3. `bars_fetch_empty_all_symbols`
4. `raw_bar_integrity_failed`
5. `l1_sev_compute_failed`
6. `l2_gate_segmentation_failed`
7. `l3_resonance_compute_failed`
8. `l4_decision_vector_missing_required_fields`
9. `snapshot_row_contract_failed`
10. `checkpoint_write_failed`

Mandatory action on deterministic repeat:
1. No rerun of full chain.
2. Patch failing layer code/contract first.
3. Re-run only bounded layer-level diagnostic protocol until gate passes.

## 16) Completion Status (2026-03-03 UTC)
Contract execution is now complete for the DB-native migration scope and the section-10 page-confidence probe set.

Completion evidence:
1. L4 phase-2 structural/snapshot lane summary pass: `backups/runtime/l4-db-native-phase2-lane-20260303T132335Z/summary.json`
2. Fresh anti-loop protocol pass after L4 phase-2 lane: `backups/runtime/failure-protocol-20260303T143709Z/summary.json`
3. Deploy gate pass with portfolio-route + validation-gate patches on `tfe-web-task:170`: `backups/deploy-evidence-20260303T150908Z/deploy-report.tsv`
4. Authenticated post-deploy page-confidence probe overall pass (`recommendations`, `screener`, `watchlist`, `portfolio`, `admin_refresh_log`, `home`): `backups/runtime/page-confidence-probe-auth-admin-postdeploy-20260303T152347Z/summary.json`
5. Consolidated closeout summary bundle: `backups/runtime/db-native-contract-closeout-20260303T152632Z/summary.json`

Operational notes:
1. One bootstrap-enabled deploy gate bypass was used to break pre-rollout validation circular dependency (`TFE_VALIDATION_GATE_BOOTSTRAP_ALLOW=1`) and ship the oracle-integrity logic patch.
2. Temporary authenticated probe user was created, elevated for admin-route evidence, and then deleted (`page-confidence-auth-user-create/promote/delete` artifacts above).

Post-deploy validation confirmation:
1. ECS runtime validation pass on deployed `tfe-web-task:170` with `oracle_integrity=pass` and no blocking reason: `backups/runtime/postdeploy-validation-ecs-check-20260303T152720Z.json`.
2. Normal (non-bootstrap) deploy gate re-run pass on `tfe-web-task:171` with strict runtime validation path `ecs` and status `pass`: `backups/deploy-evidence-20260303T153435Z/deploy-report.tsv`.
3. ECS validation payload for that normal deploy confirms `oracle_integrity=pass` and `blocking_reason=null`: `backups/deploy-evidence-20260303T153435Z/strict-gate-validation-ecs.stdout.json`.

## 17) Canonical Recommendation Runtime Governance (2026-03-05 UTC)

This section is the system-wide canonical rule set for live recommendations and must be treated as blocking governance.

### 17.1 Canonical Runtime Rules
1. Minimum bars rule is canonical at `240`.
   - Runtime source of truth: `web/src/lib/uf-snapshot.ts` (`ACCUMULATE_MIN_BARS` default).
   - Aligned tooling defaults: `tools/evaluate_recommendation_policy_snapshot.py`, `tools/recommendation_data_remediation_lane.py`.
2. Live recommendation quality gates are canonical at:
   - `minCoverage=0.828`
   - `maxFallback=0.172`
   - Runtime source of truth: `web/src/app/api/recommendations/list/route.ts`.
3. Recommendations API is fail-closed when quality gates fail.
   - Required behavior: return `503` with `degradedReason=recommendation_quality_below_threshold`.
4. Promotion behavior remains canonical:
   - No auto-promotion by default (`TFE_POLICY_AUTO_PROMOTE=0`).
   - Manual promotion only via the promotion gate path.

### 17.2 Required Post-Deploy Acceptance Gate (Blocking)
For any deploy that can affect recommendation outputs:
1. Run one authenticated recommendations consistency probe lane:
   - `tools/run_recommendations_consistency_probe_lane.sh`
2. Required pass criteria:
   - `lane-summary.status=pass`
   - `probe.summary.checks.recommendations_api_success=true`
   - `probe.summary.checks.health_counts_consistency=true`
   - `recommendationHealth.alerts=[]`
3. If probe fails, stop and patch before any additional long run.

### 17.3 Fresh Evidence (Canonical Rule Active and Passing)
1. Deploy with canonical min-bars rule:
   - `backups/deploy-evidence-20260305T040509Z/deploy-report.tsv`
   - task definition `tfe-web-task:191`
2. Authenticated probe pass after deploy:
   - `backups/runtime/recommendations-consistency-probe-20260305T042043Z/lane-summary.json`
   - `backups/runtime/recommendations-consistency-probe-20260305T042043Z/probe/summary.json`
3. Live pass payload confirms gate clearance:
   - `coverageRate=0.8285163776493256`
   - `fallbackRate=0.17148362235067438`
   - API `200`, `degraded=false`

### 17.4 Deterministic Fail-Stop Rule (Recommendations Lane)
If `degradedReason=recommendation_quality_below_threshold` repeats on unchanged code:
1. Do not start another long refresh run.
2. Run bounded diagnostics only (policy/coverage/fallback decomposition).
3. Apply one targeted patch.
4. Re-run one probe to validate.
