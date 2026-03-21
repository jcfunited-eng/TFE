# Production Shell Control Corpus v3

Generated: 2026-03-16 UTC
Status: current control surface after accepted Phase D start
Supersedes for current gate-state use:
- `/workspaces/Tao_Financial_Engine/corpora/production_shell_control_corpus_v2.md`

## Purpose

This file is the current evaluator control surface for Production Shell gate state after:

- accepted Phase C live deploy-proof
- accepted post-Phase-C transition decision
- accepted Phase D workstream start

It records only:

- current exact gate truth
- current accepted authority truth
- current exact residual failure family
- current active workstream
- current next allowed item

## Scope

This corpus covers only:

- accepted Step 1 cutover closure as inherited truth
- accepted Phase C canonical publication-bundle live proof as inherited truth
- accepted Phase D workstream start
- the residual proof-harness failure family from the accepted Phase C cycle

It does not cover:

- DSF-AI core
- later Phase D implementation beyond the next allowed item
- later master-plan phases beyond Phase D

## Current Gate State

Accepted inherited live proof anchor:

- `/workspaces/Tao_Financial_Engine/backups/runtime/phase-c-prod-deploy-proof-20260316T041214Z.json`

Accepted transition anchor:

- `/workspaces/Tao_Financial_Engine/backups/runtime/post-phase-c-transition-decision-20260316T044658Z.md`

Accepted Phase D start anchor:

- `/workspaces/Tao_Financial_Engine/backups/runtime/phase-d-workstream-start-20260316T045704Z.md`

The strict current truth is:

- Step 1 remains closed within its accepted narrow scope
- Phase C remains closed within its accepted narrow scope
- Phase D is now the active workstream
- the accepted Phase D start artifact is `/workspaces/Tao_Financial_Engine/backups/runtime/phase-d-workstream-start-20260316T045704Z.md`

## Current Authority Truth

Inherited accepted authority truth remains:

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

- `runtime_refresh_runs.validation_status`
- `runtime_refresh_runs.snapshot_publication_id`
- `runtime_refresh_runs.quote_publication_id`
- `runtime_refresh_runs.quote_binding_status`
- `runtime_refresh_runs.is_active_publication`

## Residual Failure Family

Residual failure family:

- `phase_c_live_proof_harness_drift`

Status:

- residual process debt

It does not reopen Step 1.
It does not reopen Phase C.
It does not block Phase D start.

## Active Workstream

The active workstream is:

- `Phase D: Separate Product Deployment From Data Publication`

## Next Allowed Item

The next allowed item is:

- the Phase D slice-1 contract artifact for `release gate classes`

## Not Allowed From This State

Not allowed from this state:

- reopening Step 1 without a new exact in-scope contradiction
- reopening Phase C without a new exact in-scope contradiction
- rerunning the Phase C deploy-proof cycle as if it were still the current gate

## Recommended Next Action

Recommended next action:

- write the Phase D slice-1 contract artifact for `release gate classes`

## Corpus Rule

Any future command after this point must use:

- `/workspaces/Tao_Financial_Engine/corpora/production_shell_control_corpus_v3.md`

as the current gate-state control surface, not v2.
