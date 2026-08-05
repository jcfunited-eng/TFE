# Production Shell Control Corpus v2

Generated: 2026-03-16 UTC
Status: current control surface after accepted Phase C live deploy-proof
Supersedes for current gate-state use:
- `/workspaces/Tao_Financial_Engine/corpora/production_shell_control_corpus_v1.md`

## Purpose

This file is the current evaluator control surface for the rebuilt Production Shell path after the accepted live Phase C deploy-proof.

It records only:

- current exact gate truth
- current authority truth
- current accepted live proof anchors
- current exact residual failure family
- current next allowed workstream/gate

## Scope

This corpus covers only:

- accepted Step 1 cutover closure as inherited truth
- accepted Phase C canonical publication-bundle live proof
- proof-harness/evidence-capture failures observed during the accepted Phase C cycle

It does not cover:

- DSF-AI core
- recommendation science
- epoch-library implementation completion
- quote-publication contract completion for governed families
- later implementation slices beyond current post-Phase-C transition

## Current Gate State

As of the accepted artifact:

- `/workspaces/Tao_Financial_Engine/backups/runtime/phase-c-prod-deploy-proof-20260316T041214Z.json`

the strict current truth is:

- Step 1 remains closed within its accepted narrow scope.
- Phase C live production deploy-proof is accepted.
- ECS moved to `tfe-web-task:235`.
- live image is `418384447921.dkr.ecr.us-east-1.amazonaws.com/tfe-web:manual-20260316T041214Z`.
- live proof run id is `3597430d-4d08-49d8-b76e-8a4d639cdc4a`.
- live publication bundle id is `publication_bundle_v1_514528dd972291f7f05b15b8`.
- all recorded Phase C success checks are `true`.

Therefore:

- the exact next allowed gate is not another Phase C deploy-proof cycle
- the exact next allowed item is a post-Phase-C transition decision

## Accepted Live Proof Anchors

Step 1 accepted live proof:

- `/workspaces/Tao_Financial_Engine/backups/runtime/step1-prod-deploy-proof-20260316T004020Z.json`

Phase C accepted local runtime proof:

- `/workspaces/Tao_Financial_Engine/backups/runtime/phase-c-runtime-proof-repair-rerun-20260316T021824Z.json`

Accepted runtime-validation gate repair proof:

- `/workspaces/Tao_Financial_Engine/backups/runtime/runtime-validation-gate-repair-proof-20260316T025538Z.json`

Accepted Phase C live deploy-proof:

- `/workspaces/Tao_Financial_Engine/backups/runtime/phase-c-prod-deploy-proof-20260316T041214Z.json`

## Current Authority Model

The accepted live Phase C proof preserves this authority model:

### Authoritative

- `active_publication_pointer`
  - authoritative for active publication truth
- `publication_bundles`
  - authoritative for immutable publication bundle identity and linkage
- same-run `assessment_reports`
  - authoritative for publication validity truth

### Mirror / Non-authoritative

- `runtime_refresh_runs`
  - mirror/operator-summary only
- `runtime_decisions_latest`
  - non-authoritative metadata for this path
- `auxiliary_live_verifier`
  - non-authoritative legacy observability only

### Forbidden legacy validity authority

These remain forbidden as publication-validity authority:

- `runtime_refresh_runs.validation_status`
- `runtime_refresh_runs.snapshot_publication_id`
- `runtime_refresh_runs.quote_publication_id`
- `runtime_refresh_runs.quote_binding_status`
- `runtime_refresh_runs.is_active_publication`

## What Phase C Live Proof Actually Proved

From `/workspaces/Tao_Financial_Engine/backups/runtime/phase-c-prod-deploy-proof-20260316T041214Z.json`:

