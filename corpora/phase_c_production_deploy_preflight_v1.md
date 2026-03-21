# Phase C Production Deploy Preflight v1

Generated: 2026-03-16 UTC
Status: preflight control artifact
Purpose: define the exact checks that must be satisfied before one controlled Phase C production deploy-proof cycle is allowed.

## 1. Scope

This artifact does not prove a live deploy.

It is the gate-control surface for one allowed next action:

- one controlled Phase C production deploy-proof cycle

This artifact is built from these accepted references:

- system reference:
  - `/workspaces/Tao_Financial_Engine/corpora/production_shell_system_reference_v2.md`
- traced run model:
  - `/workspaces/Tao_Financial_Engine/corpora/production_shell_life_in_day_run_v1.md`
- Step 1 live production proof:
  - `/workspaces/Tao_Financial_Engine/backups/runtime/step1-prod-deploy-proof-20260316T004020Z.json`
- Phase C local runtime proof:
  - `/workspaces/Tao_Financial_Engine/backups/runtime/phase-c-runtime-proof-repair-rerun-20260316T021824Z.json`
- runtime validation repair proof:
  - `/workspaces/Tao_Financial_Engine/backups/runtime/runtime-validation-gate-repair-proof-20260316T025538Z.json`

## 2. Current Gate Truth

Current accepted truth:

- Step 1 stays closed.
- The canonical publication-bundle contract passed readonly/local proof.
- The Phase C local production-runtime proof passed.
- The cutover-aware `runtime_validation` gate passed on live task definition `234`.
- No accepted Phase C production deploy-proof cycle exists yet.

Therefore the next allowed gate is:

- one controlled Phase C production deploy-proof cycle

## 3. Mandatory Authority Model

The Phase C deploy attempt must use this authority model exactly:

- active publication truth:
  - `active_publication_pointer`
- publication validity truth:
  - `publication_bundles` plus same-run `assessment_reports`
- mirror/operator-summary only:
  - `runtime_refresh_runs`

Forbidden authority recovery:

- `runtime_refresh_runs.validation_status`
- `runtime_refresh_runs.snapshot_publication_id`
- `runtime_refresh_runs.quote_publication_id`
- `runtime_refresh_runs.quote_binding_status`
- `runtime_refresh_runs.is_active_publication`

## 4. Preflight Checks

### Check 1: Existing Snapshot Request Path Still Owns The Live Entry

Required input:

- current code in `/workspaces/Tao_Financial_Engine/web/src/app/api/admin/refresh/route.ts`
- current code in `/workspaces/Tao_Financial_Engine/web/src/lib/step1/orchestrator.ts`

Pass condition:

- the existing `POST /api/admin/refresh` request path with `{"mode":"snapshot"}` is still the path used for the live deploy-proof cycle
- under cutover enabled, that path dispatches `step1_orchestrator`
- the path does not dispatch `run_refresh_with_l5_learning.py` for Step 1

Why this matters:

- the live deploy-proof must test the real production entry path, not a side path

Hard stop if false:

- do not deploy

### Check 2: Canonical Publication-Bundle Contract Remains The Read/Write Boundary

Required input:

- `/workspaces/Tao_Financial_Engine/web/src/lib/publication-bundle-contract.ts`
- `/workspaces/Tao_Financial_Engine/web/src/lib/step1/publication-commit.ts`
- `/workspaces/Tao_Financial_Engine/web/src/lib/publication-state.ts`
- `/workspaces/Tao_Financial_Engine/web/src/lib/runtime-publication-bundle.ts`

Pass condition:

- commit writes publication identity through the canonical publication-bundle contract layer
- publication-state reads active truth from `active_publication_pointer`
- publication-state and runtime-publication-bundle read validity truth from `publication_bundles` plus same-run `assessment_reports`
- same-run assessment prerequisite uses `(run_id, assessment_report_id)` and not `assessment_report_id` alone

Why this matters:

- the last exact Phase C local blocker was an ambiguous assessment prerequisite join

Hard stop if false:

- do not deploy

