# Production Shell Life In The Day Run v1

Generated: 2026-03-16 UTC
Status: traced model run anchored to accepted code and proof artifacts
Purpose: walk one full day-style publication cycle across the actual system boundaries so future rebuild work can be checked against one explicit flow.

## 1. Scope

This is not a new deploy proof.

It is a traced system model built from accepted evidence and current code:

- Step 1 live production proof:
  - `/workspaces/Tao_Financial_Engine/backups/runtime/step1-prod-deploy-proof-20260316T004020Z.json`
- Phase C local runtime proof:
  - `/workspaces/Tao_Financial_Engine/backups/runtime/phase-c-runtime-proof-repair-rerun-20260316T021824Z.json`
- Runtime validation repair proof:
  - `/workspaces/Tao_Financial_Engine/backups/runtime/runtime-validation-gate-repair-proof-20260316T025538Z.json`

The goal is to model the actual functioning process, inputs, outputs, authority paths, and stop gates.

## 2. Starting Conditions

Starting environment truths:

- current accepted live Step 1 deployment revision: `tfe-web-task:234`
- current accepted live Step 1 image: `418384447921.dkr.ecr.us-east-1.amazonaws.com/tfe-web:manual-20260316T004020Z`
- accepted live cutover run id: `3301a40c-a59a-4839-87fd-c936da6017c2`
- Step 1 active truth model:
  - active truth from `active_publication_pointer`
  - validity truth from `publication_bundles` plus `assessment_reports`
  - legacy `runtime_refresh_runs` validity fields are non-authoritative mirror fields

## 3. Traced Run

### Step 0: Admin Identity And Session

Input:

- admin username/password
- optional MFA code

Code:

- `/workspaces/Tao_Financial_Engine/web/src/app/api/auth/sign-in/route.ts`
- `/workspaces/Tao_Financial_Engine/web/src/lib/auth-session.ts`
- `/workspaces/Tao_Financial_Engine/web/src/lib/server-auth.ts`

Process:

- parse credentials
- authenticate user
- enforce admin MFA when enabled
- issue `tfe_session` cookie

Output:

- authenticated admin browser session

Stop gate:

- missing credentials
- invalid credentials
- invalid MFA
- auth unavailable

### Step 1: Admin Opens Control Surface

Input:

- authenticated admin request to `/admin-console`

Code:

- `/workspaces/Tao_Financial_Engine/web/src/app/admin-console/page.tsx`
- `/workspaces/Tao_Financial_Engine/web/src/components/AdminConsoleClient.tsx`

Process:

- require admin user
- load admin console UI
- expose:
  - Snapshot Refresh
  - Universe + Snapshot
  - Poll Now
  - system status
  - recommendation quality

Output:

- admin can trigger or inspect publication activity

### Step 2: Admin Starts Snapshot Publication

Input:

- `POST /api/admin/refresh`
- request body: `{"mode":"snapshot"}`
- cutover env and request contract already configured

Code:

- `/workspaces/Tao_Financial_Engine/web/src/app/api/admin/refresh/route.ts`
- `/workspaces/Tao_Financial_Engine/web/src/lib/step1/orchestrator.ts`

Process:

- route identifies existing snapshot request path
- under cutover enabled, route dispatches `step1_orchestrator`
- route does not dispatch `run_refresh_with_l5_learning.py` for this Step 1 path

Output:

- Step 1 orchestrator execution path selected

Accepted proof:

- live Step 1 proof shows `legacyRunnerDispatched=false`

Stop gate:

- missing cutover request contract
- cutover mode invalid

### Step 3: Run Request Persistence

Input:

- Step 1 cutover request contract

Code:

- `/workspaces/Tao_Financial_Engine/web/src/lib/step1/run-request.ts`
- `/workspaces/Tao_Financial_Engine/web/src/lib/step1/schema.ts`

Process:

- validate request fields
- persist request artifact
- write mirror/operator-summary run row
- write `candidate_build` phase row

Output:

- `request.json`
- one `runtime_refresh_runs` row
- one `runtime_refresh_run_phases` row

Stop gate:

- request contract invalid
- runtime Postgres not configured
- insert/write failure

### Step 4: Candidate Bundle Build

Input:

- validated run request
- normalized package id
- policy/model/config ids

Code:

- `/workspaces/Tao_Financial_Engine/web/src/lib/step1/candidate-bundle.ts`

Process:

- compute deterministic `candidate_bundle_id`
- write candidate manifest

Output:

- candidate bundle manifest
- `candidate_bundle_id`

Control rule:

- this step must not touch active publication truth

### Step 5: Assessment Report

Input:

- candidate bundle
- assessment rule set id

Code:

- `/workspaces/Tao_Financial_Engine/web/src/lib/step1/assessment-report.ts`

Process:

- assess candidate bundle
- write same-run assessment report with real execution timestamps

Output:

- `assessment_report.json`
- `assessment_report_id`
- pass/fail validity decision

Stop gate:

- forced fail case must block publication
- timestamps must reflect real execution time

### Step 6: Publication Commit

Input:

- passing assessment report
- candidate bundle identity
- target environment

Code:

- `/workspaces/Tao_Financial_Engine/web/src/lib/step1/publication-commit.ts`
- `/workspaces/Tao_Financial_Engine/web/src/lib/publication-bundle-contract.ts`

Process:

- write immutable `publication_bundle`
- write bundle manifest and digest
- write one `active_publication_pointer` row
- write one activation audit row

Output:

- `publication_bundle_id`
- active pointer switch
- publication audit record

Control rule:

- no quote-cache artifact may be consulted here

### Step 7: Deferred Follow-Up Ticket

Input:

- successful publication commit

Code:

- `/workspaces/Tao_Financial_Engine/web/src/lib/step1/followup-ticket.ts`

Process:

- resolve pointer-owned publication identity
- write durable followup ticket

Output:

- deferred or launched followup ticket
- followup job id

Observed accepted Step 1 live outcome:

- `followup_job_v1_b13633eb7699037a175f27d0`
- `phase_name=quote_cache_refresh`
- `status=deferred`

Control rule:

- follow-up failure must not roll back publication truth

### Step 8: Active Publication Read Path

Input:

- user or admin publication read request

Code:

- `/workspaces/Tao_Financial_Engine/web/src/lib/publication-state.ts`
- `/workspaces/Tao_Financial_Engine/web/src/lib/runtime-publication-bundle.ts`

Process:

- resolve active bundle from `active_publication_pointer`
- resolve validity from same-run `publication_bundles` plus `assessment_reports`

Output:

- one active publication identity for the environment
- allowed or blocked serving state

Control rule:

- do not recover authority from `runtime_refresh_runs.validation_status`, `snapshot_publication_id`, `quote_publication_id`, `quote_binding_status`, or `is_active_publication`

### Step 9: User-Facing Serving

Input:

- authenticated user requests `/recommendations` or `/screener`

Code:

- `/workspaces/Tao_Financial_Engine/web/src/app/api/recommendations/list/route.ts`
- `/workspaces/Tao_Financial_Engine/web/src/app/api/screener/route.ts`

Process:

- load canonical publication state
- load runtime snapshot and quote rows
- load published decision rows
- apply UI filters/sorts

Output:

- deterministic recommendations list
- deterministic screener rows
- one exact `publication_bundle_id` behind the response

### Step 10: Non-Critical Enrichment And Parity

Input:

- active publication identity
- parity credentials/base URL when configured

Code:

- quote follow-up ticket path
- `/workspaces/Tao_Financial_Engine/web/scripts/build_screener_finviz_overview_cache.py`
- `/workspaces/Tao_Financial_Engine/tools/run_screener_ui_parity_probe_lane.sh`
- `/workspaces/Tao_Financial_Engine/tools/verify_screener_parity_matrix.mjs`

Process:

- quote enrichment
- Finviz overview cache build
- screener parity probe

Output:

- enriched quote/admin artifacts
- parity diagnostics

Control rule:

- this plane is non-critical unless explicitly promoted
- it must not silently take authority over publication success

### Step 11: Validation And Gate Control

Input:

- live environment publication state
- current task definition

Code:

- `/workspaces/Tao_Financial_Engine/web/scripts/run_validation_gate_v1.mjs`

Process:

- validate cutover authority model under `oracle_integrity`
- keep legacy path behavior unchanged for non-cutover paths

Output:

- runtime validation pass/fail

Accepted repaired truth:

- live runtime validation on task definition `234` now passes under the cutover authority model

## 4. Authority Map Used In This Run

| Concern | Authority | Non-authority |
|---|---|---|
| active publication truth | `active_publication_pointer` | `runtime_refresh_runs.is_active_publication` |
| publication validity truth | `publication_bundles` + same-run `assessment_reports` | `runtime_refresh_runs.validation_status` |
| publication manifest identity | `publication_bundles` + manifest digest | quote cache file, log text |
| user auth truth | session cookie + user store | client-side page state |
| phase/observability truth | `runtime_refresh_run_phases` | ad hoc log-tail inference |
| quote-governed identity | explicit quote publication contract | timestamp-only freshness guesses |

## 5. Failure Stops In This Modeled Run

Hard stop conditions:

1. sign-in/auth unavailable
2. cutover request contract missing or invalid
3. Step 1 persistence write failure
4. candidate assessment fail
5. publication commit prerequisite mismatch
6. canonical publication bundle prerequisite mismatch
7. runtime validation fail under current authority model

Non-hard-stop items by rule:

1. quote follow-up deferred/fail after publication
2. UI parity probe fail
3. Finviz overlay lag
4. legacy mirror fields remaining unset

## 6. What This Traced Run Proves And Does Not Prove

What it proves:

- the system can be modeled as one explicit chain with named inputs, processes, outputs, stores, and gates
- the accepted Step 1 and local Phase C proofs fit that chain without needing legacy run-header validity authority
- the validator must be aligned to the same authority model or it becomes a false blocker

What it does not prove:

- that the next Phase C production deploy-proof cycle will pass
- that quote-publication contract work is complete
- that epoch library/runtime projection work is complete
- that all admin/internal governance families are production-active

## 7. Next Strict Use

This file should be used before the next Phase C deploy attempt to check:

1. all inputs are explicit
2. each step writes only its allowed outputs
3. each reader trusts only its declared authority
4. validators block only on declared critical-path truth
