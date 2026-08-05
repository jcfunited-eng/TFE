# TFE Repository Inventory Summary

Generated: 2026-05-28

Total files inventoried: **1330**

Excludes: `.git/`, `node_modules/`, `__pycache__/`, `.next/`, `.dev_pydeps/`, `.dev_pydeps2/`, `backups/`

## File Count by Status

| Status | Count |
|--------|-------|
| ACTIVE-PROD | 458 |
| ACTIVE-VALIDATION | 22 |
| DEAD | 15 |
| PRESERVED-ARTIFACT | 22 |
| SUPPORT-TOOL | 498 |
| TEST | 5 |
| UNKNOWN | 310 |
| **TOTAL** | **1330** |

---

## g32_* Files (Failed Feb 2026 ML Deploy)

Remnants of the ChatGPT ML injection period. All should be DEAD or removed.

| Path | Status | Last Modified | Has ML Patterns | Touches Kernel |
|------|--------|---------------|-----------------|----------------|
| `Aurelion_G32___ORCHESTRATOR.pdf` | DEAD | 2026-03-21 | NO | NO |
| `g32_horse_race.py` | DEAD | 2026-02-22 | NO | NO |
| `g32_horse_race_loop_runner.py` | DEAD | 2026-02-22 | NO | NO |
| `g32_insanity_loop_runner.py` | DEAD | 2026-03-21 | NO | NO |
| `g32_mom_irf_loop_runner.py` | DEAD | 2026-03-13 | NO | NO |
| `g32_state.json` | DEAD | untracked | NO | NO |
| `g32_thoroughbred_loop_runner.py` | DEAD | 2026-03-21 | NO | NO |
| `tfe_g32_coordinator.py` | ACTIVE-PROD | 2026-04-27 | NO | NO |

---

## Files with ML Patterns (model.fit, model.predict, .train(), etc.)

| Path | Status | Imports |
|------|--------|---------|
| `KERNEL_PHILOSOPHY.md` | UNKNOWN |  [ML FLAG: keras, lightgbm, prophet, scikit, sklearn, statsmodels, tensorflow, torch, xgboost] |
| `docs/tfe_system_recovery_architecture.tex` | SUPPORT-TOOL |  [ML FLAG: sklearn] |

---

## Files with ML-Related Names

Filenames containing: horse, race, irf, ml, model, train, predict, score

| Path | Status | Last Modified | Purpose |
|------|--------|---------------|---------|
| `.github/workflows/deploy-prod.yml` | SUPPORT-TOOL | 2026-02-22 | YAML config: deploy-prod.yml |
| `SCE_Formal_Security_Model_v1_0.pdf` | UNKNOWN | 2026-03-21 | PDF document: SCE_Formal_Security_Model_v1_0.pdf |
| `TFE_Specification_Merged/app_f_traceability_matrix.tex` | SUPPORT-TOOL | 2026-03-21 | TFE specification: app_f_traceability_matrix.tex |
| `TFE_Specification_Merged/ch09_operating_model.tex` | SUPPORT-TOOL | 2026-03-21 | TFE specification: ch09_operating_model.tex |
| `buildspec.yml` | ACTIVE-PROD | 2026-04-05 | AWS CodeBuild spec for Docker image build and ECR push |
| `cached_irf_feature_test.py` | UNKNOWN | 2026-03-21 | Cached-only deterministic feature test for IRF-aligned uncertainty drift keys. |
| `cached_rowtrace_schema_search.py` | UNKNOWN | 2026-03-21 | Cached-only full-universe schema search from row-trace data vs SPY benchmark. |
| `docs/L6_Topological_Constraint_Layer_Spec.tex` | SUPPORT-TOOL | 2026-04-09 | Documentation: L6_Topological_Constraint_Layer_Spec.tex |
| `docs/ufcp_anomaly_predictions.py` | SUPPORT-TOOL | 2026-04-22 | UFCP Anomaly Prediction Suite |
| `docs/ufcp_london_moment_predictions.py` | SUPPORT-TOOL | 2026-04-22 | UFCP London Moment Predictions for All Superconductors |
| `dsf_ai_service/buildspec.yml` | ACTIVE-PROD | 2026-05-10 | AWS CodeBuild spec for Docker image build and ECR push |
| `dsf_ai_service/static/account.html` | ACTIVE-PROD | 2026-05-10 | DSF-AI static page: account.html |
| `dsf_ai_service/static/admin.html` | ACTIVE-PROD | 2026-05-12 | DSF-AI static page: admin.html |
| `dsf_ai_service/static/battery.html` | ACTIVE-PROD | 2026-05-12 | DSF-AI static page: battery.html |
| `dsf_ai_service/static/case-battery.html` | ACTIVE-PROD | 2026-05-12 | DSF-AI static page: case-battery.html |
| `dsf_ai_service/static/case-fese.html` | ACTIVE-PROD | 2026-05-12 | DSF-AI static page: case-fese.html |
| `dsf_ai_service/static/case-mgb2.html` | ACTIVE-PROD | 2026-05-12 | DSF-AI static page: case-mgb2.html |
| `dsf_ai_service/static/case-pharma-dsc.html` | ACTIVE-PROD | 2026-05-12 | DSF-AI static page: case-pharma-dsc.html |
| `dsf_ai_service/static/case-vo2.html` | ACTIVE-PROD | 2026-05-12 | DSF-AI static page: case-vo2.html |
| `dsf_ai_service/static/discovery.html` | ACTIVE-PROD | 2026-05-26 | DSF-AI static page: discovery.html |
| `dsf_ai_service/static/hw-derive.html` | ACTIVE-PROD | 2026-05-26 | DSF-AI static page: hw-derive.html |
| `dsf_ai_service/static/index.html` | ACTIVE-PROD | 2026-05-26 | DSF-AI static page: index.html |
| `dsf_ai_service/static/legal.html` | ACTIVE-PROD | 2026-05-11 | DSF-AI static page: legal.html |
| `dsf_ai_service/static/pharma.html` | ACTIVE-PROD | 2026-05-12 | DSF-AI static page: pharma.html |
| `dsf_ai_service/static/predictions.html` | ACTIVE-PROD | 2026-05-11 | DSF-AI static page: predictions.html |
| `dsf_ai_service/static/sitemap.xml` | ACTIVE-PROD | 2026-05-12 | DSF-AI static page: sitemap.xml |
| `dsf_ai_service/static/validation-draft.html` | ACTIVE-VALIDATION | 2026-05-26 | DSF-AI static page: validation-draft.html |
| `dsf_ai_service/static/validation.html` | ACTIVE-VALIDATION | 2026-05-26 | DSF-AI static page: validation.html |
| `g32_horse_race.py` | DEAD | 2026-02-22 | G32 horse race ML model comparison (DEAD from ChatGPT ML period) |
| `g32_horse_race_loop_runner.py` | DEAD | 2026-02-22 | G32 horse race loop runner (DEAD from ML period) |
| `g32_mom_irf_loop_runner.py` | DEAD | 2026-03-13 | G32 momentum IRF loop runner (DEAD from ML period) |
| `horse_race_status.py` | DEAD | 2026-02-22 | Horse race status tracker (DEAD from ML period) |
| `real_world_cleaned_universe_l5_primitive_only_row_trace.csv` | UNKNOWN | untracked | CSV data: real_world_cleaned_universe_l5_primitive_only_row_trace.csv |
| `real_world_cleaned_universe_l5_primitive_only_row_trace_export.py` | UNKNOWN | 2026-03-21 | Single-lane primitive row-trace export for DSF Primitive Interpretation Recovery. |
| `real_world_cleaned_universe_l5_primitive_only_row_trace_metadata.json` | UNKNOWN | untracked | JSON data/config: real_world_cleaned_universe_l5_primitive_only_row_trace_metadata.json |
| `real_world_cleaned_universe_l5_row_trace_export.py` | UNKNOWN | 2026-03-21 | Sliding as-of-time cleaned-universe native UF row-trace generation. |
| `real_world_cleaned_universe_l5_row_trace_full.csv` | UNKNOWN | 2026-03-13 | CSV data: real_world_cleaned_universe_l5_row_trace_full.csv |
| `tfe_investability_score.py` | UNKNOWN | 2026-04-27 | Investability score calculator for universe filtering |
| `tools/build_merged_historical_row_trace.py` | SUPPORT-TOOL | 2026-03-21 | Tool: build_merged_historical_row_trace.py |
| `tools/build_rowtrace_backfill_plan.py` | SUPPORT-TOOL | 2026-03-21 | Tool: build_rowtrace_backfill_plan.py |
| `tools/convert_snapshot_archive_to_rowtrace.py` | SUPPORT-TOOL | 2026-03-21 | Tool: convert_snapshot_archive_to_rowtrace.py |
| `tools/freeze_production_primitive_rowtrace_fixed_snapshot.py` | SUPPORT-TOOL | 2026-03-21 | Tool: freeze_production_primitive_rowtrace_fixed_snapshot.py |
| `tools/freeze_production_primitive_rowtrace_parallel.py` | SUPPORT-TOOL | 2026-03-21 | Tool: freeze_production_primitive_rowtrace_parallel.py |
| `tools/merge_backfilled_rowtrace.py` | SUPPORT-TOOL | 2026-03-21 | Tool: merge_backfilled_rowtrace.py |
| `tools/regenerate_fresh_temporal_rowtrace_from_raw.py` | SUPPORT-TOOL | 2026-03-21 | Tool: regenerate_fresh_temporal_rowtrace_from_raw.py |
| `tools/regenerate_historical_rowtrace_from_raw.py` | SUPPORT-TOOL | 2026-03-21 | Tool: regenerate_historical_rowtrace_from_raw.py |
| `tools/run_uf_dynamic_decision_native_rowtrace_eval.py` | SUPPORT-TOOL | 2026-03-21 | Tool: run_uf_dynamic_decision_native_rowtrace_eval.py |
| `tools/ufcp_full_predictions.py` | SUPPORT-TOOL | 2026-05-13 | Dump ALL 240 UFCP predictions as a table. |
| `tools/ufcp_predictions_complete.csv` | SUPPORT-TOOL | 2026-05-10 | Tool: ufcp_predictions_complete.csv |
| `uf_core/validation/noise_model.py` | ACTIVE-PROD | 2026-02-22 | UF-Spec v1.4.0 — Section 13 Validation Utilities |
| `uf_policy_what_if_from_row_trace.json` | UNKNOWN | untracked | JSON data/config: uf_policy_what_if_from_row_trace.json |

---

## Files with ML Library Imports

| Path | Status | ML Libraries |
|------|--------|-------------|
| `KERNEL_PHILOSOPHY.md` | UNKNOWN |  [ML FLAG: keras, lightgbm, prophet, scikit, sklearn, statsmodels, tensorflow, torch, xgboost] |
| `docs/DSF_AI_MACE_Audit_Report.md` | SUPPORT-TOOL |  [ML FLAG: torch] |
| `docs/tfe_system_recovery_architecture.tex` | SUPPORT-TOOL |  [ML FLAG: sklearn] |

---

## Files Modified Jan-Mar 2026 (ChatGPT ML Period) -- 601 files