### Check 3: Local Runtime Model Already Passed On The Same Boundary

Required proof:

- `/workspaces/Tao_Financial_Engine/backups/runtime/phase-c-runtime-proof-repair-rerun-20260316T021824Z.json`

Pass condition:

- the local production-mode server started
- the existing snapshot request path dispatched `step1_orchestrator`
- Python spawn count for the Step 1 request path was `0`
- publication-state resolved validity from `publication_bundles` plus same-run `assessment_reports`
- runtime-publication-bundle resolved the same `publication_bundle_id`
- legacy `runtime_refresh_runs` validity fields stayed mirror only

Why this matters:

- this is the closest accepted pre-live proof for the exact boundary being promoted

Hard stop if false:

- do not deploy

### Check 4: Live Predeploy Validator Already Matches The Cutover Authority Model

Required proof:

- `/workspaces/Tao_Financial_Engine/backups/runtime/runtime-validation-gate-repair-proof-20260316T025538Z.json`

Pass condition:

- live `runtime_validation` on task definition `234` passed
- `oracle_integrity` under cutover derives validity from:
  - `active_publication_pointer`
  - `publication_bundles`
  - `assessment_reports`
- legacy non-cutover validator behavior stayed unchanged

Why this matters:

- the last exact live deploy blocker was a validator-contract mismatch, not a Phase C publication-bundle failure

Hard stop if false:

- do not deploy

### Check 5: Non-Authority Residuals Are Explicitly Non-Blocking

Residuals that may appear during the deploy-proof:

- `runtime_decisions_latest` may point to an older run
- `auxiliary_live_verifier.status` may still fail on legacy assumptions
- UI parity and non-critical UX parity may fail
- follow-up quote work may stay deferred

Pass condition:

- none of the above are treated as active-publication authority
- none of the above are allowed to override the accepted cutover authority model

Why this matters:

- these were already proven to be misleading or non-critical in earlier stages

Hard stop if false:

- do not deploy

### Check 6: Deploy-Proof Evidence Capture Is Defined Before The Attempt

The live attempt must freeze exact evidence for:

- deployed source state
- new image
- new ECS task definition
- cutover env state
- live `POST /api/admin/refresh` snapshot request response
- run id
- publication bundle id
- active pointer row
- publication bundle row
- assessment report row
- investor-serving resolved publication bundle id
- runtime validation result on the new live revision

Pass condition:

- the deploy-proof command includes all of the above evidence obligations before the deploy starts

Why this matters:

- if the evidence plan is missing, the deploy can succeed or fail without leaving a trustworthy record

Hard stop if false:

- do not deploy

## 5. Exact Failure Classification Rule For The Next Live Attempt

If the next live attempt fails:

- stop at one exact blocker only
- classify the blocker against the authority model in this artifact
- do not reopen Step 1 unless the contradiction is actually in Step 1 narrow scope
- do not widen a validator, parity, or follow-up failure into a fake publication-core failure

## 6. Exact Success Rule For The Next Live Attempt

The next live attempt is accepted only if all of these are true in live production:

1. ECS moved to a new task revision and image.
2. The existing snapshot request path dispatched `step1_orchestrator`.
3. The dead Python Step 1 runner was not used for the Step 1 request.
4. Publication commit wrote and activated through the canonical publication-bundle contract layer.
5. Publication-state resolved active truth from `active_publication_pointer`.
6. Publication-state and runtime-publication-bundle resolved validity truth from `publication_bundles` plus same-run `assessment_reports`.
7. Investor-serving resolution returned the same `publication_bundle_id`.
8. Legacy `runtime_refresh_runs` validity fields remained mirror/operator-summary only.

If any one of those is not proved, the deploy-proof cycle is not accepted.

## 7. Recommended Next Action

Recommended next action:

- one controlled Phase C production deploy-proof cycle using this artifact, `production_shell_system_reference_v2.md`, and `production_shell_life_in_day_run_v1.md` as mandatory inputs

Not recommended:

- another generic deploy attempt without this preflight
- another broad debugging pass before the next exact live proof attempt