1. ECS moved to a new task revision and image.
2. The existing snapshot request path dispatched `step1_orchestrator`.
3. The dead Python Step 1 runner was not used.
4. Publication commit wrote and activated through the canonical publication-bundle contract layer.
5. `publication-state` resolved active truth from `active_publication_pointer`.
6. `publication-state` and `runtime-publication-bundle` resolved validity truth from `publication_bundles` plus same-run `assessment_reports`.
7. Investor-serving resolution returned the same `publication_bundle_id`.
8. A durable deferred follow-up ticket was written.
9. Legacy `runtime_refresh_runs` validity fields stayed mirror-only.
10. Post-deploy `runtime_validation` passed.

## Phase C Proof-Harness Failure Family

This is a separate accepted failure family. It does not reopen Phase C. It must still be recorded.

### Family Name

- `phase_c_live_proof_harness_drift`

### Exact observed failures

#### Failure A: false blocker from response-parser drift

Artifact:

- `/workspaces/Tao_Financial_Engine/backups/runtime/phase-c-prod-deploy-blocker-20260316T041214Z-continuation.json`

Exact bad conclusion:

- blocker claimed `snapshot_request_did_not_dispatch_cutover_orchestrator`

Why that blocker was false:

- `dispatchPath` was already `step1_orchestrator`
- `legacyRunnerDispatched` was already `false`
- the corrected response body already contained `result.runId="3597430d-4d08-49d8-b76e-8a4d639cdc4a"`

Real root cause:

- proof harness read the live response incorrectly and froze a blocker against stale parser assumptions

#### Failure B: live SQL schema-drift bug

Evidence trail:

- same Phase C evidence directory

Exact fault:

- live SQL selected non-existent column `requested_at` from `runtime_refresh_runs`

Impact:

- authority query failed before it could produce machine-readable evidence

Real root cause:

- proof SQL was not schema-checked against the live table before execution

#### Failure C: interactive ECS JSON capture corruption

Evidence:

- `/workspaces/Tao_Financial_Engine/backups/runtime/phase-c-prod-deploy-cycle-20260316T041214Z/live-authority.execute.stdout.txt`

Exact fault:

- interactive ECS session wrapped/paged JSON output
- the payload became unusable for direct machine parsing

#### Failure D: wrong recovery assumption about non-interactive execute-command

Evidence:

- `/workspaces/Tao_Financial_Engine/backups/runtime/phase-c-prod-deploy-cycle-20260316T041214Z/live-authority.noninteractive.stderr.txt`

Exact fault:

- ECS returned `InvalidParameterException: Interactive is the only mode supported currently.`

Impact:

- first attempted recovery path for clean capture was invalid for this environment

#### Final recovery that worked

Evidence:

- `/workspaces/Tao_Financial_Engine/backups/runtime/phase-c-prod-deploy-cycle-20260316T041214Z/live-authority.marked.stdout.txt`

Working method:

- marked/compressed payload framing
- explicit extraction after session wrapper noise

### Classification rule for this family

This family is:

- proof-harness/evidence-capture failure

It is not:

- publication-bundle contract failure
- live cutover authority failure
- live investor-serving failure

### Never-again rules from this family

1. Never freeze a live blocker from parsed response fields until the raw response body is checked directly.
2. Never run live proof SQL without verifying the selected columns exist on the current live schema.
3. Never assume `ecs execute-command` gives clean machine JSON when interactive mode is required.
4. Never classify proof-harness breakage as publication-path failure.
5. Never let a long evidence-salvage loop pretend to be fresh system diagnosis.

## Residual Debt After Accepted Phase C Proof

Residual debt now includes:

- legacy proof-harness/evidence-capture instability in live ECS probing
- `runtime_decisions_latest` remains non-authoritative metadata for this path and may still point to older runs
- legacy auxiliary verifier logic can still fail on outdated assumptions

These are not Phase C closure contradictions.

## Current Recommended Next Action

Recommended next action:

- write a post-Phase-C transition decision artifact before any new live work

Not recommended:

- another Phase C deploy-proof cycle
- reopening Step 1
- widening proof-harness failures into fake publication-core regressions

## Corpus Rule

Any future command after this point must use:

- `/workspaces/Tao_Financial_Engine/corpora/production_shell_control_corpus_v2.md`

as the current gate-state control surface, not v1.