| Path | Status | Last Modified | Has ML | Touches Kernel |
|------|--------|---------------|--------|----------------|
| `.github/workflows/deploy-prod.yml` | SUPPORT-TOOL | 2026-02-22 | NO | NO |
| `alpaca_market_data_service.py` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `aws_root_key_provider.py` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `certs/rds-global-bundle.pem` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `coc_events_dev.log` | UNKNOWN | 2026-02-22 | NO | NO |
| `data/AAPL.csv` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `data/BTC-USD.csv` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `data/ETH-USD.csv` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `data/TEST.csv` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `data/VTI.csv` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `data/cache/price_snapshot.json` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `data/cache/uf_junk.json` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `energy_entropy_output.txt` | UNKNOWN | 2026-02-22 | NO | NO |
| `g32_horse_race.py` | DEAD | 2026-02-22 | NO | NO |
| `g32_horse_race_loop_runner.py` | DEAD | 2026-02-22 | NO | NO |
| `horse_race_status.py` | DEAD | 2026-02-22 | NO | NO |
| `market_data/BTC.csv` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `market_data/QQQ.csv` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `market_data/SPY.csv` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `massive_universe_cache_etf.py` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `massive_universe_crypto.py` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `massive_universe_index.py` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `ses_core/__init__.py` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `ses_core/aead_backend.py` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `ses_core/aws_root_key_provider.py` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `ses_core/chain_of_custody.py` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `ses_core/domain_params.py` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `ses_core/key_derivation.py` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `ses_core/tenant_id.py` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `tfe_bar_integrity.py` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `tfe_encrypted_portfolios/tenant-tao__default.json` | SUPPORT-TOOL | 2026-02-22 | NO | NO |
| `tfe_market_data.py` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `tfe_market_data_factory.py` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `tfe_market_data_service.py` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `tfe_portfolio_index.json` | UNKNOWN | 2026-02-22 | NO | NO |
| `tfe_root_key.bin` | UNKNOWN | 2026-02-22 | NO | NO |
| `tfe_ses_core_adapter.py` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `tools/ensure_deploy_runtime.sh` | SUPPORT-TOOL | 2026-02-22 | NO | NO |
| `tools/post_rebuild_deploy_gate.sh` | SUPPORT-TOOL | 2026-02-22 | NO | NO |
| `tools/pre_rebuild_chat_backup.sh` | SUPPORT-TOOL | 2026-02-22 | NO | NO |
| `tools/verify_build_only_with_evidence.sh` | SUPPORT-TOOL | 2026-02-22 | NO | NO |
| `uf_core/Archieve/ARC1_config.py` | ACTIVE-PROD | 2026-02-22 | NO | YES |
| `uf_core/Archieve/ARC1_layer2.py` | ACTIVE-PROD | 2026-02-22 | NO | YES |
| `uf_core/Archieve/ARC1_layer3.py` | ACTIVE-PROD | 2026-02-22 | NO | YES |
| `uf_core/Archieve/ARC_1_layer4.py` | ACTIVE-PROD | 2026-02-22 | NO | YES |
| `uf_core/_init_.py` | ACTIVE-PROD | 2026-02-22 | NO | YES |
| `uf_core/config.py` | ACTIVE-PROD | 2026-02-22 | NO | YES |
| `uf_core/hardening.py` | ACTIVE-PROD | 2026-02-22 | NO | YES |
| `uf_core/hardening_actions.py` | ACTIVE-PROD | 2026-02-22 | NO | YES |
| `uf_core/hardening_controller.py` | ACTIVE-PROD | 2026-02-22 | NO | YES |
| `uf_core/layer0.py` | ACTIVE-PROD | 2026-02-22 | NO | YES |
| `uf_core/layer1.py` | ACTIVE-PROD | 2026-02-22 | NO | YES |
| `uf_core/layer2.py` | ACTIVE-PROD | 2026-02-22 | NO | YES |
| `uf_core/layer3.py` | ACTIVE-PROD | 2026-02-22 | NO | YES |
| `uf_core/layer4.py` | ACTIVE-PROD | 2026-02-22 | NO | YES |
| `uf_core/safemode.py` | ACTIVE-PROD | 2026-02-22 | NO | YES |
| `uf_core/validation/__init__.py` | ACTIVE-PROD | 2026-02-22 | NO | YES |
| `uf_core/validation/layer0 - Copy.py` | ACTIVE-PROD | 2026-02-22 | NO | YES |
| `uf_core/validation/noise_model.py` | ACTIVE-PROD | 2026-02-22 | NO | YES |
| `uf_core/validation/qa_dataset.py` | ACTIVE-PROD | 2026-02-22 | NO | YES |
| `uf_core/validation/val_baseline.py` | ACTIVE-PROD | 2026-02-22 | NO | YES |
| `uf_core/validation/val_composite_metrics.py` | ACTIVE-PROD | 2026-02-22 | NO | YES |
| `uf_core/validation/val_direction_stability.py` | ACTIVE-PROD | 2026-02-22 | NO | YES |
| `uf_core/validation/val_dsf_stability.py` | ACTIVE-PROD | 2026-02-22 | NO | YES |
| `uf_core/validation/val_gate_stability.py` | ACTIVE-PROD | 2026-02-22 | NO | YES |
| `uf_core/validation/val_metrics.py` | ACTIVE-PROD | 2026-02-22 | NO | YES |
| `uf_core/validation/val_noise.py` | ACTIVE-PROD | 2026-02-22 | NO | YES |
| `uf_core/validation/val_sensitivity_curve.py` | ACTIVE-PROD | 2026-02-22 | NO | YES |
| `uf_core/validation/val_sensitivity_sweep.py` | ACTIVE-PROD | 2026-02-22 | NO | YES |
| `uf_core/validation/val_stability_report.py` | ACTIVE-PROD | 2026-02-22 | NO | YES |
| `uf_snapshot.json` | UNKNOWN | 2026-02-22 | NO | NO |
| `uf_snapshot_old_backup.json` | UNKNOWN | 2026-02-22 | NO | NO |
| `uf_structural_cache.json` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `validation_sample.csv` | ACTIVE-VALIDATION | 2026-02-22 | NO | NO |
| `watchlist.csv` | UNKNOWN | 2026-02-22 | NO | NO |
| `web/next.config.ts` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/postcss.config.mjs` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/public/file.svg` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/public/globe.svg` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/public/landing-zen.jpg` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/public/next.svg` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/public/uploads/1771019530856-account-accountpage.png` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/public/uploads/1771019560017-recommendations-accountpage.png` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/public/uploads/1771019598184-recommendations-recommendationspage.png` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/public/uploads/1771021004354-watchlist-watchlistpage.png` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/public/uploads/1771022274445-portfolioAdvisor-portfolioadvisdorpage.jpg` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/public/uploads/1771029307452-legal-legalpage.jpg` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/public/uploads/1771146411980-help-helppage.jpg` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/public/uploads/1771147499302-support-supportpage.jpg` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/public/uploads/1771174792200-adminConsole-adminpage.jpg` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/public/uploads/Act1MarketScanFilter.png` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/public/uploads/Act1iconGlass.png` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/public/uploads/Act2Compare.png` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/public/uploads/Act2iconGlass.png` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/public/uploads/Act3Recommendations.png` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/public/uploads/Act3Watchlist.png` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/public/uploads/Act3iconGlass.png` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/public/uploads/Act4Portfolio.png` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/public/uploads/Act4iconGlass.png` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/public/uploads/AdminPage.jpeg` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/public/uploads/BarIntegrityflyin.png` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/public/uploads/Chapter4AIinAction.mp4` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/public/uploads/HomeClearGlass.png` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/public/uploads/HomePageGlassIcon-rgba-v2.png` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/public/uploads/HomePageGlassIcon-rgba-v3.png` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/public/uploads/HomePageGlassIcon-rgba-v4-onblue.png` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/public/uploads/HomePageGlassIcon-rgba-v4.png` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/public/uploads/HomePageGlassIcon.png` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/public/uploads/LoginClearGlass.png` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/public/uploads/LogionGlassIcon-rgba-v2.png` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/public/uploads/LogionGlassIcon-rgba-v3.png` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/public/uploads/LogionGlassIcon-rgba-v4-onblue.png` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/public/uploads/LogionGlassIcon-rgba-v4.png` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/public/uploads/LogionGlassIcon.png` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/public/uploads/Plainlanguageflyin.png` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/public/uploads/ProprietAIflyin.png` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/public/uploads/ResetClearGlass.png` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/public/uploads/TickerInputsflyin.png` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/public/uploads/Whatifflyin.png` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/public/uploads/home-story-1-pingpong.mp4` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/public/uploads/home-story-2-library.png` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/public/vercel.svg` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/public/window.svg` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/src/app/admin-console/page.tsx` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/src/app/api/auth/sign-out/route.ts` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/src/app/favicon.ico` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/src/app/help/page.tsx` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/src/app/legal/page.tsx` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/src/app/page.tsx` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/src/app/portfolio-advisor/page.module.css` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/src/app/support/page.tsx` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/src/app/theme-preview/page.tsx` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/src/app/watchlist/page.tsx` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/src/lib/external-url.ts` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `web/tsconfig.json` | ACTIVE-PROD | 2026-02-22 | NO | NO |
| `PRODUCTION_EVALUATION_CONTRACT.md` | UNKNOWN | 2026-03-13 | NO | NO |
| `PROJECT_REALIGNMENT_PROTOCOL.md` | UNKNOWN | 2026-03-13 | NO | NO |
| `g32_mom_irf_loop_runner.py` | DEAD | 2026-03-13 | NO | NO |
| `l5_postgres_io.py` | UNKNOWN | 2026-03-13 | NO | NO |
| `real_world_cleaned_universe_l5_row_trace_full.csv` | UNKNOWN | 2026-03-13 | NO | NO |
| `structural_episodes.csv` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `structural_recency_snapshot.py` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `tools/l0_phase1_sync_postgres.py` | ACTIVE-PROD | 2026-03-13 | NO | YES |
| `tools/l0_phase2_bars_sync_postgres.py` | ACTIVE-PROD | 2026-03-13 | NO | YES |
| `tools/l1_phase1_sync_postgres.py` | ACTIVE-PROD | 2026-03-13 | NO | YES |
| `tools/l2_phase1_sync_postgres.py` | ACTIVE-PROD | 2026-03-13 | NO | YES |
| `tools/l3_phase1_sync_postgres.py` | ACTIVE-PROD | 2026-03-13 | NO | YES |
| `tools/l4_phase1_decision_sync_postgres.py` | ACTIVE-PROD | 2026-03-13 | NO | YES |
| `tools/l4_phase2_structural_snapshot_sync_postgres.py` | ACTIVE-PROD | 2026-03-13 | NO | YES |
| `tools/l5_db_native_preflight.py` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `tools/l5_phase2_sync_postgres.py` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `tools/run_recommendation_quality_audit_lane.sh` | SUPPORT-TOOL | 2026-03-13 | NO | NO |
| `tools/run_site_reliability_contract_gate.sh` | SUPPORT-TOOL | 2026-03-13 | NO | NO |
| `web/scripts/backfill_runtime_decision_provenance_fallback_ladder.mjs` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `web/scripts/build_a54s_contract_artifacts.mjs` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `web/scripts/build_a55_activation_readiness_artifacts.mjs` | ACTIVE-PROD | 2026-03-13 | NO | YES |
| `web/scripts/build_admin_rulebook_coverage_artifacts.mjs` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `web/scripts/build_blocked_family_field_contract_artifacts.mjs` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `web/scripts/build_exact_match_recovery_audit.mjs` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `web/scripts/build_exact_path_alignment_artifacts.mjs` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `web/scripts/build_exact_path_alignment_phase3_artifacts.mjs` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `web/scripts/build_long_side_rulebook_decomposition_artifacts.mjs` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `web/scripts/build_long_side_subfamily_contract_artifacts.mjs` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `web/scripts/build_quote_freshness_root_cause_artifacts.mjs` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `web/scripts/build_quote_publication_alignment_fix_artifacts.mjs` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `web/scripts/build_quote_publication_alignment_fix_artifacts.py` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `web/scripts/build_typed_fallback_ladder_artifacts.mjs` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `web/scripts/evaluate_live_uf_row.py` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `web/scripts/generate_schedule_cadence_evidence.mjs` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `web/scripts/get_history_json.py` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `web/scripts/live_screener_tab_filter_check.mjs` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `web/scripts/page_confidence_probe.mjs` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `web/scripts/publication_identity.py` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `web/scripts/run_a3_surgical_sync_and_parity.mjs` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `web/scripts/run_admin_rulebook_coverage_route_check.ts` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `web/scripts/run_exact_path_alignment_admin_route_check.ts` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `web/scripts/run_provenance_persistence_parity_audit.mjs` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `web/scripts/screener_api_timing_diagnostics.mjs` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `web/scripts/ses_web_blob.py` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `web/scripts/stamp_quote_publication_alignment.py` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `web/scripts/watchlist_confidence_probe.mjs` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `web/src/app/admin-console/refresh-log/page.tsx` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `web/src/app/error.tsx` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `web/src/app/portfolio/page.tsx` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `web/src/app/screener/page.tsx` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `web/src/components/ClientPortal.tsx` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `web/src/components/ScreenerChart.tsx` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `web/src/lib/admin-refresh-persist.ts` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `web/src/lib/auth-session.ts` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `web/src/lib/live-price.ts` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `web/src/lib/market-analysis.ts` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `web/src/lib/runtime-build-metadata.ts` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `web/src/lib/screener-filter-schema-v111.ts` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `web/src/lib/screener-filter-v111.ts` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `web/src/lib/screener-profile-overrides.ts` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `web/src/lib/screener-quote-cache.ts` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `web/src/lib/uf-snapshot.ts` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `web/src/lib/use-flyout-panel.ts` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `web/src/lib/user-storage-backend.ts` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `web/src/lib/workspace-root.ts` | ACTIVE-PROD | 2026-03-13 | NO | NO |
| `tools/prove_terminal_phase_truth.ts` | SUPPORT-TOOL | 2026-03-14 | NO | NO |
| `tools/verify_refresh_phase_truth_readonly.py` | SUPPORT-TOOL | 2026-03-14 | NO | NO |
| `web/scripts/pre_ingestion_completeness_check.py` | ACTIVE-PROD | 2026-03-14 | NO | NO |
| `web/src/lib/screenerTableSort.ts` | ACTIVE-PROD | 2026-03-14 | NO | NO |
| `web/scripts/seed_screener_quote_cache_from_runtime.mjs` | ACTIVE-PROD | 2026-03-15 | NO | NO |
| `web/src/lib/refresh-terminal-truth.ts` | ACTIVE-PROD | 2026-03-15 | NO | NO |
| `web/src/lib/step1/followup-ticket.ts` | ACTIVE-PROD | 2026-03-15 | NO | NO |
| `tools/verify_phase_d_deployment_record.py` | SUPPORT-TOOL | 2026-03-16 | NO | NO |
| `tools/verify_phase_e_orchestrator_package_contract.py` | SUPPORT-TOOL | 2026-03-16 | NO | NO |
| `tools/verify_phase_e_package_contract.py` | SUPPORT-TOOL | 2026-03-16 | NO | NO |
| `tools/verify_phase_e_source_package_identity_request.py` | SUPPORT-TOOL | 2026-03-16 | NO | NO |
| `web/data/screener-finviz-overview-cache.json` | ACTIVE-PROD | 2026-03-16 | NO | NO |
| `web/data/screener-profile-overrides.json` | ACTIVE-PROD | 2026-03-16 | NO | NO |
| `web/data/screener-quote-cache.failures.json` | ACTIVE-PROD | 2026-03-16 | NO | NO |
| `web/data/screener-quote-cache.json` | ACTIVE-PROD | 2026-03-16 | NO | NO |
| `web/src/lib/publication-bundle-contract.ts` | ACTIVE-PROD | 2026-03-16 | NO | NO |
| `web/src/lib/release-gate-classes.ts` | ACTIVE-PROD | 2026-03-16 | NO | NO |
| `web/src/lib/step1/assessment-report.ts` | ACTIVE-PROD | 2026-03-16 | NO | NO |
| `web/src/lib/step1/candidate-bundle.ts` | ACTIVE-PROD | 2026-03-16 | NO | NO |
| `web/src/lib/step1/package-contract.ts` | ACTIVE-PROD | 2026-03-16 | NO | NO |
| `web/src/lib/step1/publication-commit.ts` | ACTIVE-PROD | 2026-03-16 | NO | NO |
| `web/src/lib/step1/run-request.ts` | ACTIVE-PROD | 2026-03-16 | NO | NO |
| `web/src/lib/step1/schema.ts` | ACTIVE-PROD | 2026-03-16 | NO | NO |
| `tools/run_validation_gate_v1_in_ecs_network.py` | ACTIVE-VALIDATION | 2026-03-17 | NO | NO |
| `tools/verify_phase_e_admin_refresh_source_package_resolution.py` | SUPPORT-TOOL | 2026-03-17 | NO | NO |
| `web/scripts/read_runtime_selector_rows.mjs` | ACTIVE-PROD | 2026-03-17 | NO | NO |
| `web/scripts/read_runtime_selector_rows_impl.mjs` | ACTIVE-PROD | 2026-03-17 | NO | NO |
| `web/scripts/resolve_runtime_db_secret.py` | ACTIVE-PROD | 2026-03-17 | NO | NO |
| `web/scripts/run_validation_gate_v1.mjs` | ACTIVE-PROD | 2026-03-17 | NO | NO |
| `web/scripts/runtime_db_refresh_env.mjs` | ACTIVE-PROD | 2026-03-17 | NO | NO |
| `web/scripts/sync_runtime_postgres.mjs` | ACTIVE-PROD | 2026-03-17 | NO | NO |
| `web/scripts/update_refresh_phase_ledger.mjs` | ACTIVE-PROD | 2026-03-17 | NO | NO |
| `web/scripts/update_refresh_phase_ledger_impl.mjs` | ACTIVE-PROD | 2026-03-17 | NO | NO |
| `web/src/lib/step1/orchestrator.ts` | ACTIVE-PROD | 2026-03-17 | NO | NO |
| `web/src/lib/step1/source-package-identities.ts` | ACTIVE-PROD | 2026-03-17 | NO | NO |
| `AWS Deployment Notes.docx` | UNKNOWN | 2026-03-21 | NO | NO |
| `AWS_RUNBOOK.md` | UNKNOWN | 2026-03-21 | NO | NO |
| `Appendix A.docx` | UNKNOWN | 2026-03-21 | NO | NO |
| `Appendix B.docx` | UNKNOWN | 2026-03-21 | NO | NO |
| `ArcLoom_LoomCore_RNA3D_Spec_v0_1.pdf` | UNKNOWN | 2026-03-21 | NO | NO |
| `Archieve_2/ARC_rebuild_uf_snapshot.py` | DEAD | 2026-03-21 | NO | NO |
| `Archieve_2/ARC_uf_engine_aws_service.py` | DEAD | 2026-03-21 | NO | YES |
| `Archieve_2/Arc1_data_loader.py` | DEAD | 2026-03-21 | NO | NO |
| `Archieve_2/aws_root_key_provider.py` | DEAD | 2026-03-21 | NO | NO |
| `Archieve_2/uf_structural_engine` | DEAD | 2026-03-21 | NO | YES |
| `Archieve_2/uf_structural_engine.py` | DEAD | 2026-03-21 | NO | YES |
| `Aurelion_G32___ORCHESTRATOR.pdf` | DEAD | 2026-03-21 | NO | NO |
| `Build a Temporal Memory Policy Layer.txt` | UNKNOWN | 2026-03-21 | NO | NO |
| `ChatGTP UF Assistant Instructions.docx` | UNKNOWN | 2026-03-21 | NO | NO |
| `DB_NATIVE_MIGRATION_CONTRACT.md` | UNKNOWN | 2026-03-21 | NO | NO |
| `DSF_PRIMITIVE_INTERPRETATION_RECOVERY_STATUS.md` | UNKNOWN | 2026-03-21 | NO | NO |
| `DSF_PRIMITIVE_LAW_SKETCH.md` | UNKNOWN | 2026-03-21 | NO | NO |
| `FMM_CF.pdf` | UNKNOWN | 2026-03-21 | NO | NO |
| `FRONTEND_MIGRATION_PLAN.md` | UNKNOWN | 2026-03-21 | NO | NO |
| `INGESTION LAYER + DB SCHEMA.docx` | UNKNOWN | 2026-03-21 | NO | NO |
| `INGESTION_LAYER_DB_SCHEMA_extracted.txt` | UNKNOWN | 2026-03-21 | NO | NO |
| `Information_Resonance_Fields_and_Premonition__Like_Inference_in_High__Dimensional_Histories__A_Theoretical_Framework.pdf` | UNKNOWN | 2026-03-21 | NO | NO |
| `L5_CURRENT_SYSTEM_FULL_SPEC.md` | UNKNOWN | 2026-03-21 | NO | YES |
| `L5_CURRENT_SYSTEM_FULL_SPEC.tex` | UNKNOWN | 2026-03-21 | NO | NO |
| `L5_CURRENT_SYSTEM_FULL_SPEC_latex.zip` | UNKNOWN | 2026-03-21 | NO | NO |
| `OVERNIGHT_DELIVERY_SPEC.md` | UNKNOWN | 2026-03-21 | NO | NO |
| `PRIMITIVE_DIRECT_FIELD_STATE_CALC_DRAFT.md` | UNKNOWN | 2026-03-21 | NO | NO |
| `PROJECT_REALIGNMENT_PROTOCOL.docx` | UNKNOWN | 2026-03-21 | NO | NO |
| `RNA3D Fold Stanford Challenge Kaggle Site Website Content.docx` | UNKNOWN | 2026-03-21 | NO | NO |
| `SCE_Formal_Security_Model_v1_0.pdf` | UNKNOWN | 2026-03-21 | NO | NO |
| `SCE_Specification_v1_0.pdf` | UNKNOWN | 2026-03-21 | NO | NO |
| `Section 17-19.docx` | UNKNOWN | 2026-03-21 | NO | NO |
| `Section 20 Glossary.docx` | UNKNOWN | 2026-03-21 | NO | NO |
| `Section 21.docx` | UNKNOWN | 2026-03-21 | NO | NO |
| `Section 22-23.docx` | UNKNOWN | 2026-03-21 | NO | NO |
| `Section13-Main.tex` | UNKNOWN | 2026-03-21 | NO | NO |
| `Spider_Eyes_GD_FMM_Specification.pdf` | UNKNOWN | 2026-03-21 | NO | NO |
| `Spider_Eyes_Multi_Eye_Specification.pdf` | UNKNOWN | 2026-03-21 | NO | NO |
| `TFE_5_3_Implementation Plan v2.6.md` | UNKNOWN | 2026-03-21 | NO | NO |
| `TFE_5_3_Implementation_Plan_v1_1.md` | UNKNOWN | 2026-03-21 | NO | NO |
| `TFE_5_3_Implementation_Plan_v2_0.md` | UNKNOWN | 2026-03-21 | NO | NO |
| `TFE_5_3_Implementation_Plan_v2_2 (1).md` | UNKNOWN | 2026-03-21 | NO | NO |
| `TFE_5_3_Implementation_Plan_v2_2.md` | UNKNOWN | 2026-03-21 | NO | NO |
| `TFE_5_3_Implementation_Plan_v2_3.md` | UNKNOWN | 2026-03-21 | NO | NO |
| `TFE_5_3_Implementation_Plan_v2_4.md` | UNKNOWN | 2026-03-21 | NO | NO |
| `TFE_5_3_Implementation_Plan_v2_5.md` | UNKNOWN | 2026-03-21 | NO | NO |
| `TFE_ADMIN_CONSOLE_SPEC.md` | UNKNOWN | 2026-03-21 | NO | NO |
| `TFE_Global_Market_Engine_Summary.docx` | UNKNOWN | 2026-03-21 | NO | NO |
| `TFE_REARCHITECTURE_MASTER_PLAN_v2_7.md` | UNKNOWN | 2026-03-21 | NO | NO |
| `TFE_SPECIFICATION.md` | UNKNOWN | 2026-03-21 | NO | NO |
| `TFE_SUBSCRIPTION_AND_CART_SPEC.md` | UNKNOWN | 2026-03-21 | NO | NO |
| `TFE_Spec_Internal_Review_v2_0 (1).md` | UNKNOWN | 2026-03-21 | NO | NO |
| `TFE_Spec_Internal_Review_v2_0.md` | UNKNOWN | 2026-03-21 | NO | NO |
| `TFE_Spec_Internal_Review_v2_2 (1).md` | UNKNOWN | 2026-03-21 | NO | NO |
| `TFE_Spec_Internal_Review_v2_2.md` | UNKNOWN | 2026-03-21 | NO | NO |
| `TFE_Spec_Internal_Review_v2_3.md` | UNKNOWN | 2026-03-21 | NO | NO |
| `TFE_Spec_Internal_Review_v2_4.md` | UNKNOWN | 2026-03-21 | NO | NO |
| `TFE_Specification_Merged/app_a_epoch_channel_registry.tex` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `TFE_Specification_Merged/app_b_audit_event_registry.tex` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `TFE_Specification_Merged/app_c_lineage.tex` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `TFE_Specification_Merged/app_d_gap_matrix.tex` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `TFE_Specification_Merged/app_e_revision_history.tex` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `TFE_Specification_Merged/app_f_traceability_matrix.tex` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `TFE_Specification_Merged/app_g_parameter_registry.tex` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `TFE_Specification_Merged/ch01_document_control.tex` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `TFE_Specification_Merged/ch02_references.tex` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `TFE_Specification_Merged/ch03_definitions.tex` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `TFE_Specification_Merged/ch04_mathematics.tex` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `TFE_Specification_Merged/ch05_uf_l0_l4.tex` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `TFE_Specification_Merged/ch06_l5_governance.tex` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `TFE_Specification_Merged/ch07_architecture_overview.tex` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `TFE_Specification_Merged/ch08_architecture_principles.tex` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `TFE_Specification_Merged/ch09_operating_model.tex` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `TFE_Specification_Merged/ch10_source_plane.tex` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `TFE_Specification_Merged/ch11_canonical_objects.tex` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `TFE_Specification_Merged/ch12_assessment_publication_plane.tex` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `TFE_Specification_Merged/ch13_serving_plane.tex` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `TFE_Specification_Merged/ch14_enrichment_plane.tex` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `TFE_Specification_Merged/ch15_refresh_state_machine.tex` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `TFE_Specification_Merged/ch16_product_deployment.tex` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `TFE_Specification_Merged/ch17_resilience.tex` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `TFE_Specification_Merged/ch18_financial_governance.tex` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `TFE_Specification_Merged/ch19_commercial_adaptation.tex` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `TFE_Specification_Merged/ch20_ses_security.tex` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `TFE_Specification_Merged/ch21_persistence_runtime.tex` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `TFE_Specification_Merged/ch22_cp0_code_truth.tex` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `TFE_Specification_Merged/ch23_security_documentation.tex` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `TFE_Specification_Merged/ch24_mathematical_determinism.tex` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `TFE_Specification_Merged/ch25_verification_validation.tex` | ACTIVE-VALIDATION | 2026-03-21 | NO | NO |
| `TFE_Specification_Merged/ch26_commercial_benchmarking.tex` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `TFE_Specification_Merged/ch27_change_control.tex` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `TFE_Specification_Merged/ch28_risks_limitations.tex` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `TFE_Specification_Merged/ch29_competitiveness_ceiling.tex` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `TFE_Specification_Merged/ch30_migration_cutover.tex` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `TFE_Specification_Merged/main.tex` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `TFE_Specification_v1_1 (1).pdf` | UNKNOWN | 2026-03-21 | NO | NO |
| `TFE_Specification_v1_1.pdf` | UNKNOWN | 2026-03-21 | NO | NO |
| `TFE_Specification_v2_0.pdf` | UNKNOWN | 2026-03-21 | NO | NO |
| `TFE_Specification_v2_0.tex` | UNKNOWN | 2026-03-21 | NO | NO |
| `TFE_Specification_v2_2 (1).pdf` | UNKNOWN | 2026-03-21 | NO | NO |
| `TFE_Specification_v2_2 (1).tex` | UNKNOWN | 2026-03-21 | NO | NO |
| `TFE_Specification_v2_2.pdf` | UNKNOWN | 2026-03-21 | NO | NO |
| `TFE_Specification_v2_2.tex` | UNKNOWN | 2026-03-21 | NO | NO |
| `TFE_Specification_v2_3.pdf` | UNKNOWN | 2026-03-21 | NO | NO |
| `TFE_Specification_v2_3.tex` | UNKNOWN | 2026-03-21 | NO | NO |
| `TFE_Specification_v2_4.pdf` | UNKNOWN | 2026-03-21 | NO | NO |
| `TFE_Specification_v2_4.tex` | UNKNOWN | 2026-03-21 | NO | NO |
| `TFE_Specification_v2_5.pdf` | UNKNOWN | 2026-03-21 | NO | NO |
| `TFE_Specification_v2_5.tex` | UNKNOWN | 2026-03-21 | NO | NO |
| `TFE_Specification_v2_7.tex` | UNKNOWN | 2026-03-21 | NO | NO |
| `TFE_Specification_v3_0_single.tex` | UNKNOWN | 2026-03-21 | NO | NO |
| `TFE_TASK5_BEHAVIOR_GAP_REPORT.md` | UNKNOWN | 2026-03-21 | NO | NO |
| `TFE_UI_WRITING_STYLE_GUIDE.md` | UNKNOWN | 2026-03-21 | NO | NO |
| `Test13-0-GlobalProtocolStandards.tex` | UNKNOWN | 2026-03-21 | NO | NO |
| `Test13-1-NoiseRobustness.tex` | UNKNOWN | 2026-03-21 | NO | NO |
| `Test13-2-AdversarialInputs.tex` | UNKNOWN | 2026-03-21 | NO | NO |
| `Test13-3-ParameterPerturbation.tex` | UNKNOWN | 2026-03-21 | NO | NO |
| `Test13-4-MemoryStress.tex` | UNKNOWN | 2026-03-21 | NO | NO |
| `Test13-5-MosaicConflict.tex` | UNKNOWN | 2026-03-21 | NO | NO |
| `Test13-6-BreathingSync.tex` | UNKNOWN | 2026-03-21 | NO | NO |
| `Test13-7-SESEvolution.tex` | UNKNOWN | 2026-03-21 | NO | NO |
| `Test13-8-CrossDomainTransfer.tex` | UNKNOWN | 2026-03-21 | NO | NO |
| `Test13-9-StabilityShock.tex` | UNKNOWN | 2026-03-21 | NO | NO |
| `Tfe Specification V2 6 Full.pdf` | UNKNOWN | 2026-03-21 | NO | NO |
| `UF-L0.docx` | UNKNOWN | 2026-03-21 | NO | NO |
| `UF-L1.docx` | UNKNOWN | 2026-03-21 | NO | NO |
| `UF-L2.docx` | UNKNOWN | 2026-03-21 | NO | NO |
| `UF-L3.docx` | UNKNOWN | 2026-03-21 | NO | NO |
| `UF-L4.docx` | UNKNOWN | 2026-03-21 | NO | NO |
| `UF-Section11-MathFramework.docx` | UNKNOWN | 2026-03-21 | NO | NO |
| `UF-Section13-ValidationSuite.docx` | ACTIVE-VALIDATION | 2026-03-21 | NO | NO |
| `UF_Core_Kernel_Security_Spec.pdf` | UNKNOWN | 2026-03-21 | NO | NO |
| `UF_Core_Kernel_Spec_with_SES (1).pdf` | UNKNOWN | 2026-03-21 | NO | NO |
| `UF_Core_Kernel_Spec_with_SES.pdf` | UNKNOWN | 2026-03-21 | NO | NO |
| `UF_Full_Spec_Guided_Walkthrough.docx` | UNKNOWN | 2026-03-21 | NO | NO |
| `UF_Guided_Walkthrough_Final.docx` | UNKNOWN | 2026-03-21 | NO | NO |
| `UF_Introduction.docx` | UNKNOWN | 2026-03-21 | NO | NO |
| `UF_Spec_v1.3.0_Final_Structure.docx` | UNKNOWN | 2026-03-21 | NO | NO |
| `UF_Spec_v1_4_0_skeleton.pdf` | UNKNOWN | 2026-03-21 | NO | NO |
| `Validation-Matrix.tex` | ACTIVE-VALIDATION | 2026-03-21 | NO | NO |
| `app.py` | UNKNOWN | 2026-03-21 | NO | NO |
| `cached_irf_feature_test.py` | UNKNOWN | 2026-03-21 | NO | YES |
| `cached_policy_schema_search.py` | UNKNOWN | 2026-03-21 | NO | YES |
| `cached_rowtrace_schema_search.py` | UNKNOWN | 2026-03-21 | NO | NO |
| `corpora/CORPUS_OPERATING_RULES.md` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `corpora/phase_c_failure_learning_corpus_v1.md` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `corpora/phase_c_production_deploy_preflight_v1.md` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `corpora/production_shell_control_corpus_v1.md` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `corpora/production_shell_control_corpus_v2.md` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `corpora/production_shell_control_corpus_v3.md` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `corpora/production_shell_control_corpus_v4.md` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `corpora/production_shell_control_corpus_v5.md` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `corpora/production_shell_life_in_day_run_v1.md` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `corpora/production_shell_system_reference_v2.md` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `corpora/step1_failure_learning_corpus_v1.md` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `data_loader.py` | UNKNOWN | 2026-03-21 | NO | NO |
| `engine.py` | UNKNOWN | 2026-03-21 | NO | NO |
| `full_universe_index_freeze_dataset.py` | UNKNOWN | 2026-03-21 | NO | NO |
| `g32_insanity_loop_runner.py` | DEAD | 2026-03-21 | NO | NO |
| `g32_thoroughbred_loop_runner.py` | DEAD | 2026-03-21 | NO | NO |
| `heuristics_registry_v1.json` | UNKNOWN | 2026-03-21 | NO | NO |
| `information_event_registry_v1.json` | ACTIVE-PROD | 2026-03-21 | NO | NO |
| `load-refresh-approval-env.sh` | UNKNOWN | 2026-03-21 | NO | NO |
| `market.py` | UNKNOWN | 2026-03-21 | NO | NO |
| `massive_tickers_raw.json` | UNKNOWN | 2026-03-21 | NO | NO |
| `not_math (1).pdf` | UNKNOWN | 2026-03-21 | NO | NO |
| `policy_h60_overrides_candidate.json` | UNKNOWN | 2026-03-21 | NO | NO |
| `policy_horizon_overrides_oos_holdout.json` | UNKNOWN | 2026-03-21 | NO | NO |
| `policy_horizon_overrides_oos_holdout_tf065.json` | UNKNOWN | 2026-03-21 | NO | NO |
| `portfolio.py` | UNKNOWN | 2026-03-21 | NO | NO |
| `portfolio_valuation_engine.py` | UNKNOWN | 2026-03-21 | NO | NO |
| `price_cache.py` | UNKNOWN | 2026-03-21 | NO | NO |
| `real_world_cleaned_universe_l5_primitive_only_row_trace_export.py` | UNKNOWN | 2026-03-21 | NO | YES |
| `real_world_cleaned_universe_l5_row_trace_export.py` | UNKNOWN | 2026-03-21 | NO | YES |
| `recommendation_policy_promotion_contract.json` | UNKNOWN | 2026-03-21 | NO | NO |
| `risk.py` | UNKNOWN | 2026-03-21 | NO | NO |
| `sector_sphere_coupling_registry_v1.json` | ACTIVE-PROD | 2026-03-21 | NO | NO |
| `setup_registry_v1.json` | UNKNOWN | 2026-03-21 | NO | NO |
| `sp500.csv` | UNKNOWN | 2026-03-21 | NO | NO |
| `start_tfe.sh` | UNKNOWN | 2026-03-21 | NO | NO |
| `strategy_registry_v1.json` | UNKNOWN | 2026-03-21 | NO | NO |
| `tfe_app_integration.py` | UNKNOWN | 2026-03-21 | NO | NO |
| `tfe_auth.py` | UNKNOWN | 2026-03-21 | NO | NO |
| `tfe_crypto_manager.py` | UNKNOWN | 2026-03-21 | NO | NO |
| `tfe_portfolio_api.py` | UNKNOWN | 2026-03-21 | NO | NO |
| `tfe_portfolio_service.py` | UNKNOWN | 2026-03-21 | NO | NO |
| `tfe_ui_page_assets.json` | UNKNOWN | 2026-03-21 | NO | NO |
| `tools/artifact_timestamp_inventory.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/audit_temporal_dataset.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/aws_bootstrap.sh` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/build_aws_run_manifest.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/build_item40_closure_check.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/build_item42_closure_check.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/build_merged_historical_row_trace.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/build_rowtrace_backfill_plan.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/build_screener_v111_descriptive_fixture.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/build_temporal_policy_dataset.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/clear_stuck_refresh_run.mjs` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/codex_notify_slack.sh` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/convert_snapshot_archive_to_rowtrace.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/discover_locked_provenance.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/eval_temporal_walkforward.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/export_screener_schema.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/freeze_production_primitive_rowtrace_fixed_snapshot.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/freeze_production_primitive_rowtrace_parallel.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/freeze_research_baseline_manifest.py` | SUPPORT-TOOL | 2026-03-21 | NO | YES |
| `tools/fresh_range_feasibility_report.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/full_dsf_h5_abstain_frontier.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/full_dsf_h5_cell_purity_audit.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/full_dsf_h5_continuous_timeblock_lab.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/full_dsf_h5_objective_lane.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/full_dsf_horizon_lab.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/h60_oos_holdout_sweep.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/h60_oos_holdout_validation.py` | ACTIVE-VALIDATION | 2026-03-21 | NO | NO |
| `tools/l4_l5_semantic_truth_audit.py` | SUPPORT-TOOL | 2026-03-21 | NO | YES |
| `tools/merge_backfilled_rowtrace.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/merge_temporal_walkforward_horizons.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/migrate_legacy_portfolio_envelopes.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/production_freeze_fixed_snapshot_equivalence.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/promote_runtime_policy_from_lane.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/recommendation_competitive_benchmark_lane.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/recommendation_data_remediation_lane.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/recommendation_policy_quality_sweep_lane.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/recommendation_rule_ablation_lane.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/recommendation_target_recalibration_lane.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/reconcile_temporal_gate_logic.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/refresh_failure_protocol.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/regenerate_fresh_temporal_rowtrace_from_raw.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/regenerate_historical_rowtrace_from_raw.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/replay_publication_activation_run.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/run_epoch_channel_decomposition_microprobe.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/run_fast_temporal_structural_conformance_gate.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/run_l5_db_native_preflight_in_ecs_network.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/run_production_fixed_snapshot_gate_distribution.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/run_production_fixed_snapshot_one_sided_contested_audit.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/run_production_fixed_snapshot_remaining_validation.mjs` | ACTIVE-VALIDATION | 2026-03-21 | NO | NO |
| `tools/run_production_latest_snapshot_fixed_snapshot.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/run_recommendation_lab_offline_cycle.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/run_recommendations_consistency_probe_lane.sh` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/run_refresh_task_with_live_network.sh` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/run_remote_full_cycle.sh` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/run_screener_tab_order_probe_lane.sh` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/run_screener_ui_parity_probe_lane.sh` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/run_temporal_structural_conformance_diagnosis.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/run_uf_dynamic_decision_native_rowtrace_eval.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/run_watchlist_confidence_probe_lane.sh` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/runtime_evidence_retention.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/sync_baseline_to_external.sh` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/sync_from_aws.sh` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/sync_to_aws.sh` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/taxonomy_source_completeness_probe.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/temporal_stage_loss_accounting.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/verify_phase_c_publication_bundle_contract.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/verify_phase_d_hotfix_lane_integration.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/verify_phase_d_real_shell_hotfix_lane.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/verify_phase_d_release_gate_classes.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/verify_scheduled_refresh_run.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/verify_screener_parity_matrix.mjs` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/verify_screener_table_filter_behavior.mjs` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `tools/verify_step1_cutover_readonly.py` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `uf_canonical_bootstrap.txt` | UNKNOWN | 2026-03-21 | NO | NO |
| `uf_energy_entropy_phase_map.py` | UNKNOWN | 2026-03-21 | NO | YES |
| `uf_engine_aws_service.py` | UNKNOWN | 2026-03-21 | NO | YES |
| `uf_engine_ses_adapter.py` | UNKNOWN | 2026-03-21 | NO | NO |
| `uf_kernel_engine.py` | UNKNOWN | 2026-03-21 | NO | YES |
| `uf_lessons_learned_audit_ingestion_method.txt` | UNKNOWN | 2026-03-21 | NO | NO |
| `uf_mdg_v02_regime_backtest.py` | UNKNOWN | 2026-03-21 | NO | NO |
| `uf_snapshot_cache.py` | UNKNOWN | 2026-03-21 | NO | NO |
| `uf_structural_episodes_log.py` | UNKNOWN | 2026-03-21 | NO | YES |
| `web/.gitignore` | SUPPORT-TOOL | 2026-03-21 | NO | NO |
| `web/README.md` | UNKNOWN | 2026-03-21 | NO | NO |
| `web/eslint.config.mjs` | UNKNOWN | 2026-03-21 | NO | NO |
| `web/scripts/run_uf_dynamic_decision_accumulate_envelope_widen_scan.mjs` | ACTIVE-PROD | 2026-03-21 | NO | NO |
| `web/scripts/run_uf_dynamic_decision_anchor_accuracy_surface.mjs` | ACTIVE-PROD | 2026-03-21 | NO | NO |
| `web/scripts/run_uf_dynamic_decision_anchor_neighborhood_scan.mjs` | ACTIVE-PROD | 2026-03-21 | NO | NO |
| `web/scripts/run_uf_dynamic_decision_anchor_structure_extract.py` | ACTIVE-PROD | 2026-03-21 | NO | NO |
| `web/scripts/run_uf_dynamic_decision_answer_conditioned_accumulate_strict_subset.py` | ACTIVE-PROD | 2026-03-21 | NO | NO |
| `web/scripts/run_uf_dynamic_decision_answer_conditioned_comparison.py` | ACTIVE-PROD | 2026-03-21 | NO | NO |
| `web/scripts/run_uf_dynamic_decision_answer_conditioned_structure_extract.py` | ACTIVE-PROD | 2026-03-21 | NO | NO |
| `web/scripts/run_uf_dynamic_decision_oracle_eval.mjs` | ACTIVE-PROD | 2026-03-21 | NO | NO |
| `web/scripts/run_uf_dynamic_decision_pressure_test.mjs` | ACTIVE-PROD | 2026-03-21 | NO | NO |
| `web/src/lib/uf-dynamic-decision-pressure-test.ts` | ACTIVE-PROD | 2026-03-21 | NO | NO |
| `web/src/lib/uf-dynamic-decision-unified-field.ts` | ACTIVE-PROD | 2026-03-21 | NO | NO |
| `web/src/lib/uf-dynamic-decision.ts` | ACTIVE-PROD | 2026-03-21 | NO | NO |
| `.devcontainer/devcontainer.json` | SUPPORT-TOOL | 2026-03-26 | NO | NO |
| `DSF_CLEAN_WALKFORWARD_REPLAY_WITH_SYMBOL_MEMORY_V1.md` | UNKNOWN | 2026-03-26 | NO | NO |
| `DSF_GOVERNANCE_HANDOFF_FROM_FROZEN_PRIMITIVE.md` | UNKNOWN | 2026-03-26 | NO | NO |
| `DSF_HISTORICAL_FULL_SURFACE_SNAPSHOT_ARCHIVE.md` | UNKNOWN | 2026-03-26 | NO | NO |
| `DSF_PRIMITIVE_BK_RECOVERY.md` | UNKNOWN | 2026-03-26 | NO | NO |
| `DSF_PRIMITIVE_FULL_FIELD_SORTABLE_V1.md` | UNKNOWN | 2026-03-26 | NO | NO |
| `DSF_PRIMITIVE_FULL_FIELD_SORTABLE_V3_PREVIEW.md` | UNKNOWN | 2026-03-26 | NO | NO |
| `DSF_PRIMITIVE_FULL_FIELD_SORTABLE_V3_RATIONALIZED.md` | UNKNOWN | 2026-03-26 | NO | NO |
| `DSF_PRIMITIVE_INTERPRETATION_RECOVERY.md` | UNKNOWN | 2026-03-26 | NO | NO |
| `GEMINI.md` | UNKNOWN | 2026-03-26 | NO | NO |
| `L5_CANONICAL_BASELINE.md` | UNKNOWN | 2026-03-26 | NO | NO |
| `LOAD_DIRECTIVE_NEXT_CHAT.md` | UNKNOWN | 2026-03-26 | NO | NO |
| `expanded_universe_l5.csv` | UNKNOWN | 2026-03-26 | NO | NO |
| `l0_l4_integrity_probe.py` | UNKNOWN | 2026-03-26 | NO | YES |
| `live_accumulate_safe_history_l5.csv` | UNKNOWN | 2026-03-26 | NO | NO |
| `live_accumulate_universe_l5.csv` | UNKNOWN | 2026-03-26 | NO | NO |
| `quarantine_12k_governed_l5_trades.csv` | SUPPORT-TOOL | 2026-03-26 | NO | NO |
| `quarantine_12k_ingest.py` | SUPPORT-TOOL | 2026-03-26 | NO | NO |
| `quarantine_12k_l5_trades.csv` | SUPPORT-TOOL | 2026-03-26 | NO | NO |
| `quarantine_backtester.py` | SUPPORT-TOOL | 2026-03-26 | NO | NO |
| `quarantine_base_pool_truth.py` | SUPPORT-TOOL | 2026-03-26 | NO | NO |
| `quarantine_bottleneck_diagnostic.py` | SUPPORT-TOOL | 2026-03-26 | NO | NO |
| `quarantine_governance_sweeper.py` | SUPPORT-TOOL | 2026-03-26 | NO | NO |
| `quarantine_historical_kernel.py` | SUPPORT-TOOL | 2026-03-26 | NO | NO |
| `quarantine_ingest.py` | SUPPORT-TOOL | 2026-03-26 | NO | NO |
| `quarantine_l5_trades.csv` | SUPPORT-TOOL | 2026-03-26 | NO | NO |
| `quarantine_primitive_governance_join.py` | SUPPORT-TOOL | 2026-03-26 | NO | NO |
| `quarantine_sequential_filter.py` | SUPPORT-TOOL | 2026-03-26 | NO | NO |
| `standalone_truth_kernel.py` | UNKNOWN | 2026-03-26 | NO | NO |
| `test_fetcher_acn.py` | TEST | 2026-03-26 | NO | NO |
| `test_pristine_cognition.py` | TEST | 2026-03-26 | NO | NO |
| `test_raw_sector.py` | TEST | 2026-03-26 | NO | NO |
| `tools/build_dsf_historical_full_surface_snapshot_archive.py` | SUPPORT-TOOL | 2026-03-26 | NO | YES |
| `tools/run_dsf_bk_recovery_audit.py` | SUPPORT-TOOL | 2026-03-26 | NO | NO |
| `tools/run_dsf_clean_walkforward_replay_with_symbol_memory_v1.py` | SUPPORT-TOOL | 2026-03-26 | NO | YES |
| `tools/run_dsf_frozen_primitive_backtest_vs_spy.py` | SUPPORT-TOOL | 2026-03-26 | NO | NO |
| `tools/run_dsf_full_field_sortable_v1.py` | SUPPORT-TOOL | 2026-03-26 | NO | NO |
| `tools/run_dsf_full_field_sortable_v3_preview.py` | SUPPORT-TOOL | 2026-03-26 | NO | NO |
| `tools/run_dsf_full_field_sortable_v3_rationalized.py` | SUPPORT-TOOL | 2026-03-26 | NO | NO |
| `tools/run_dsf_full_field_sortable_v3_rationalized_accuracy_gate.py` | SUPPORT-TOOL | 2026-03-26 | NO | NO |
| `tools/run_ufc_cgrv_identification.py` | SUPPORT-TOOL | 2026-03-26 | NO | NO |
| `tools/run_ufc_deformation_path_audit.py` | SUPPORT-TOOL | 2026-03-26 | NO | NO |
| `tools/run_ufc_dual_mode_identification.py` | SUPPORT-TOOL | 2026-03-26 | NO | NO |
| `tools/run_ufc_extremal_identification.py` | SUPPORT-TOOL | 2026-03-26 | NO | NO |
| `tools/run_ufc_four_phase_identification.py` | SUPPORT-TOOL | 2026-03-26 | NO | NO |
| `tools/run_ufc_four_phase_v5_continuation.py` | SUPPORT-TOOL | 2026-03-26 | NO | NO |
| `tools/run_ufc_four_phase_v5_full_field_lift.py` | SUPPORT-TOOL | 2026-03-26 | NO | NO |
| `tools/run_ufc_invariant_manifold_identification.py` | SUPPORT-TOOL | 2026-03-26 | NO | NO |
| `tools/run_ufc_transport_coupled_governed.py` | SUPPORT-TOOL | 2026-03-26 | NO | NO |
| `tools/run_ufc_two_order_parameter_identification.py` | SUPPORT-TOOL | 2026-03-26 | NO | NO |
| `tools/run_unified_field_tensor_validation.py` | ACTIVE-VALIDATION | 2026-03-26 | NO | NO |
| `web/scripts/test_shadow_sync.mjs` | TEST | 2026-03-26 | NO | NO |
| `audit_raw_sics.py` | UNKNOWN | 2026-03-28 | NO | NO |
| `recommendation-acceptance-gate.json` | UNKNOWN | 2026-03-28 | NO | NO |
| `tools/deploy_verify_publication_activation.py` | SUPPORT-TOOL | 2026-03-28 | NO | NO |
| `tools/verify_publication_activation_postdeploy.py` | SUPPORT-TOOL | 2026-03-28 | NO | NO |
| `web/src/components/AdminConsoleClient.module.css` | ACTIVE-PROD | 2026-03-28 | NO | NO |
| `web/src/lib/runtime-publication-bundle.ts` | ACTIVE-PROD | 2026-03-28 | NO | NO |
| `web/src/lib/watchlist-live-ingestion.ts` | ACTIVE-PROD | 2026-03-28 | NO | NO |
| `load-readonly-env.sh` | UNKNOWN | 2026-03-29 | NO | NO |
| `massive_market_data_service.py` | ACTIVE-PROD | 2026-03-29 | NO | NO |
| `massive_universe_etf.json` | ACTIVE-PROD | 2026-03-29 | NO | NO |
| `massive_universe_stocks.json` | ACTIVE-PROD | 2026-03-29 | NO | NO |
| `uf_snapshot.ses.json` | UNKNOWN | 2026-03-29 | NO | NO |
| `uf_snapshot_rebuild_report.json` | UNKNOWN | 2026-03-29 | NO | NO |
| `web/scripts/build_screener_finviz_overview_cache.py` | ACTIVE-PROD | 2026-03-29 | NO | NO |
| `web/scripts/build_screener_quote_cache.py` | ACTIVE-PROD | 2026-03-29 | NO | NO |
| `web/scripts/build_screener_quote_cache_impl.py` | ACTIVE-PROD | 2026-03-29 | NO | NO |
| `web/src/lib/investor-serving-policy.ts` | ACTIVE-PROD | 2026-03-29 | NO | NO |
| `web/src/lib/publication-state.ts` | ACTIVE-PROD | 2026-03-29 | NO | NO |
| `web/src/lib/runtime-postgres.ts` | ACTIVE-PROD | 2026-03-29 | NO | NO |
| `web/src/lib/screener-finviz-overview-cache.ts` | ACTIVE-PROD | 2026-03-29 | NO | NO |
| `tools/evaluate_recommendation_policy_snapshot.py` | ACTIVE-PROD | 2026-03-30 | NO | NO |
| `tools/run_portfolio_advisor_confidence_probe_lane.sh` | SUPPORT-TOOL | 2026-03-30 | NO | NO |
| `tools/validation_state_contract.py` | ACTIVE-VALIDATION | 2026-03-30 | NO | NO |
| `uf_core/uf_structural_engine.py` | ACTIVE-PROD | 2026-03-30 | NO | YES |
| `web/src/lib/published-decision.ts` | ACTIVE-PROD | 2026-03-30 | NO | NO |
| `DEPLOYMENT_REFERENCE.md` | UNKNOWN | 2026-03-31 | NO | NO |
| `tools/h60_deterministic_physics_audit.py` | SUPPORT-TOOL | 2026-03-31 | NO | NO |
| `tools/open_db_tunnel.sh` | SUPPORT-TOOL | 2026-03-31 | NO | NO |
| `tools/recommendation_quality_audit_lane.py` | SUPPORT-TOOL | 2026-03-31 | NO | NO |
| `tools/run_local_sync_via_tunnel.sh` | SUPPORT-TOOL | 2026-03-31 | NO | NO |

---

## Recovered Versions (Preserved Artifacts) -- 22 files

| Path | Purpose | Last Modified |
|------|---------|---------------|
| `recovered_versions/l5_policy_learning_latest_feb21.json` | Preserved artifact: l5_policy_learning_latest_feb21.json | untracked |
| `recovered_versions/l5_policy_learning_latest_feb27_deploy.json` | Preserved artifact: l5_policy_learning_latest_feb27_deploy.json | untracked |
| `recovered_versions/l5_policy_learning_latest_mar26.json` | Preserved artifact: l5_policy_learning_latest_mar26.json | untracked |
| `recovered_versions/l5_policy_learning_pipeline_feb20.py` | L5 policy learning pipeline (production path). | untracked |
| `recovered_versions/l5_policy_learning_pipeline_feb21.py` | L5 policy learning pipeline (production path). | untracked |
| `recovered_versions/l5_policy_learning_pipeline_v1_mar26.py` | Preserved artifact: l5_policy_learning_pipeline_v1_mar26.py | untracked |
| `recovered_versions/l5_policy_learning_pipeline_v2_feb20.py` | Corrected production wrapper for L5 policy learning pipeline. | untracked |
| `recovered_versions/l5_policy_learning_pipeline_v2_mar26.py` | Corrected production wrapper for L5 policy learning pipeline. | untracked |
| `recovered_versions/pscf_policy_runtime_feb20.json` | Preserved artifact: pscf_policy_runtime_feb20.json | untracked |
| `recovered_versions/pscf_policy_runtime_feb21.json` | Preserved artifact: pscf_policy_runtime_feb21.json | untracked |
| `recovered_versions/pscf_policy_runtime_feb27_deploy.json` | Preserved artifact: pscf_policy_runtime_feb27_deploy.json | untracked |
| `recovered_versions/pscf_policy_runtime_mar26.json` | Preserved artifact: pscf_policy_runtime_mar26.json | untracked |
| `recovered_versions/quarantine_12k_ingest.py` | Preserved artifact: quarantine_12k_ingest.py | untracked |
| `recovered_versions/quarantine_backtester.py` | Quarantine backtesting tool for filter validation | untracked |
| `recovered_versions/quarantine_base_pool_truth.py` | Preserved artifact: quarantine_base_pool_truth.py | untracked |
| `recovered_versions/quarantine_bottleneck_diagnostic.py` | Preserved artifact: quarantine_bottleneck_diagnostic.py | untracked |
| `recovered_versions/quarantine_governance_sweeper.py` | Preserved artifact: quarantine_governance_sweeper.py | untracked |
| `recovered_versions/quarantine_historical_kernel.py` | Historical kernel analysis in quarantine | untracked |
| `recovered_versions/quarantine_ingest.py` | Quarantine data ingestion | untracked |
| `recovered_versions/quarantine_primitive_governance_join.py` | Preserved artifact: quarantine_primitive_governance_join.py | untracked |
| `recovered_versions/quarantine_sequential_filter.py` | Sequential filter for quarantine analysis | untracked |
| `recovered_versions/tfe_l5_mar26_recovered.py` | Preserved artifact: tfe_l5_mar26_recovered.py | untracked |

---

## Production Files Not Modified in 90+ Days (before 2026-02-27) -- 118 files

Referenced in Dockerfile but untouched for 90+ days.

| Path | Last Modified | Last Modified By | Size |
|------|---------------|------------------|------|
| `alpaca_market_data_service.py` | 2026-02-22 | TFE Bot | 95 lines |
| `aws_root_key_provider.py` | 2026-02-22 | TFE Bot | 303 lines |
| `certs/rds-global-bundle.pem` | 2026-02-22 | TFE Bot | 2736 lines |
| `data/AAPL.csv` | 2026-02-22 | TFE Bot | 4 lines |
| `data/BTC-USD.csv` | 2026-02-22 | TFE Bot | 4 lines |
| `data/ETH-USD.csv` | 2026-02-22 | TFE Bot | 4 lines |
| `data/TEST.csv` | 2026-02-22 | TFE Bot | 4 lines |
| `data/VTI.csv` | 2026-02-22 | TFE Bot | 4 lines |
| `data/cache/price_snapshot.json` | 2026-02-22 | TFE Bot | 11673 lines |
| `data/cache/uf_junk.json` | 2026-02-22 | TFE Bot | 45344 lines |
| `market_data/BTC.csv` | 2026-02-22 | TFE Bot | 731 lines |
| `market_data/QQQ.csv` | 2026-02-22 | TFE Bot | 1256 lines |
| `market_data/SPY.csv` | 2026-02-22 | TFE Bot | 1256 lines |
| `massive_universe_cache_etf.py` | 2026-02-22 | TFE Bot | 102 lines |
| `massive_universe_crypto.py` | 2026-02-22 | TFE Bot | 52 lines |
| `massive_universe_index.py` | 2026-02-22 | TFE Bot | 48 lines |
| `ses_core/__init__.py` | 2026-02-22 | TFE Bot | 44 lines |
| `ses_core/aead_backend.py` | 2026-02-22 | TFE Bot | 443 lines |
| `ses_core/aws_root_key_provider.py` | 2026-02-22 | TFE Bot | 147 lines |
| `ses_core/chain_of_custody.py` | 2026-02-22 | TFE Bot | 269 lines |
| `ses_core/domain_params.py` | 2026-02-22 | TFE Bot | 195 lines |
| `ses_core/key_derivation.py` | 2026-02-22 | TFE Bot | 153 lines |
| `ses_core/tenant_id.py` | 2026-02-22 | TFE Bot | 174 lines |
| `tfe_bar_integrity.py` | 2026-02-22 | TFE Bot | 88 lines |
| `tfe_market_data.py` | 2026-02-22 | TFE Bot | 42 lines |
| `tfe_market_data_factory.py` | 2026-02-22 | TFE Bot | 64 lines |
| `tfe_market_data_service.py` | 2026-02-22 | TFE Bot | 156 lines |
| `tfe_ses_core_adapter.py` | 2026-02-22 | TFE Bot | 482 lines |
| `uf_core/Archieve/ARC1_config.py` | 2026-02-22 | TFE Bot | 57 lines |
| `uf_core/Archieve/ARC1_layer2.py` | 2026-02-22 | TFE Bot | 264 lines |
| `uf_core/Archieve/ARC1_layer3.py` | 2026-02-22 | TFE Bot | 235 lines |
| `uf_core/Archieve/ARC_1_layer4.py` | 2026-02-22 | TFE Bot | 309 lines |
| `uf_core/_init_.py` | 2026-02-22 | TFE Bot | 19 lines |
| `uf_core/config.py` | 2026-02-22 | TFE Bot | 95 lines |
| `uf_core/hardening.py` | 2026-02-22 | TFE Bot | 357 lines |
| `uf_core/hardening_actions.py` | 2026-02-22 | TFE Bot | 101 lines |
| `uf_core/hardening_controller.py` | 2026-02-22 | TFE Bot | 129 lines |
| `uf_core/layer0.py` | 2026-02-22 | TFE Bot | 169 lines |
| `uf_core/layer1.py` | 2026-02-22 | TFE Bot | 321 lines |
| `uf_core/layer2.py` | 2026-02-22 | TFE Bot | 222 lines |
| `uf_core/layer3.py` | 2026-02-22 | TFE Bot | 157 lines |
| `uf_core/layer4.py` | 2026-02-22 | TFE Bot | 246 lines |
| `uf_core/safemode.py` | 2026-02-22 | TFE Bot | 186 lines |
| `uf_core/validation/__init__.py` | 2026-02-22 | TFE Bot | 13 lines |
| `uf_core/validation/layer0 - Copy.py` | 2026-02-22 | TFE Bot | 156 lines |
| `uf_core/validation/noise_model.py` | 2026-02-22 | TFE Bot | 102 lines |
| `uf_core/validation/qa_dataset.py` | 2026-02-22 | TFE Bot | 98 lines |
| `uf_core/validation/val_baseline.py` | 2026-02-22 | TFE Bot | 90 lines |
| `uf_core/validation/val_composite_metrics.py` | 2026-02-22 | TFE Bot | 127 lines |
| `uf_core/validation/val_direction_stability.py` | 2026-02-22 | TFE Bot | 75 lines |
| `uf_core/validation/val_dsf_stability.py` | 2026-02-22 | TFE Bot | 74 lines |
| `uf_core/validation/val_gate_stability.py` | 2026-02-22 | TFE Bot | 76 lines |
| `uf_core/validation/val_metrics.py` | 2026-02-22 | TFE Bot | 201 lines |
| `uf_core/validation/val_noise.py` | 2026-02-22 | TFE Bot | 189 lines |
| `uf_core/validation/val_sensitivity_curve.py` | 2026-02-22 | TFE Bot | 97 lines |
| `uf_core/validation/val_sensitivity_sweep.py` | 2026-02-22 | TFE Bot | 90 lines |
| `uf_core/validation/val_stability_report.py` | 2026-02-22 | TFE Bot | 78 lines |
| `uf_structural_cache.json` | 2026-02-22 | TFE Bot | 217334 lines |
| `web/next.config.ts` | 2026-02-22 | TFE Bot | 7 lines |
| `web/postcss.config.mjs` | 2026-02-22 | TFE Bot | 7 lines |
| `web/public/file.svg` | 2026-02-22 | TFE Bot | 391 bytes |
| `web/public/globe.svg` | 2026-02-22 | TFE Bot | 1035 bytes |
| `web/public/landing-zen.jpg` | 2026-02-22 | TFE Bot | 2308665 bytes |
| `web/public/next.svg` | 2026-02-22 | TFE Bot | 1375 bytes |
| `web/public/uploads/1771019530856-account-accountpage.png` | 2026-02-22 | TFE Bot | 2527589 bytes |
| `web/public/uploads/1771019560017-recommendations-accountpage.png` | 2026-02-22 | TFE Bot | 2527589 bytes |
| `web/public/uploads/1771019598184-recommendations-recommendationspage.png` | 2026-02-22 | TFE Bot | 4915368 bytes |
| `web/public/uploads/1771021004354-watchlist-watchlistpage.png` | 2026-02-22 | TFE Bot | 1858317 bytes |
| `web/public/uploads/1771022274445-portfolioAdvisor-portfolioadvisdorpage.jpg` | 2026-02-22 | TFE Bot | 2602840 bytes |
| `web/public/uploads/1771029307452-legal-legalpage.jpg` | 2026-02-22 | TFE Bot | 2366736 bytes |
| `web/public/uploads/1771146411980-help-helppage.jpg` | 2026-02-22 | TFE Bot | 2499962 bytes |
| `web/public/uploads/1771147499302-support-supportpage.jpg` | 2026-02-22 | TFE Bot | 2001684 bytes |
| `web/public/uploads/1771174792200-adminConsole-adminpage.jpg` | 2026-02-22 | TFE Bot | 1937952 bytes |
| `web/public/uploads/Act1MarketScanFilter.png` | 2026-02-22 | TFE Bot | 3667572 bytes |
| `web/public/uploads/Act1iconGlass.png` | 2026-02-22 | TFE Bot | 2360558 bytes |
| `web/public/uploads/Act2Compare.png` | 2026-02-22 | TFE Bot | 2225521 bytes |
| `web/public/uploads/Act2iconGlass.png` | 2026-02-22 | TFE Bot | 2390430 bytes |
| `web/public/uploads/Act3Recommendations.png` | 2026-02-22 | TFE Bot | 2448345 bytes |
| `web/public/uploads/Act3Watchlist.png` | 2026-02-22 | TFE Bot | 2408468 bytes |
| `web/public/uploads/Act3iconGlass.png` | 2026-02-22 | TFE Bot | 2399081 bytes |
| `web/public/uploads/Act4Portfolio.png` | 2026-02-22 | TFE Bot | 2495813 bytes |
| `web/public/uploads/Act4iconGlass.png` | 2026-02-22 | TFE Bot | 2376255 bytes |
| `web/public/uploads/AdminPage.jpeg` | 2026-02-22 | TFE Bot | 1937952 bytes |
| `web/public/uploads/BarIntegrityflyin.png` | 2026-02-22 | TFE Bot | 3066524 bytes |
| `web/public/uploads/Chapter4AIinAction.mp4` | 2026-02-22 | TFE Bot | 26556 lines |
| `web/public/uploads/HomeClearGlass.png` | 2026-02-22 | TFE Bot | 2388717 bytes |
| `web/public/uploads/HomePageGlassIcon-rgba-v2.png` | 2026-02-22 | TFE Bot | 561167 bytes |
| `web/public/uploads/HomePageGlassIcon-rgba-v3.png` | 2026-02-22 | TFE Bot | 601156 bytes |
| `web/public/uploads/HomePageGlassIcon-rgba-v4-onblue.png` | 2026-02-22 | TFE Bot | 344139 bytes |
| `web/public/uploads/HomePageGlassIcon-rgba-v4.png` | 2026-02-22 | TFE Bot | 467807 bytes |
| `web/public/uploads/HomePageGlassIcon.png` | 2026-02-22 | TFE Bot | 561167 bytes |
| `web/public/uploads/LoginClearGlass.png` | 2026-02-22 | TFE Bot | 2238355 bytes |
| `web/public/uploads/LogionGlassIcon-rgba-v2.png` | 2026-02-22 | TFE Bot | 299311 bytes |
| `web/public/uploads/LogionGlassIcon-rgba-v3.png` | 2026-02-22 | TFE Bot | 331874 bytes |
| `web/public/uploads/LogionGlassIcon-rgba-v4-onblue.png` | 2026-02-22 | TFE Bot | 180213 bytes |
| `web/public/uploads/LogionGlassIcon-rgba-v4.png` | 2026-02-22 | TFE Bot | 257909 bytes |
| `web/public/uploads/LogionGlassIcon.png` | 2026-02-22 | TFE Bot | 299311 bytes |
| `web/public/uploads/Plainlanguageflyin.png` | 2026-02-22 | TFE Bot | 2527268 bytes |
| `web/public/uploads/ProprietAIflyin.png` | 2026-02-22 | TFE Bot | 1803838 bytes |
| `web/public/uploads/ResetClearGlass.png` | 2026-02-22 | TFE Bot | 2406292 bytes |
| `web/public/uploads/TickerInputsflyin.png` | 2026-02-22 | TFE Bot | 2684747 bytes |
| `web/public/uploads/Whatifflyin.png` | 2026-02-22 | TFE Bot | 2802047 bytes |
| `web/public/uploads/home-story-1-pingpong.mp4` | 2026-02-22 | TFE Bot | 128556 lines |
| `web/public/uploads/home-story-2-library.png` | 2026-02-22 | TFE Bot | 2644458 bytes |
| `web/public/vercel.svg` | 2026-02-22 | TFE Bot | 128 bytes |
| `web/public/window.svg` | 2026-02-22 | TFE Bot | 385 bytes |
| `web/src/app/admin-console/page.tsx` | 2026-02-22 | TFE Bot | 7 lines |
| `web/src/app/api/auth/sign-out/route.ts` | 2026-02-22 | TFE Bot | 55 lines |
| `web/src/app/favicon.ico` | 2026-02-22 | TFE Bot | 25931 bytes |
| `web/src/app/help/page.tsx` | 2026-02-22 | TFE Bot | 35 lines |
| `web/src/app/legal/page.tsx` | 2026-02-22 | TFE Bot | 184 lines |
| `web/src/app/page.tsx` | 2026-02-22 | TFE Bot | 13 lines |
| `web/src/app/portfolio-advisor/page.module.css` | 2026-02-22 | TFE Bot | 56 lines |
| `web/src/app/support/page.tsx` | 2026-02-22 | TFE Bot | 40 lines |
| `web/src/app/theme-preview/page.tsx` | 2026-02-22 | TFE Bot | 166 lines |
| `web/src/app/watchlist/page.tsx` | 2026-02-22 | TFE Bot | 18 lines |
| `web/src/lib/external-url.ts` | 2026-02-22 | TFE Bot | 42 lines |
| `web/tsconfig.json` | 2026-02-22 | TFE Bot | 34 lines |

---

## UNKNOWN Status Files (Flagged for Review) -- 310 files

| Path | Purpose | Last Modified | Imported By |
|------|---------|---------------|-------------|
| `ADVANCED_LOCALIZED_THERMODYNAMICS___ASYMMETRIC_EXHAUSTION.pdf` | PDF document: ADVANCED_LOCALIZED_THERMODYNAMICS___ASYMMETRIC_EXHAUSTION.pdf | 2026-04-22 |  |
| `AGENTS.md` | Agent configuration for Claude Code | 2026-04-11 | DB_NATIVE_MIGRATION_CONTRACT.md; LOAD_DIRECTIVE_NEXT_CHAT.md |
| `AWS Deployment Notes.docx` | Word document: AWS Deployment Notes.docx | 2026-03-21 |  |
| `AWS_RUNBOOK.md` | Documentation: AWS RUNBOOK | 2026-03-21 | TFE_5_3_Implementation_Plan_v1_1.md; TFE_5_3_Implementation_ |
| `Appendix A.docx` | Word document: Appendix A.docx | 2026-03-21 |  |
| `Appendix B.docx` | Word document: Appendix B.docx | 2026-03-21 |  |
| `ArcLoom_LoomCore_RNA3D_Spec_v0_1.pdf` | PDF document: ArcLoom_LoomCore_RNA3D_Spec_v0_1.pdf | 2026-03-21 |  |
| `Build a Temporal Memory Policy Layer.txt` | Text: Build a Temporal Memory Policy Layer.txt | 2026-03-21 |  |
| `CHANGELOG.md` | Documentation: CHANGELOG | 2026-05-28 | DOC_UPDATES_MAY28.md; web/scripts/execution/financial_rules. |
| `ChatGTP UF Assistant Instructions.docx` | Word document: ChatGTP UF Assistant Instructions.docx | 2026-03-21 |  |
| `DB_NATIVE_MIGRATION_CONTRACT.md` | Documentation: DB NATIVE MIGRATION CONTRACT | 2026-03-21 |  |
| `DEPLOYMENT_REFERENCE.md` | Documentation: DEPLOYMENT REFERENCE | 2026-03-31 |  |
| `DOC_UPDATES_MAY28.md` | Documentation: DOC UPDATES MAY28 | untracked |  |
| `DSF_CLEAN_WALKFORWARD_REPLAY_WITH_SYMBOL_MEMORY_V1.md` | Documentation: DSF CLEAN WALKFORWARD REPLAY WITH SYMBOL MEMORY V1 | 2026-03-26 | tools/run_dsf_clean_walkforward_replay_with_symbol_memory_v1 |
| `DSF_GOVERNANCE_HANDOFF_FROM_FROZEN_PRIMITIVE.md` | Documentation: DSF GOVERNANCE HANDOFF FROM FROZEN PRIMITIVE | 2026-03-26 | LOAD_DIRECTIVE_NEXT_CHAT.md |
| `DSF_HISTORICAL_FULL_SURFACE_SNAPSHOT_ARCHIVE.md` | Documentation: DSF HISTORICAL FULL SURFACE SNAPSHOT ARCHIVE | 2026-03-26 | tools/build_dsf_historical_full_surface_snapshot_archive.py |
| `DSF_PRIMITIVE_BK_RECOVERY.md` | Documentation: DSF PRIMITIVE BK RECOVERY | 2026-03-26 |  |
| `DSF_PRIMITIVE_FULL_FIELD_SORTABLE_V1.md` | Documentation: DSF PRIMITIVE FULL FIELD SORTABLE V1 | 2026-03-26 | tools/run_dsf_full_field_sortable_v1.py |
| `DSF_PRIMITIVE_FULL_FIELD_SORTABLE_V3_PREVIEW.md` | Documentation: DSF PRIMITIVE FULL FIELD SORTABLE V3 PREVIEW | 2026-03-26 | tools/run_dsf_full_field_sortable_v3_preview.py |
| `DSF_PRIMITIVE_FULL_FIELD_SORTABLE_V3_RATIONALIZED.md` | Documentation: DSF PRIMITIVE FULL FIELD SORTABLE V3 RATIONALIZED | 2026-03-26 | DSF_GOVERNANCE_HANDOFF_FROM_FROZEN_PRIMITIVE.md; DSF_PRIMITI |
| `DSF_PRIMITIVE_INTERPRETATION_RECOVERY.md` | Documentation: DSF PRIMITIVE INTERPRETATION RECOVERY | 2026-03-26 | DSF_PRIMITIVE_LAW_SKETCH.md; LOAD_DIRECTIVE_NEXT_CHAT.md; to |
| `DSF_PRIMITIVE_INTERPRETATION_RECOVERY_STATUS.md` | Documentation: DSF PRIMITIVE INTERPRETATION RECOVERY STATUS | 2026-03-21 |  |
| `DSF_PRIMITIVE_LAW_SKETCH.md` | Documentation: DSF PRIMITIVE LAW SKETCH | 2026-03-21 | LOAD_DIRECTIVE_NEXT_CHAT.md |
| `FMM_CF.pdf` | PDF document: FMM_CF.pdf | 2026-03-21 |  |
| `FRONTEND_MIGRATION_PLAN.md` | Documentation: FRONTEND MIGRATION PLAN | 2026-03-21 |  |
| `GEMINI.md` | Documentation: GEMINI | 2026-03-26 | DEPLOYMENT_REFERENCE.md; TFE_KERNEL_DIAGNOSTIC_20260526.md;  |
| `INGESTION LAYER + DB SCHEMA.docx` | Word document: INGESTION LAYER + DB SCHEMA.docx | 2026-03-21 | INGESTION_LAYER_DB_SCHEMA_extracted.txt |
| `INGESTION_LAYER_DB_SCHEMA_extracted.txt` | Text: INGESTION_LAYER_DB_SCHEMA_extracted.txt | 2026-03-21 | corpora/production_shell_system_reference_v2.md |
| `Information_Resonance_Fields_and_Premonition__Like_Inference_in_High__Dimensional_Histories__A_Theoretical_Framework.pdf` | PDF document: Information_Resonance_Fields_and_Premonition__Like_Inference_in_High__Dimensional_Histories__A_Theoretical_Framework.pdf | 2026-03-21 |  |
| `KERNEL_PHILOSOPHY.md` | Canonical kernel philosophy document - structural perception, not prediction | 2026-05-28 | CHANGELOG.md; DOC_UPDATES_MAY28.md; PROJECT_STATE.md; TFE_ST |
| `L5_CANONICAL_BASELINE.md` | Documentation: L5 CANONICAL BASELINE | 2026-03-26 | LOAD_DIRECTIVE_NEXT_CHAT.md; LOAD_DIRECTIVE_NEXT_CHAT_MAY19. |
| `L5_CURRENT_SYSTEM_FULL_SPEC.md` | Documentation: L5 CURRENT SYSTEM FULL SPEC | 2026-03-21 | blocked_family_field_contracts_latest.json; current_l5_code_ |
| `L5_CURRENT_SYSTEM_FULL_SPEC.tex` | LaTeX source: L5_CURRENT_SYSTEM_FULL_SPEC.tex | 2026-03-21 | blocked_family_field_contracts_latest.json; current_l5_code_ |
| `L5_CURRENT_SYSTEM_FULL_SPEC_latex.zip` | File: L5_CURRENT_SYSTEM_FULL_SPEC_latex.zip | 2026-03-21 |  |
| `LOAD_DIRECTIVE_NEXT_CHAT.md` | Documentation: LOAD DIRECTIVE NEXT CHAT | 2026-03-26 | DB_NATIVE_MIGRATION_CONTRACT.md; LOAD_DIRECTIVE_NEXT_CHAT_MA |
| `LOAD_DIRECTIVE_NEXT_CHAT_MAY19.md` | Documentation: LOAD DIRECTIVE NEXT CHAT MAY19 | 2026-05-26 |  |
| `OVERNIGHT_DELIVERY_SPEC.md` | Documentation: OVERNIGHT DELIVERY SPEC | 2026-03-21 |  |
| `PRIMITIVE_DIRECT_FIELD_STATE_CALC_DRAFT.md` | Documentation: PRIMITIVE DIRECT FIELD STATE CALC DRAFT | 2026-03-21 |  |
| `PRODUCTION_EVALUATION_CONTRACT.md` | Documentation: PRODUCTION EVALUATION CONTRACT | 2026-03-13 | LOAD_DIRECTIVE_NEXT_CHAT.md |
| `PROJECT_REALIGNMENT_PROTOCOL.docx` | Word document: PROJECT_REALIGNMENT_PROTOCOL.docx | 2026-03-21 |  |
| `PROJECT_REALIGNMENT_PROTOCOL.md` | Documentation: PROJECT REALIGNMENT PROTOCOL | 2026-03-13 |  |
| `PROJECT_STATE.md` | Project state documentation | 2026-05-28 | CHANGELOG.md; DOC_UPDATES_MAY28.md; docs/VALIDATION_ENVIRONM |
| `RNA3D Fold Stanford Challenge Kaggle Site Website Content.docx` | Word document: RNA3D Fold Stanford Challenge Kaggle Site Website Content.docx | 2026-03-21 |  |
| `SCE_Formal_Security_Model_v1_0.pdf` | PDF document: SCE_Formal_Security_Model_v1_0.pdf | 2026-03-21 |  |
| `SCE_Specification_v1_0.pdf` | PDF document: SCE_Specification_v1_0.pdf | 2026-03-21 | ses_core/aead_backend.py |
| `Section 17-19.docx` | Word document: Section 17-19.docx | 2026-03-21 |  |
| `Section 20 Glossary.docx` | Word document: Section 20 Glossary.docx | 2026-03-21 |  |
| `Section 21.docx` | Word document: Section 21.docx | 2026-03-21 |  |
| `Section 22-23.docx` | Word document: Section 22-23.docx | 2026-03-21 |  |
| `Section13-Main.tex` | LaTeX source: Section13-Main.tex | 2026-03-21 |  |
| `Spider_Eyes_GD_FMM_Specification.pdf` | PDF document: Spider_Eyes_GD_FMM_Specification.pdf | 2026-03-21 |  |
| `Spider_Eyes_Multi_Eye_Specification.pdf` | PDF document: Spider_Eyes_Multi_Eye_Specification.pdf | 2026-03-21 |  |
| `TFE_5_3_Implementation Plan v2.6.md` | Documentation: TFE 5 3 Implementation Plan v2.6 | 2026-03-21 |  |
| `TFE_5_3_Implementation_Plan_v1_1.md` | Documentation: TFE 5 3 Implementation Plan v1 1 | 2026-03-21 |  |
| `TFE_5_3_Implementation_Plan_v2_0.md` | Documentation: TFE 5 3 Implementation Plan v2 0 | 2026-03-21 |  |
| `TFE_5_3_Implementation_Plan_v2_2 (1).md` | Documentation: TFE 5 3 Implementation Plan v2 2 (1) | 2026-03-21 |  |
| `TFE_5_3_Implementation_Plan_v2_2.md` | Documentation: TFE 5 3 Implementation Plan v2 2 | 2026-03-21 |  |
| `TFE_5_3_Implementation_Plan_v2_3.md` | Documentation: TFE 5 3 Implementation Plan v2 3 | 2026-03-21 |  |
| `TFE_5_3_Implementation_Plan_v2_4.md` | Documentation: TFE 5 3 Implementation Plan v2 4 | 2026-03-21 | admin_rulebook_coverage_latest.json; blocked_family_field_co |
| `TFE_5_3_Implementation_Plan_v2_5.md` | Documentation: TFE 5 3 Implementation Plan v2 5 | 2026-03-21 |  |
| `TFE_ADMIN_CONSOLE_SPEC.md` | Documentation: TFE ADMIN CONSOLE SPEC | 2026-03-21 | TFE_TASK5_BEHAVIOR_GAP_REPORT.md |
| `TFE_AUDIT_MAY26_2026.md` | Documentation: TFE AUDIT MAY26 2026 | 2026-05-26 |  |
| `TFE_Global_Market_Engine_Summary.docx` | Word document: TFE_Global_Market_Engine_Summary.docx | 2026-03-21 |  |
| `TFE_KERNEL_DIAGNOSTIC_20260526.md` | Documentation: TFE KERNEL DIAGNOSTIC 20260526 | 2026-05-26 |  |
| `TFE_REARCHITECTURE_MASTER_PLAN_v2_7.md` | Documentation: TFE REARCHITECTURE MASTER PLAN v2 7 | 2026-03-21 | corpora/production_shell_system_reference_v2.md |
| `TFE_SOURCE_PACKAGE_FOR_REVIEW.md` | Documentation: TFE SOURCE PACKAGE FOR REVIEW | untracked |  |
| `TFE_SPECIFICATION.md` | Documentation: TFE SPECIFICATION | 2026-03-21 |  |
| `TFE_STATE_OF_SYSTEM_AND_3WA_RISK_ASSESSMENT.md` | Documentation: TFE STATE OF SYSTEM AND 3WA RISK ASSESSMENT | untracked | PROJECT_STATE.md |
| `TFE_SUBSCRIPTION_AND_CART_SPEC.md` | Documentation: TFE SUBSCRIPTION AND CART SPEC | 2026-03-21 | TFE_TASK5_BEHAVIOR_GAP_REPORT.md |
| `TFE_Spec_Internal_Review_v2_0 (1).md` | Documentation: TFE Spec Internal Review v2 0 (1) | 2026-03-21 |  |
| `TFE_Spec_Internal_Review_v2_0.md` | Documentation: TFE Spec Internal Review v2 0 | 2026-03-21 |  |
| `TFE_Spec_Internal_Review_v2_2 (1).md` | Documentation: TFE Spec Internal Review v2 2 (1) | 2026-03-21 |  |
| `TFE_Spec_Internal_Review_v2_2.md` | Documentation: TFE Spec Internal Review v2 2 | 2026-03-21 |  |
| `TFE_Spec_Internal_Review_v2_3.md` | Documentation: TFE Spec Internal Review v2 3 | 2026-03-21 |  |
| `TFE_Spec_Internal_Review_v2_4.md` | Documentation: TFE Spec Internal Review v2 4 | 2026-03-21 | heuristics_registry_v1.json; information_event_registry_v1.j |
| `TFE_Specification_v1_1 (1).pdf` | PDF document: TFE_Specification_v1_1 (1).pdf | 2026-03-21 |  |
| `TFE_Specification_v1_1.pdf` | PDF document: TFE_Specification_v1_1.pdf | 2026-03-21 |  |
| `TFE_Specification_v2_0.pdf` | PDF document: TFE_Specification_v2_0.pdf | 2026-03-21 | TFE_Spec_Internal_Review_v2_0 (1).md; TFE_Spec_Internal_Revi |
| `TFE_Specification_v2_0.tex` | LaTeX source: TFE_Specification_v2_0.tex | 2026-03-21 | TFE_Spec_Internal_Review_v2_0 (1).md; TFE_Spec_Internal_Revi |
| `TFE_Specification_v2_2 (1).pdf` | PDF document: TFE_Specification_v2_2 (1).pdf | 2026-03-21 |  |
| `TFE_Specification_v2_2 (1).tex` | LaTeX source: TFE_Specification_v2_2 (1).tex | 2026-03-21 |  |
| `TFE_Specification_v2_2.pdf` | PDF document: TFE_Specification_v2_2.pdf | 2026-03-21 | TFE_5_3_Implementation_Plan_v2_2 (1).md; TFE_5_3_Implementat |
| `TFE_Specification_v2_2.tex` | LaTeX source: TFE_Specification_v2_2.tex | 2026-03-21 | TFE_5_3_Implementation_Plan_v2_2 (1).md; TFE_5_3_Implementat |
| `TFE_Specification_v2_3.pdf` | PDF document: TFE_Specification_v2_3.pdf | 2026-03-21 | TFE_5_3_Implementation_Plan_v2_3.md; TFE_Spec_Internal_Revie |
| `TFE_Specification_v2_3.tex` | LaTeX source: TFE_Specification_v2_3.tex | 2026-03-21 | TFE_5_3_Implementation_Plan_v2_3.md; TFE_Spec_Internal_Revie |
| `TFE_Specification_v2_4.pdf` | PDF document: TFE_Specification_v2_4.pdf | 2026-03-21 | admin_rulebook_coverage_latest.json; blocked_family_field_co |
| `TFE_Specification_v2_4.tex` | LaTeX source: TFE_Specification_v2_4.tex | 2026-03-21 | admin_rulebook_coverage_latest.json; blocked_family_field_co |
| `TFE_Specification_v2_5.pdf` | PDF document: TFE_Specification_v2_5.pdf | 2026-03-21 |  |
| `TFE_Specification_v2_5.tex` | LaTeX source: TFE_Specification_v2_5.tex | 2026-03-21 |  |
| `TFE_Specification_v2_7.tex` | LaTeX source: TFE_Specification_v2_7.tex | 2026-03-21 | corpora/production_shell_system_reference_v2.md |
| `TFE_Specification_v3_0_single.tex` | LaTeX source: TFE_Specification_v3_0_single.tex | 2026-03-21 |  |
| `TFE_TASK5_BEHAVIOR_GAP_REPORT.md` | Documentation: TFE TASK5 BEHAVIOR GAP REPORT | 2026-03-21 |  |
| `TFE_TODO_LIST.md` | Documentation: TFE TODO LIST | 2026-04-22 | DB_NATIVE_MIGRATION_CONTRACT.md; PROJECT_REALIGNMENT_PROTOCO |
| `TFE_UI_WRITING_STYLE_GUIDE.md` | Documentation: TFE UI WRITING STYLE GUIDE | 2026-03-21 | TFE_TASK5_BEHAVIOR_GAP_REPORT.md |
| `Test13-0-GlobalProtocolStandards.tex` | LaTeX source: Test13-0-GlobalProtocolStandards.tex | 2026-03-21 | Section13-Main.tex |
| `Test13-1-NoiseRobustness.tex` | LaTeX source: Test13-1-NoiseRobustness.tex | 2026-03-21 | Section13-Main.tex |
| `Test13-2-AdversarialInputs.tex` | LaTeX source: Test13-2-AdversarialInputs.tex | 2026-03-21 | Section13-Main.tex |
| `Test13-3-ParameterPerturbation.tex` | LaTeX source: Test13-3-ParameterPerturbation.tex | 2026-03-21 | Section13-Main.tex |
| `Test13-4-MemoryStress.tex` | LaTeX source: Test13-4-MemoryStress.tex | 2026-03-21 | Section13-Main.tex |
| `Test13-5-MosaicConflict.tex` | LaTeX source: Test13-5-MosaicConflict.tex | 2026-03-21 | Section13-Main.tex |
| `Test13-6-BreathingSync.tex` | LaTeX source: Test13-6-BreathingSync.tex | 2026-03-21 | Section13-Main.tex |
| `Test13-7-SESEvolution.tex` | LaTeX source: Test13-7-SESEvolution.tex | 2026-03-21 | Section13-Main.tex |
| `Test13-8-CrossDomainTransfer.tex` | LaTeX source: Test13-8-CrossDomainTransfer.tex | 2026-03-21 | Section13-Main.tex |
| `Test13-9-StabilityShock.tex` | LaTeX source: Test13-9-StabilityShock.tex | 2026-03-21 | Section13-Main.tex |
| `Tfe Specification V2 6 Full.pdf` | PDF document: Tfe Specification V2 6 Full.pdf | 2026-03-21 |  |
| `UF-L0.docx` | Word document: UF-L0.docx | 2026-03-21 |  |
| `UF-L1.docx` | Word document: UF-L1.docx | 2026-03-21 |  |
| `UF-L2.docx` | Word document: UF-L2.docx | 2026-03-21 |  |
| `UF-L3.docx` | Word document: UF-L3.docx | 2026-03-21 |  |
| `UF-L4.docx` | Word document: UF-L4.docx | 2026-03-21 |  |
| `UF-Section11-MathFramework.docx` | Word document: UF-Section11-MathFramework.docx | 2026-03-21 |  |
| `UF_Core_Kernel_Security_Spec.pdf` | PDF document: UF_Core_Kernel_Security_Spec.pdf | 2026-03-21 |  |
| `UF_Core_Kernel_Spec_with_SES (1).pdf` | PDF document: UF_Core_Kernel_Spec_with_SES (1).pdf | 2026-03-21 |  |
| `UF_Core_Kernel_Spec_with_SES.pdf` | PDF document: UF_Core_Kernel_Spec_with_SES.pdf | 2026-03-21 |  |
| `UF_Full_Spec_Guided_Walkthrough.docx` | Word document: UF_Full_Spec_Guided_Walkthrough.docx | 2026-03-21 |  |
| `UF_Guided_Walkthrough_Final.docx` | Word document: UF_Guided_Walkthrough_Final.docx | 2026-03-21 |  |
| `UF_Introduction.docx` | Word document: UF_Introduction.docx | 2026-03-21 |  |
| `UF_Spec_v1.3.0_Final_Structure.docx` | Word document: UF_Spec_v1.3.0_Final_Structure.docx | 2026-03-21 |  |
| `UF_Spec_v1_4_0_skeleton.pdf` | PDF document: UF_Spec_v1_4_0_skeleton.pdf | 2026-03-21 |  |
| `ab_adaptive_vs_fixed_report.json` | JSON data/config: ab_adaptive_vs_fixed_report.json | untracked | .gitignore; web/src/app/api/admin/system-status/route.ts |
| `ab_adaptive_vs_fixed_sanity_samples.txt` | Text: ab_adaptive_vs_fixed_sanity_samples.txt | untracked | .gitignore; real_world_uf_audit_from_ab_sample.json |
| `accumulate_sanity_check.json` | JSON data/config: accumulate_sanity_check.json | untracked | .gitignore |
| `admin_quality_fallback_breakdown_latest.json` | JSON data/config: admin_quality_fallback_breakdown_latest.json | untracked | admin_rulebook_coverage_latest.json; exact_path_alignment_ph |
| `admin_refresh_history.jsonl` | File: admin_refresh_history.jsonl | untracked | .gitignore; web/src/app/api/admin/refresh/history/route.ts;  |
| `admin_refresh_latest.log` | Log file: admin_refresh_latest.log | untracked | .gitignore; data/cache/tfe-kill-run-bdbbc932-d92e-471c-92fe- |
| `admin_refresh_status.json` | JSON data/config: admin_refresh_status.json | untracked | .gitignore; quote_freshness_root_cause_latest.json; quote_fr |
| `admin_rulebook_coverage_latest.json` | JSON data/config: admin_rulebook_coverage_latest.json | untracked | admin_rulebook_coverage_route_check_latest.json; corpora/pro |
| `admin_rulebook_coverage_latest.md` | Documentation: admin rulebook coverage latest | untracked | admin_rulebook_coverage_route_check_latest.json; corpora/pro |
| `admin_rulebook_coverage_route_check_latest.json` | JSON data/config: admin_rulebook_coverage_route_check_latest.json | untracked | web/scripts/run_admin_rulebook_coverage_route_check.ts |
| `advisor_provenance_read_path_flag_latest.md` | Documentation: advisor provenance read path flag latest | untracked |  |
| `app.py` | Legacy Flask app entry point (dead) | 2026-03-21 |  |
| `arcloom_hdl.zip` | File: arcloom_hdl.zip | 2026-05-26 | arcloom/docs/PYNQ_DEPLOYMENT_LESSONS.md |
| `audit_raw_sics.py` | Python module: audit_raw_sics.py | 2026-03-28 |  |
| `auth_fix_verification_latest.json` | JSON data/config: auth_fix_verification_latest.json | untracked |  |
| `auth_triage_latest.json` | JSON data/config: auth_triage_latest.json | untracked | corpora/production_shell_system_reference_v2.md |
| `auth_triage_latest.md` | Documentation: auth triage latest | untracked | corpora/production_shell_system_reference_v2.md |
| `backtest_5year_results.json` | JSON data/config: backtest_5year_results.json | 2026-05-03 | tfe_5year_backtest.py |
| `backtest_universe_500.json` | JSON data/config: backtest_universe_500.json | 2026-05-03 | tfe_5year_backtest.py |
| `blocked_family_field_contracts_latest.json` | JSON data/config: blocked_family_field_contracts_latest.json | untracked | corpora/production_shell_system_reference_v2.md; web/scripts |
| `blocked_family_field_contracts_latest.md` | Documentation: blocked family field contracts latest | untracked | corpora/production_shell_system_reference_v2.md; web/scripts |
| `blocked_family_readiness_latest.json` | JSON data/config: blocked_family_readiness_latest.json | untracked | web/scripts/build_a55_activation_readiness_artifacts.mjs; we |
| `cached_irf_feature_test.py` | Cached-only deterministic feature test for IRF-aligned uncertainty drift keys. | 2026-03-21 |  |
| `cached_policy_schema_search.py` | Cached-only deterministic schema search for L5 policy cell keys. | 2026-03-21 |  |
| `cached_rowtrace_schema_search.py` | Cached-only full-universe schema search from row-trace data vs SPY benchmark. | 2026-03-21 |  |
| `coc_events_aws.log` | Log file: coc_events_aws.log | untracked |  |
| `coc_events_dev.log` | Log file: coc_events_dev.log | 2026-02-22 |  |
| `current_l5_code_truth_to_spec_gap_latest.json` | JSON data/config: current_l5_code_truth_to_spec_gap_latest.json | untracked | TFE_5_3_Implementation_Plan_v2_4.md; admin_rulebook_coverage |
| `current_l5_code_truth_to_spec_gap_latest.md` | Documentation: current l5 code truth to spec gap latest | untracked | TFE_5_3_Implementation_Plan_v2_4.md; admin_rulebook_coverage |
| `current_l5_provenance_persistence_latest.json` | JSON data/config: current_l5_provenance_persistence_latest.json | untracked | admin_rulebook_coverage_latest.json; web/scripts/build_admin |
| `data_loader.py` | Data loader utility | 2026-03-21 | Archieve_2/Arc1_data_loader.py; engine.py |
| `deploy_run.log` | Log file: deploy_run.log | untracked |  |
| `energy_entropy_output.txt` | Text: energy_entropy_output.txt | 2026-02-22 | .gitignore |
| `engine.py` | Legacy UF engine entry point (dead) | 2026-03-21 | AGENTS.md; Archieve_2/ARC_uf_engine_aws_service.py; Archieve |
| `epoch_activation_readiness_latest.json` | JSON data/config: epoch_activation_readiness_latest.json | untracked | web/scripts/build_a55_activation_readiness_artifacts.mjs |
| `epoch_projection_join_contract_latest.md` | Documentation: epoch projection join contract latest | untracked | corpora/production_shell_system_reference_v2.md; web/scripts |
| `epoch_runtime_join_semantics_latest.md` | Documentation: epoch runtime join semantics latest | untracked | web/scripts/build_a55_activation_readiness_artifacts.mjs |
| `epoch_sidecar_projection_contract_latest.md` | Documentation: epoch sidecar projection contract latest | untracked | web/scripts/build_a55_activation_readiness_artifacts.mjs |
| `epoch_state_contract_latest.json` | JSON data/config: epoch_state_contract_latest.json | untracked | corpora/production_shell_system_reference_v2.md; web/scripts |
| `epoch_state_contract_latest.md` | Documentation: epoch state contract latest | untracked | corpora/production_shell_system_reference_v2.md; web/scripts |
| `epoch_state_enum_registry_latest.json` | JSON data/config: epoch_state_enum_registry_latest.json | untracked | TFE_5_3_Implementation_Plan_v2_5.md; web/scripts/build_a55_a |
| `epoch_state_enum_registry_latest.md` | Documentation: epoch state enum registry latest | untracked | TFE_5_3_Implementation_Plan_v2_5.md; web/scripts/build_a55_a |
| `epoch_state_runtime_readiness_latest.json` | JSON data/config: epoch_state_runtime_readiness_latest.json | untracked | corpora/production_shell_system_reference_v2.md; epoch_runti |
| `epoch_structural_analysis.txt` | Text: epoch_structural_analysis.txt | 2026-05-03 | tfe_epoch_structural_history.py |
| `epoch_structural_history.json` | JSON data/config: epoch_structural_history.json | 2026-05-03 | tfe_epoch_structural_history.py |
| `exact_match_recovery_audit_latest.json` | JSON data/config: exact_match_recovery_audit_latest.json | untracked | web/scripts/build_exact_match_recovery_audit.mjs |
| `exact_match_recovery_audit_latest.md` | Documentation: exact match recovery audit latest | untracked | web/scripts/build_exact_match_recovery_audit.mjs |
| `exact_path_alignment_admin_route_check_latest.json` | JSON data/config: exact_path_alignment_admin_route_check_latest.json | untracked | web/scripts/build_exact_path_alignment_phase3_artifacts.mjs; |
| `exact_path_alignment_contract_latest.md` | Documentation: exact path alignment contract latest | untracked | exact_path_alignment_admin_route_check_latest.json; exact_pa |
| `exact_path_alignment_phase3_adoption_latest.json` | JSON data/config: exact_path_alignment_phase3_adoption_latest.json | untracked | web/scripts/build_exact_path_alignment_phase3_artifacts.mjs |
| `exact_path_alignment_phase3_adoption_latest.md` | Documentation: exact path alignment phase3 adoption latest | untracked | web/scripts/build_exact_path_alignment_phase3_artifacts.mjs |
| `exact_path_alignment_post_adoption_verification_latest.json` | JSON data/config: exact_path_alignment_post_adoption_verification_latest.json | untracked | web/scripts/build_exact_path_alignment_phase3_artifacts.mjs |
| `exact_path_alignment_readiness_latest.json` | JSON data/config: exact_path_alignment_readiness_latest.json | untracked | exact_path_alignment_admin_route_check_latest.json; exact_pa |
| `exact_path_alignment_shadow_latest.json` | JSON data/config: exact_path_alignment_shadow_latest.json | untracked | exact_path_alignment_admin_route_check_latest.json; exact_pa |
| `exact_path_alignment_shadow_latest.md` | Documentation: exact path alignment shadow latest | untracked | exact_path_alignment_admin_route_check_latest.json; exact_pa |
| `expanded_universe_l5.csv` | CSV data: expanded_universe_l5.csv | 2026-03-26 |  |
| `full_universe_index_freeze_dataset.py` | Freeze a deterministic full-universe replay dataset for policy learning/evaluation. | 2026-03-21 |  |
| `heuristics_registry_v1.json` | JSON data/config: heuristics_registry_v1.json | 2026-03-21 | TFE_5_3_Implementation_Plan_v2_4.md; admin_rulebook_coverage |
| `ingestion_pipeline_verification_latest.json` | JSON data/config: ingestion_pipeline_verification_latest.json | untracked | web/src/app/api/admin/system-status/route.ts |
| `intraday_test_cases.json` | JSON data/config: intraday_test_cases.json | 2026-05-03 |  |
| `l0_l4_integrity_probe.py` | L0-L4 pipeline integrity probe | 2026-03-26 |  |
| `l5_backtest_vs_spy_5y.json` | JSON data/config: l5_backtest_vs_spy_5y.json | untracked | .gitignore; PROJECT_REALIGNMENT_PROTOCOL.md |
| `l5_postgres_io.py` | L5 PostgreSQL I/O operations | 2026-03-13 | .dockerignore; L5_CURRENT_SYSTEM_FULL_SPEC.md; deploy_run.lo |
| `live_accumulate_safe_history_l5.csv` | CSV data: live_accumulate_safe_history_l5.csv | 2026-03-26 |  |
| `live_accumulate_universe_l5.csv` | CSV data: live_accumulate_universe_l5.csv | 2026-03-26 |  |
| `live_quote_publication_alignment_verification_latest.json` | JSON data/config: live_quote_publication_alignment_verification_latest.json | untracked | TFE_5_3_Implementation Plan v2.6.md |
| `live_quote_publish_run_latest.json` | JSON data/config: live_quote_publish_run_latest.json | untracked | TFE_5_3_Implementation Plan v2.6.md |
| `live_quote_publish_run_latest.md` | Documentation: live quote publish run latest | untracked | TFE_5_3_Implementation Plan v2.6.md |
| `load-readonly-env.sh` | Shell script: load-readonly-env.sh | 2026-03-29 | DEPLOYMENT_REFERENCE.md; load-refresh-approval-env.sh; reado |
| `load-refresh-approval-env.sh` | Shell script: load-refresh-approval-env.sh | 2026-03-21 | DEPLOYMENT_REFERENCE.md; readonly-production-verification-pa |
| `long_side_activation_readiness_latest.json` | JSON data/config: long_side_activation_readiness_latest.json | untracked | web/scripts/build_a55_activation_readiness_artifacts.mjs; we |
| `long_side_rulebook_decomposition_latest.json` | JSON data/config: long_side_rulebook_decomposition_latest.json | untracked | blocked_family_field_contracts_latest.json; long_side_subfam |
| `long_side_rulebook_decomposition_latest.md` | Documentation: long side rulebook decomposition latest | untracked | blocked_family_field_contracts_latest.json; long_side_subfam |
| `long_side_subfamily_activation_readiness_latest.json` | JSON data/config: long_side_subfamily_activation_readiness_latest.json | untracked | web/scripts/build_long_side_subfamily_contract_artifacts.mjs |
| `long_side_subfamily_blocked_dependency_matrix_latest.json` | JSON data/config: long_side_subfamily_blocked_dependency_matrix_latest.json | untracked | blocked_family_field_contracts_latest.json; quote_field_cont |
| `long_side_subfamily_contracts_latest.json` | JSON data/config: long_side_subfamily_contracts_latest.json | untracked | web/scripts/build_long_side_subfamily_contract_artifacts.mjs |
| `long_side_subfamily_contracts_latest.md` | Documentation: long side subfamily contracts latest | untracked | web/scripts/build_long_side_subfamily_contract_artifacts.mjs |
| `long_side_subfamily_hierarchy_latest.json` | JSON data/config: long_side_subfamily_hierarchy_latest.json | untracked | web/scripts/build_long_side_subfamily_contract_artifacts.mjs |
| `market.py` | Market data utilities | 2026-03-21 | $AUDIT_DIR/portfolio.body.txt; $AUDIT_DIR/watchlist_chart_ca |
| `massive_tickers_raw.json` | JSON data/config: massive_tickers_raw.json | 2026-03-21 |  |
| `not_math (1).pdf` | PDF document: not_math (1).pdf | 2026-03-21 |  |
| `pages/Arcloom_w3_1_mix_architecture_pure_and_hybid.pdf` | PDF document: Arcloom_w3_1_mix_architecture_pure_and_hybid.pdf | 2026-04-23 |  |
| `policy_h60_overrides_candidate.json` | JSON data/config: policy_h60_overrides_candidate.json | 2026-03-21 |  |
| `policy_horizon_overrides_oos_holdout.json` | JSON data/config: policy_horizon_overrides_oos_holdout.json | 2026-03-21 | tools/h60_oos_holdout_validation.py |
| `policy_horizon_overrides_oos_holdout_tf065.json` | JSON data/config: policy_horizon_overrides_oos_holdout_tf065.json | 2026-03-21 |  |
| `portfolio.py` | Portfolio data structures | 2026-03-21 | $AUDIT_DIR/account_page.body.txt; $AUDIT_DIR/portfolio.body. |
| `portfolio_manual.json` | JSON data/config: portfolio_manual.json | untracked | $AUDIT_DIR/portfolio.body.txt; .gitignore; coc_events_dev.lo |
| `portfolio_valuation_engine.py` | Portfolio valuation and P&L calculation engine | 2026-03-21 | tfe_portfolio_api.py |
| `price_cache.py` | Price caching layer | 2026-03-21 |  |
| `promotion_gate_fallback_integration_latest.md` | Documentation: promotion gate fallback integration latest | untracked | exact_path_alignment_phase3_adoption_latest.json; web/script |
| `provenance_persistence_parity_latest.json` | JSON data/config: provenance_persistence_parity_latest.json | untracked | corpora/production_shell_system_reference_v2.md; web/scripts |
| `provenance_persistence_parity_latest.md` | Documentation: provenance persistence parity latest | untracked | corpora/production_shell_system_reference_v2.md; web/scripts |
| `pscf_policy_runtime.only_c.tmp.json` | JSON data/config: pscf_policy_runtime.only_c.tmp.json | untracked |  |
| `quote_family_activation_blockers_latest.json` | JSON data/config: quote_family_activation_blockers_latest.json | untracked | web/scripts/build_a54s_contract_artifacts.mjs; web/scripts/b |
| `quote_field_contracts_latest.json` | JSON data/config: quote_field_contracts_latest.json | untracked | web/scripts/build_a54s_contract_artifacts.mjs; web/scripts/b |
| `quote_freshness_activation_blocks_latest.json` | JSON data/config: quote_freshness_activation_blocks_latest.json | untracked | web/scripts/build_quote_freshness_root_cause_artifacts.mjs;  |
| `quote_freshness_remediation_plan_latest.md` | Documentation: quote freshness remediation plan latest | untracked | TFE_5_3_Implementation_Plan_v2_5.md; web/scripts/build_quote |
| `quote_freshness_root_cause_latest.json` | JSON data/config: quote_freshness_root_cause_latest.json | untracked | TFE_5_3_Implementation_Plan_v2_5.md; web/scripts/build_quote |
| `quote_freshness_root_cause_latest.md` | Documentation: quote freshness root cause latest | untracked | TFE_5_3_Implementation_Plan_v2_5.md; web/scripts/build_quote |
| `quote_freshness_sla_latest.md` | Documentation: quote freshness sla latest | untracked | web/scripts/build_a54s_contract_artifacts.mjs; web/scripts/b |
| `quote_publication_alignment_fix_latest.json` | JSON data/config: quote_publication_alignment_fix_latest.json | untracked | web/scripts/build_quote_publication_alignment_fix_artifacts. |
| `quote_publication_alignment_fix_latest.md` | Documentation: quote publication alignment fix latest | untracked | web/scripts/build_quote_publication_alignment_fix_artifacts. |
| `quote_publication_alignment_latest.json` | JSON data/config: quote_publication_alignment_latest.json | untracked | TFE_5_3_Implementation_Plan_v2_5.md; web/scripts/build_quote |
| `quote_publication_alignment_post_fix_verification_latest.json` | JSON data/config: quote_publication_alignment_post_fix_verification_latest.json | untracked | web/scripts/build_quote_publication_alignment_fix_artifacts. |
| `quote_publication_contract_latest.md` | Documentation: quote publication contract latest | untracked | corpora/production_shell_system_reference_v2.md; web/scripts |
| `quote_publish_run_latest.json` | JSON data/config: quote_publish_run_latest.json | untracked | TFE_5_3_Implementation Plan v2.6.md |
| `quote_publish_run_latest.md` | Documentation: quote publish run latest | untracked | TFE_5_3_Implementation Plan v2.6.md |
| `quote_source_readiness_gate_latest.json` | JSON data/config: quote_source_readiness_gate_latest.json | untracked | quote_freshness_root_cause_latest.json; web/scripts/build_a5 |
| `readonly-production-verification-path.json` | JSON data/config: readonly-production-verification-path.json | untracked | .gitignore; PRODUCTION_EVALUATION_CONTRACT.md |
| `real_world_cleaned_universe_anchor_audit_l5.json` | JSON data/config: real_world_cleaned_universe_anchor_audit_l5.json | untracked | .gitignore |
| `real_world_cleaned_universe_l5_primitive_only_row_trace.csv` | CSV data: real_world_cleaned_universe_l5_primitive_only_row_trace.csv | untracked | .gitignore; DSF_PRIMITIVE_INTERPRETATION_RECOVERY.md; DSF_PR |
| `real_world_cleaned_universe_l5_primitive_only_row_trace_export.py` | Single-lane primitive row-trace export for DSF Primitive Interpretation Recovery. | 2026-03-21 | DSF_PRIMITIVE_INTERPRETATION_RECOVERY.md; DSF_PRIMITIVE_INTE |
| `real_world_cleaned_universe_l5_primitive_only_row_trace_metadata.json` | JSON data/config: real_world_cleaned_universe_l5_primitive_only_row_trace_metadata.json | untracked | .gitignore; real_world_cleaned_universe_l5_primitive_only_ro |
| `real_world_cleaned_universe_l5_row_trace_export.py` | Sliding as-of-time cleaned-universe native UF row-trace generation. | 2026-03-21 | DSF_PRIMITIVE_INTERPRETATION_RECOVERY_STATUS.md; L5_CURRENT_ |
| `real_world_cleaned_universe_l5_row_trace_full.csv` | CSV data: real_world_cleaned_universe_l5_row_trace_full.csv | 2026-03-13 | .dockerignore; DB_NATIVE_MIGRATION_CONTRACT.md; L5_CURRENT_S |
| `real_world_uf_audit_from_ab_sample.json` | JSON data/config: real_world_uf_audit_from_ab_sample.json | untracked | .gitignore; web/src/app/api/admin/system-status/route.ts |
| `real_world_uf_audit_from_ab_sample.txt` | Text: real_world_uf_audit_from_ab_sample.txt | untracked | .gitignore; web/src/app/api/admin/system-status/route.ts |
| `recommendation-acceptance-gate.json` | JSON data/config: recommendation-acceptance-gate.json | 2026-03-28 | tools/deploy_to_prod_with_evidence.sh; tools/validation_stat |
| `recommendation_policy_promotion_contract.json` | JSON data/config: recommendation_policy_promotion_contract.json | 2026-03-21 | tools/discover_locked_provenance.py; tools/promote_runtime_p |
| `risk.py` | Risk management module | 2026-03-21 | Archieve_2/ARC_uf_engine_aws_service.py; OVERNIGHT_DELIVERY_ |
| `runtime_fallback_semantics_latest.json` | JSON data/config: runtime_fallback_semantics_latest.json | untracked | admin_rulebook_coverage_latest.json; exact_path_alignment_ph |
| `runtime_provenance_schema_latest.md` | Documentation: runtime provenance schema latest | untracked | long_side_subfamily_contracts_latest.json; web/scripts/build |
| `setup_registry_v1.json` | JSON data/config: setup_registry_v1.json | 2026-03-21 | TFE_5_3_Implementation_Plan_v2_4.md; admin_rulebook_coverage |
| `snapshot_event_contracts_latest.json` | JSON data/config: snapshot_event_contracts_latest.json | untracked | web/scripts/build_a54s_contract_artifacts.mjs; web/scripts/b |
| `sp500.csv` | S&P 500 ticker list | 2026-03-21 | DB_NATIVE_MIGRATION_CONTRACT.md; energy_entropy_output.txt;  |
| `spike_transition_register.json` | JSON data/config: spike_transition_register.json | 2026-05-03 |  |
| `standalone_truth_kernel.py` | Standalone truth kernel for validation testing | 2026-03-26 |  |
| `start_tfe.sh` | Shell script: start_tfe.sh | 2026-03-21 |  |
| `strategy_registry_v1.json` | JSON data/config: strategy_registry_v1.json | 2026-03-21 | TFE_5_3_Implementation_Plan_v2_4.md; admin_rulebook_coverage |
| `structural_recency_activation_readiness_latest.json` | JSON data/config: structural_recency_activation_readiness_latest.json | untracked | web/scripts/build_a55_activation_readiness_artifacts.mjs |
| `structural_recency_contract_latest.json` | JSON data/config: structural_recency_contract_latest.json | untracked | web/scripts/build_a54s_contract_artifacts.mjs |
| `structural_recency_contract_latest.md` | Documentation: structural recency contract latest | untracked | web/scripts/build_a54s_contract_artifacts.mjs |
| `structural_recency_materialization_status_latest.json` | JSON data/config: structural_recency_materialization_status_latest.json | untracked |  |
| `structural_recency_materialization_status_latest.md` | Documentation: structural recency materialization status latest | untracked |  |
| `structural_recency_member_registry_latest.json` | JSON data/config: structural_recency_member_registry_latest.json | untracked | TFE_5_3_Implementation_Plan_v2_5.md; web/scripts/build_a55_a |
| `structural_recency_member_registry_latest.md` | Documentation: structural recency member registry latest | untracked | TFE_5_3_Implementation_Plan_v2_5.md; web/scripts/build_a55_a |
| `structural_recency_runtime_readiness_latest.json` | JSON data/config: structural_recency_runtime_readiness_latest.json | untracked | structural_recency_runtime_transport_contract_latest.md; web |
| `structural_recency_runtime_transport_contract_latest.md` | Documentation: structural recency runtime transport contract latest | untracked | web/scripts/build_a55_activation_readiness_artifacts.mjs |
| `structural_recency_schema_delta_latest.md` | Documentation: structural recency schema delta latest | untracked | web/scripts/build_a54s_contract_artifacts.mjs |
| `structural_recency_snapshot_materialization_contract_latest.md` | Documentation: structural recency snapshot materialization contract latest | untracked | web/scripts/build_a55_activation_readiness_artifacts.mjs |
| `structural_register.json` | JSON data/config: structural_register.json | 2026-05-03 | tfe_structural_register.py |
| `structural_register_500.json` | JSON data/config: structural_register_500.json | 2026-05-03 |  |
| `tau_backfill_results.json` | JSON data/config: tau_backfill_results.json | 2026-05-03 |  |
| `tau_d_calibration_filtered_dt_report.json` | JSON data/config: tau_d_calibration_filtered_dt_report.json | untracked | .gitignore; web/src/app/api/admin/system-status/route.ts |
| `tau_d_calibration_full_universe_report.json` | JSON data/config: tau_d_calibration_full_universe_report.json | untracked | .gitignore; web/src/app/api/admin/system-status/route.ts |
| `tfe_5year_backtest.py` | 5-year backtest runner for strategy validation | 2026-05-03 |  |
| `tfe_app_integration.py` | TFE app integration layer | 2026-03-21 | tfe_portfolio_api.py |
| `tfe_auth.py` | TFE authentication module | 2026-03-21 | app.py |
| `tfe_crypto_manager.py` | Cryptographic key and session management | 2026-03-21 | tfe_app_integration.py; tfe_portfolio_service.py; uf_engine_ |
| `tfe_epoch_resonance_shield.py` | Epoch resonance shield for regime-filtered entry | 2026-05-01 |  |
| `tfe_epoch_structural_history.py` | Epoch structural history tracking | 2026-05-03 |  |
| `tfe_investability_score.py` | Investability score calculator for universe filtering | 2026-04-27 |  |
| `tfe_live_manifest.csv` | CSV data: tfe_live_manifest.csv | 2026-05-03 |  |
| `tfe_portfolio_api.py` | Portfolio API endpoints | 2026-03-21 | app.py; engine.py |
| `tfe_portfolio_index.json` | JSON data/config: tfe_portfolio_index.json | 2026-02-22 | .gitignore |
| `tfe_portfolio_service.py` | Portfolio service for position tracking and valuation | 2026-03-21 | tfe_app_integration.py |
| `tfe_root_key.bin` | File: tfe_root_key.bin | 2026-02-22 | .gitignore; aws_root_key_provider.py; tfe_ses_core_adapter.p |
| `tfe_session_secret.bin` | File: tfe_session_secret.bin | untracked | .gitignore; corpora/production_shell_system_reference_v2.md; |
| `tfe_structural_register.py` | Structural register builder for universe state tracking | 2026-04-29 |  |
| `tfe_ui_page_assets.json` | JSON data/config: tfe_ui_page_assets.json | 2026-03-21 | app.py |
| `tfe_universe.json` | JSON data/config: tfe_universe.json | 2026-05-03 |  |
| `tfe_users.json` | User credentials file (should not be committed) | untracked | .gitignore; tfe_auth.py; tfe_startup.sh; tools/deploy_verify |
| `typed_fallback_ladder_schema_latest.json` | JSON data/config: typed_fallback_ladder_schema_latest.json | untracked | exact_path_alignment_phase3_adoption_latest.json; web/script |
| `typed_fallback_ladder_schema_latest.md` | Documentation: typed fallback ladder schema latest | untracked | exact_path_alignment_phase3_adoption_latest.json; web/script |
| `uf_canonical_bootstrap.txt` | Text: uf_canonical_bootstrap.txt | 2026-03-21 |  |
| `uf_energy_entropy_phase_map.py` | UF-Core Multi-Horizon Energy–Entropy Phase Map (S&P 500 Universe) | 2026-03-21 | energy_entropy_output.txt |
| `uf_engine_aws_service.py` | UF engine AWS service adapter | 2026-03-21 | Archieve_2/ARC_uf_engine_aws_service.py; TFE_TODO_LIST.md |
| `uf_engine_ses_adapter.py` | UF engine SES adapter | 2026-03-21 | uf_engine_aws_service.py |
| `uf_kernel_engine.py` | UF kernel engine (legacy entry point) | 2026-03-21 | Archieve_2/ARC_uf_engine_aws_service.py; uf_engine_aws_servi |
| `uf_lessons_learned_audit_ingestion_method.txt` | Text: uf_lessons_learned_audit_ingestion_method.txt | 2026-03-21 |  |
| `uf_mdg_v02_regime_backtest.py` | UF-Core MDG v0.2 – Regime-based backtest from structural_episodes.csv | 2026-03-21 |  |
| `uf_policy_what_if_from_row_trace.json` | JSON data/config: uf_policy_what_if_from_row_trace.json | untracked | .gitignore |
| `uf_policy_what_if_recommended_changes.csv` | CSV data: uf_policy_what_if_recommended_changes.csv | untracked | .gitignore; uf_policy_what_if_from_row_trace.json |
| `uf_snapshot.dev_current_eval.json` | JSON data/config: uf_snapshot.dev_current_eval.json | untracked | web/scripts/run_uf_dynamic_decision_accumulate_envelope_wide |
| `uf_snapshot.dev_live12.json` | JSON data/config: uf_snapshot.dev_live12.json | untracked | web/scripts/run_uf_dynamic_decision_accumulate_envelope_wide |
| `uf_snapshot.dev_replay.json` | JSON data/config: uf_snapshot.dev_replay.json | untracked |  |
| `uf_snapshot.json` | JSON data/config: uf_snapshot.json | 2026-02-22 | $AUDIT_DIR/portfolio.body.txt; $AUDIT_DIR/screener_overview. |
| `uf_snapshot.ses.json` | JSON data/config: uf_snapshot.ses.json | 2026-03-29 | .gitignore; DB_NATIVE_MIGRATION_CONTRACT.md; DEPLOYMENT_REFE |
| `uf_snapshot.ses.json.pre-aws-align.bak` | File: uf_snapshot.ses.json.pre-aws-align.bak | untracked | .gitignore |
| `uf_snapshot_cache.py` | uf_snapshot_cache.py | 2026-03-21 | app.py |
| `uf_snapshot_fresh.json` | JSON data/config: uf_snapshot_fresh.json | 2026-05-03 | tfe_structural_register.py |
| `uf_snapshot_old_backup.json` | JSON data/config: uf_snapshot_old_backup.json | 2026-02-22 | .gitignore; Archieve_2/ARC_rebuild_uf_snapshot.py; DB_NATIVE |
| `uf_snapshot_old_backup.ses.json` | JSON data/config: uf_snapshot_old_backup.ses.json | untracked | .gitignore; DB_NATIVE_MIGRATION_CONTRACT.md; rebuild_uf_snap |
| `uf_snapshot_rebuild_report.json` | JSON data/config: uf_snapshot_rebuild_report.json | 2026-03-29 | DB_NATIVE_MIGRATION_CONTRACT.md; DSF_HISTORICAL_FULL_SURFACE |
| `uf_structural_episodes_log.py` | UF-Core Structural Episodes Logger (L0–L4, NO Hardening/Safemode) | 2026-03-21 | DB_NATIVE_MIGRATION_CONTRACT.md; uf_mdg_v02_regime_backtest. |
| `unmapped_policy_keys_report.json` | JSON data/config: unmapped_policy_keys_report.json | untracked | .gitignore |
| `watchlist.csv` | User watchlist data | 2026-02-22 | $AUDIT_DIR/account_page.body.txt; $AUDIT_DIR/watchlist.body. |
| `web/.env.local` | File: .env.local | untracked | .gitignore; Archieve_2/aws_root_key_provider.py; DEPLOYMENT_ |
| `web/README.md` | Documentation: README | 2026-03-21 | docs/antenna_pcb_specification.txt |
| `web/eslint.config.mjs` | JavaScript: eslint.config.mjs | 2026-03-21 |  |
| `web/tsconfig.tsbuildinfo` | File: tsconfig.tsbuildinfo | untracked | .dockerignore; deploy_run.log; tools/validation_state_contra |

---

## Files Touching Kernel (L0-L4) -- 68 files

| Path | Status | Production |
|------|--------|-----------|
| `Archieve_2/ARC_uf_engine_aws_service.py` | DEAD | NO |
| `Archieve_2/uf_structural_engine` | DEAD | NO |
| `Archieve_2/uf_structural_engine.py` | DEAD | NO |
| `L5_CURRENT_SYSTEM_FULL_SPEC.md` | UNKNOWN | NO |
| `TFE_KERNEL_DIAGNOSTIC_20260526.md` | UNKNOWN | NO |
| `TFE_SOURCE_PACKAGE_FOR_REVIEW.md` | UNKNOWN | NO |
| `TFE_STATE_OF_SYSTEM_AND_3WA_RISK_ASSESSMENT.md` | UNKNOWN | NO |
| `TFE_TODO_LIST.md` | UNKNOWN | NO |
| `cached_irf_feature_test.py` | UNKNOWN | NO |
| `cached_policy_schema_search.py` | UNKNOWN | NO |
| `current_l5_code_truth_to_spec_gap_latest.json` | UNKNOWN | NO |
| `current_l5_code_truth_to_spec_gap_latest.md` | UNKNOWN | NO |
| `docs/VALIDATION_ENVIRONMENT_SPEC.md` | ACTIVE-VALIDATION | NO |
| `epoch_state_enum_registry_latest.json` | UNKNOWN | NO |
| `epoch_state_enum_registry_latest.md` | UNKNOWN | NO |
| `l0_l4_integrity_probe.py` | UNKNOWN | NO |
| `real_world_cleaned_universe_l5_primitive_only_row_trace_export.py` | UNKNOWN | NO |
| `real_world_cleaned_universe_l5_row_trace_export.py` | UNKNOWN | NO |
| `recovered_versions/l5_policy_learning_pipeline_feb20.py` | PRESERVED-ARTIFACT | NO |
| `recovered_versions/l5_policy_learning_pipeline_feb21.py` | PRESERVED-ARTIFACT | NO |
| `tools/build_dsf_historical_full_surface_snapshot_archive.py` | SUPPORT-TOOL | NO |
| `tools/freeze_research_baseline_manifest.py` | SUPPORT-TOOL | NO |
| `tools/l0_phase1_sync_postgres.py` | ACTIVE-PROD | YES |
| `tools/l0_phase2_bars_sync_postgres.py` | ACTIVE-PROD | YES |
| `tools/l1_phase1_sync_postgres.py` | ACTIVE-PROD | YES |
| `tools/l2_phase1_sync_postgres.py` | ACTIVE-PROD | YES |
| `tools/l3_phase1_sync_postgres.py` | ACTIVE-PROD | YES |
| `tools/l4_l5_semantic_truth_audit.py` | SUPPORT-TOOL | NO |
| `tools/l4_phase1_decision_sync_postgres.py` | ACTIVE-PROD | YES |
| `tools/l4_phase2_structural_snapshot_sync_postgres.py` | ACTIVE-PROD | YES |
| `tools/run_dsf_clean_walkforward_replay_with_symbol_memory_v1.py` | SUPPORT-TOOL | NO |
| `tools/validation_env_refresh.py` | ACTIVE-VALIDATION | NO |
| `uf_core/Archieve/ARC1_config.py` | ACTIVE-PROD | YES |
| `uf_core/Archieve/ARC1_layer2.py` | ACTIVE-PROD | YES |
| `uf_core/Archieve/ARC1_layer3.py` | ACTIVE-PROD | YES |
| `uf_core/Archieve/ARC_1_layer4.py` | ACTIVE-PROD | YES |
| `uf_core/_init_.py` | ACTIVE-PROD | YES |
| `uf_core/config.py` | ACTIVE-PROD | YES |
| `uf_core/hardening.py` | ACTIVE-PROD | YES |
| `uf_core/hardening_actions.py` | ACTIVE-PROD | YES |
| `uf_core/hardening_controller.py` | ACTIVE-PROD | YES |
| `uf_core/layer0.py` | ACTIVE-PROD | YES |
| `uf_core/layer1.py` | ACTIVE-PROD | YES |
| `uf_core/layer2.py` | ACTIVE-PROD | YES |
| `uf_core/layer3.py` | ACTIVE-PROD | YES |
| `uf_core/layer4.py` | ACTIVE-PROD | YES |
| `uf_core/safemode.py` | ACTIVE-PROD | YES |
| `uf_core/uf_structural_engine.py` | ACTIVE-PROD | YES |
| `uf_core/validation/__init__.py` | ACTIVE-PROD | YES |
| `uf_core/validation/layer0 - Copy.py` | ACTIVE-PROD | YES |
| `uf_core/validation/noise_model.py` | ACTIVE-PROD | YES |
| `uf_core/validation/qa_dataset.py` | ACTIVE-PROD | YES |
| `uf_core/validation/val_baseline.py` | ACTIVE-PROD | YES |
| `uf_core/validation/val_composite_metrics.py` | ACTIVE-PROD | YES |
| `uf_core/validation/val_direction_stability.py` | ACTIVE-PROD | YES |
| `uf_core/validation/val_dsf_stability.py` | ACTIVE-PROD | YES |
| `uf_core/validation/val_gate_stability.py` | ACTIVE-PROD | YES |
| `uf_core/validation/val_metrics.py` | ACTIVE-PROD | YES |
| `uf_core/validation/val_noise.py` | ACTIVE-PROD | YES |
| `uf_core/validation/val_sensitivity_curve.py` | ACTIVE-PROD | YES |
| `uf_core/validation/val_sensitivity_sweep.py` | ACTIVE-PROD | YES |
| `uf_core/validation/val_stability_report.py` | ACTIVE-PROD | YES |
| `uf_energy_entropy_phase_map.py` | UNKNOWN | NO |
| `uf_engine_aws_service.py` | UNKNOWN | NO |
| `uf_kernel_engine.py` | UNKNOWN | NO |
| `uf_mdg_snapshot.py` | ACTIVE-PROD | YES |
| `uf_structural_episodes_log.py` | UNKNOWN | NO |
| `web/scripts/build_a55_activation_readiness_artifacts.mjs` | ACTIVE-PROD | YES |

---

## Files Touching L5 (Entry/Exit/Sizing) -- 61 files

| Path | Status | Production |
|------|--------|-----------|
| `.dockerignore` | SUPPORT-TOOL | NO |
| `DB_NATIVE_MIGRATION_CONTRACT.md` | UNKNOWN | NO |
| `KERNEL_PHILOSOPHY.md` | UNKNOWN | NO |
| `L5_CANONICAL_BASELINE.md` | UNKNOWN | NO |
| `L5_CURRENT_SYSTEM_FULL_SPEC.md` | UNKNOWN | NO |
| `L5_CURRENT_SYSTEM_FULL_SPEC.tex` | UNKNOWN | NO |
| `L5_CURRENT_SYSTEM_FULL_SPEC_latex.zip` | UNKNOWN | NO |
| `LOAD_DIRECTIVE_NEXT_CHAT.md` | UNKNOWN | NO |
| `PROJECT_STATE.md` | UNKNOWN | NO |
| `TFE_KERNEL_DIAGNOSTIC_20260526.md` | UNKNOWN | NO |
| `TFE_SOURCE_PACKAGE_FOR_REVIEW.md` | UNKNOWN | NO |
| `TFE_STATE_OF_SYSTEM_AND_3WA_RISK_ASSESSMENT.md` | UNKNOWN | NO |
| `TFE_Specification_Merged/ch06_l5_governance.tex` | SUPPORT-TOOL | NO |
| `current_l5_code_truth_to_spec_gap_latest.json` | UNKNOWN | NO |
| `current_l5_code_truth_to_spec_gap_latest.md` | UNKNOWN | NO |
| `current_l5_provenance_persistence_latest.json` | UNKNOWN | NO |
| `docs/CP0_CP2_L5_GAP_ANALYSIS.md` | SUPPORT-TOOL | NO |
| `docs/TFE_VALIDATION_ISSUES_LOG.md` | ACTIVE-VALIDATION | NO |
| `expanded_universe_l5.csv` | UNKNOWN | NO |
| `l5_backtest_vs_spy_5y.json` | UNKNOWN | NO |
| `l5_postgres_io.py` | UNKNOWN | NO |
| `live_accumulate_safe_history_l5.csv` | UNKNOWN | NO |
| `live_accumulate_universe_l5.csv` | UNKNOWN | NO |
| `quarantine_12k_governed_l5_trades.csv` | SUPPORT-TOOL | NO |
| `quarantine_12k_l5_trades.csv` | SUPPORT-TOOL | NO |
| `quarantine_l5_trades.csv` | SUPPORT-TOOL | NO |
| `real_world_cleaned_universe_anchor_audit_l5.json` | UNKNOWN | NO |
| `real_world_cleaned_universe_l5_primitive_only_row_trace.csv` | UNKNOWN | NO |
| `real_world_cleaned_universe_l5_primitive_only_row_trace_export.py` | UNKNOWN | NO |
| `real_world_cleaned_universe_l5_primitive_only_row_trace_metadata.json` | UNKNOWN | NO |
| `real_world_cleaned_universe_l5_row_trace_export.py` | UNKNOWN | NO |
| `real_world_cleaned_universe_l5_row_trace_full.csv` | UNKNOWN | NO |
| `rebuild_uf_snapshot.py` | ACTIVE-PROD | YES |
| `recovered_versions/l5_policy_learning_latest_feb21.json` | PRESERVED-ARTIFACT | NO |
| `recovered_versions/l5_policy_learning_latest_feb27_deploy.json` | PRESERVED-ARTIFACT | NO |
| `recovered_versions/l5_policy_learning_latest_mar26.json` | PRESERVED-ARTIFACT | NO |
| `recovered_versions/l5_policy_learning_pipeline_feb20.py` | PRESERVED-ARTIFACT | NO |
| `recovered_versions/l5_policy_learning_pipeline_feb21.py` | PRESERVED-ARTIFACT | NO |
| `recovered_versions/l5_policy_learning_pipeline_v1_mar26.py` | PRESERVED-ARTIFACT | NO |
| `recovered_versions/l5_policy_learning_pipeline_v2_feb20.py` | PRESERVED-ARTIFACT | NO |
| `recovered_versions/l5_policy_learning_pipeline_v2_mar26.py` | PRESERVED-ARTIFACT | NO |
| `recovered_versions/tfe_l5_mar26_recovered.py` | PRESERVED-ARTIFACT | NO |
| `run_refresh_with_l5_learning.py` | ACTIVE-PROD | YES |
| `tfe_l5_baseline.py` | ACTIVE-PROD | YES |
| `tfe_l5_epoch_governance.py` | ACTIVE-PROD | YES |
| `tools/l4_l5_semantic_truth_audit.py` | SUPPORT-TOOL | NO |
| `tools/l5_db_native_preflight.py` | ACTIVE-PROD | YES |
| `tools/l5_phase2_sync_postgres.py` | ACTIVE-PROD | YES |
| `tools/recommendation_quality_audit_lane.py` | SUPPORT-TOOL | NO |
| `tools/run_l5_db_native_preflight_in_ecs_network.py` | SUPPORT-TOOL | NO |
| `tools/validation_state_contract.py` | ACTIVE-VALIDATION | NO |
| `web/Dockerfile` | ACTIVE-PROD | YES |
| `web/scripts/execution/alpaca_bridge.mjs` | ACTIVE-PROD | YES |
| `web/scripts/execution/ch2_strategist.mjs` | ACTIVE-PROD | YES |
| `web/scripts/execution/circuit_breaker.mjs` | ACTIVE-PROD | YES |
| `web/scripts/execution/financial_rules.mjs` | ACTIVE-PROD | YES |
| `web/scripts/execution/pee1_runner.mjs` | ACTIVE-PROD | YES |
| `web/scripts/execution/sentinel_daemon.mjs` | ACTIVE-PROD | YES |
| `web/scripts/execution/sentinel_monitor.mjs` | ACTIVE-PROD | YES |
| `web/scripts/execution/tests/sentinel_bugs_test.mjs` | ACTIVE-PROD | YES |
| `web/scripts/sync_runtime_postgres_impl.mjs` | ACTIVE-PROD | YES |
