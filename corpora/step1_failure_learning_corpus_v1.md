# Step 1 Failure Learning Corpus v1

## Purpose

This file remains the external memory for the accepted Step 1 cutover closure.

It also serves as the handoff boundary into the current broader control corpus:

- `/workspaces/Tao_Financial_Engine/corpora/production_shell_control_corpus_v5.md`

This file stays focused on what was proved for Step 1 and what later work must not undo.

## Scope

This corpus covers only the accepted `Production Shell` Step 1 cutover closure and its handoff constraints.

It does not cover:

- the full Phase C workstream
- the full Phase D workstream
- later phases
- DSF-AI core

## Current Truth

As of `2026-03-16T05:54:00Z`:

- Step 1 remains closed within its narrow accepted scope
- the accepted live production proof artifact remains:
  `/workspaces/Tao_Financial_Engine/backups/runtime/step1-prod-deploy-proof-20260316T004020Z.json`
- the accepted closure artifact remains:
  `/workspaces/Tao_Financial_Engine/backups/runtime/step1-closure-decision-20260316T010629Z.md`
- the current active workstream is now Phase D
- the current control surface for post-Step-1 work is:
  `/workspaces/Tao_Financial_Engine/corpora/production_shell_control_corpus_v5.md`

## Step 1 Authority Map

Under the accepted Step 1 cutover model:

- `active_publication_pointer` is authoritative for active publication truth
- `assessment_reports` plus `publication_bundles` are authoritative for validity truth
- `runtime_refresh_runs` is mirror/operator-summary truth only
- `runtime_decisions_latest` is non-authoritative metadata only under cutover

`runtime_refresh_runs` must not be made authoritative again for:

- `validation_status`
- `snapshot_publication_id`
- `quote_publication_id`
- `quote_binding_status`
- `is_active_publication`

## Accepted Step 1 Proof Chain

Accepted Step 1 artifacts in order:

- `/workspaces/Tao_Financial_Engine/backups/runtime/step1-clean-replacement-process-20260315T200443Z.md`
- `/workspaces/Tao_Financial_Engine/backups/runtime/step1-cutover-implementation-plan-20260315T203622Z.md`
- `/workspaces/Tao_Financial_Engine/backups/runtime/step1-slice1-proof-20260315T205239Z.json`
- `/workspaces/Tao_Financial_Engine/backups/runtime/step1-slice2-proof-20260315T210512Z.json`
- `/workspaces/Tao_Financial_Engine/backups/runtime/step1-slice3-proof-20260315T212810Z.json`
- `/workspaces/Tao_Financial_Engine/backups/runtime/step1-slice4-proof-20260315T220538Z.json`
- `/workspaces/Tao_Financial_Engine/backups/runtime/step1-slice5-proof-20260315T221600Z.json`
- `/workspaces/Tao_Financial_Engine/backups/runtime/step1-final-cutover-seam-repair-proof-20260315T224746Z.json`
- `/workspaces/Tao_Financial_Engine/backups/runtime/step1-cutover-authority-repair-proof-20260315T232644Z.json`
- `/workspaces/Tao_Financial_Engine/backups/runtime/step1-build-gate-proof-20260315T234014Z.json`
- `/workspaces/Tao_Financial_Engine/backups/runtime/step1-postgres-prereq-proof-20260316T001901Z.json`
- `/workspaces/Tao_Financial_Engine/backups/runtime/step1-runtime-gate-proof-20260316T003225Z.json`
- `/workspaces/Tao_Financial_Engine/backups/runtime/step1-prod-deploy-proof-20260316T004020Z.json`
- `/workspaces/Tao_Financial_Engine/backups/runtime/step1-closure-decision-20260316T010629Z.md`
- `/workspaces/Tao_Financial_Engine/backups/runtime/step1-closure-adversarial-challenge-20260316T010959Z.md`
- `/workspaces/Tao_Financial_Engine/backups/runtime/step1-residual-debt-register-20260316T011409Z.md`

## Step 1 Failure Registry

### Failure 1

- Artifact:
  `/workspaces/Tao_Financial_Engine/backups/runtime/step1-prod-deploy-blocker-20260315T230547Z.json`
- Exact blocker:
  Step 1 cutover active publication validity still depended on legacy `runtime_refresh_runs` validity fields.
- Root cause:
  rebuilt Step 1 wrote new authority tables, but the read side still validated the pointed run using old run-header fields.
- Prevention rule:
  under cutover, resolve active truth from `active_publication_pointer` and validity from `assessment_reports` plus `publication_bundles`.

### Failure 2

- Artifact:
  `/workspaces/Tao_Financial_Engine/backups/runtime/step1-runtime-gate-blocker-20260315T235800Z.json`
- Exact blocker:
  `request_state_persistence_failure`
- Root cause:
  local production-mode runtime smoke reached the Step 1 orchestrator, but `isPostgresConfigured()` was false, so no request-state persistence could start.
- Prevention rule:
  do not rerun the full local runtime gate until local writable Postgres configuration is proved closed first.

### Failure 3

- Artifact:
  `/workspaces/Tao_Financial_Engine/backups/runtime/step1-postgres-prereq-blocker-20260316T000721Z.json`
- Exact blocker:
  `createPostgresStep1Persistence().writeRunRow(runRow)` failed with `INSERT has more target columns than expressions`.
- Root cause:
  `web/src/lib/step1/schema.ts` had a mechanically wrong `runtime_refresh_runs` INSERT.
- Prevention rule:
  for every new persistence path, require one real database write proof before any wider runtime smoke.

## Step 1 Never-Again Rules

1. Never recommend a production deploy after readonly proofs alone.
2. Never recommend the full local runtime smoke before writable local Postgres persistence is proved.
3. Never accept persistence claims without a real `ensureReady()`, `writeRunRow()`, and `writePhaseRow()` against Postgres.
4. Never widen scope when one exact blocker is already identified.
5. Never treat `runtime_refresh_runs` as Step 1 validity authority under cutover.
6. Never call Step 1 complete until there is one accepted live production deploy-proof cycle.
7. Never let later validators or deploy gates silently reintroduce legacy validity authority for the accepted cutover path.

## What Step 1 Proved

- The rebuilt Step 1 object chain exists
- The cutover seam exists
- The authority mismatch was repaired
- The web app builds in production mode
- Local Postgres persistence and local runtime proof passed
- The existing production snapshot request path dispatched `step1_orchestrator`
- The dead Python Step 1 runner was not used
- Live cutover run `3301a40c-a59a-4839-87fd-c936da6017c2` completed through `publication_commit` with durable deferred followup
- Active publication truth came from `active_publication_pointer` plus `publication_bundles` and `assessment_reports`
- The same run’s legacy `runtime_refresh_runs` validity fields stayed non-authoritative

## Residual Step 1 Debt

Accepted residual debt remains:

- `auxiliary_live_verifier.status=fail`
- `runtime_decisions_latest` still pointing to an older failed run during the accepted proof window

These do not reopen Step 1.
They remain deferred outside the narrow Step 1 closure scope.

## Current Handoff Rule

Step 1 stays closed.

Any current or future work on Phase C, Phase D, or later phases must use:

- `/workspaces/Tao_Financial_Engine/corpora/production_shell_control_corpus_v5.md`

as the primary control surface.

## Corpus Rule

Any future command touching the accepted Step 1 cutover boundary must:

- preserve the Step 1 authority map above
- not reopen Step 1 without one exact in-scope contradiction
- cite the current production shell control corpus for any post-Step-1 gate movement
