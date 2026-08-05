# Production Shell Control Corpus v5

Generated: 2026-03-16 UTC
Status: current control surface after accepted Phase D local hotfix-lane integration proof and accepted workspace-integrity blocker closure
Supersedes for current gate-state use:
- `/workspaces/Tao_Financial_Engine/corpora/production_shell_control_corpus_v4.md`

## Purpose

This file is the current control surface for Production Shell gate state after:

- accepted Step 1 closure
- accepted Phase C live deploy-proof
- accepted Phase D workstream start
- accepted Phase D slice-1 contract
- accepted Phase D local hotfix-lane integration proof
- accepted Phase D workspace-integrity blocker closure

It records only:

- current exact gate truth
- current accepted authority truth
- current residual failure family status
- current active workstream
- current exact next step

## Scope

This corpus covers only:

- accepted Step 1 cutover closure as inherited truth
- accepted Phase C canonical publication-bundle live proof as inherited truth
- accepted Phase D release-gate-class behavior change in local proof
- accepted closure of the exact `deploy_workspace_integrity` blocker for the Phase D real-shell proof

It does not cover:

- DSF-AI core
- later master-plan phases beyond Phase D
- any accepted live Phase D deploy proof, because that does not exist yet

## Current Gate State

Accepted inherited live proof anchor:

- `/workspaces/Tao_Financial_Engine/backups/runtime/phase-c-prod-deploy-proof-20260316T041214Z.json`

Accepted Phase D start anchor:

- `/workspaces/Tao_Financial_Engine/backups/runtime/phase-d-workstream-start-20260316T045704Z.md`

Accepted Phase D slice-1 contract anchor:

- `/workspaces/Tao_Financial_Engine/backups/runtime/phase-d-slice1-release-gate-classes-contract-20260316T050238Z.md`

Accepted Phase D local integration proof:

- `/workspaces/Tao_Financial_Engine/backups/runtime/phase-d-hotfix-lane-integration-proof-20260316T052323Z.json`

Accepted Phase D workspace-integrity blocker closure proof:

- `/workspaces/Tao_Financial_Engine/backups/runtime/phase-d-deploy-workspace-integrity-closure-proof-20260316T053805Z.json`

The strict current truth is:

- Step 1 remains closed within its accepted narrow scope
- Phase C remains closed within its accepted narrow scope
- Phase D remains the active workstream
- the local Phase D behavior change is real: default hotfix-lane blocking now comes from release gate classes instead of promoting changed non-blocking gates into blockers
- the exact `deploy_workspace_integrity` blocker for:
  - `tools/validation_state_contract.py`
  - `web/scripts/run_validation_gate_v1.mjs`
  - `web/src/lib/release-gate-classes.ts`
  is closed
- there is still no accepted real-shell proof-only artifact for the Phase D hotfix lane

## Current Authority Truth

Inherited accepted publication authority truth remains:

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

## Current Phase D Deploy Authority Truth

Under the accepted local Phase D hotfix-lane behavior:

- `runtime_critical`
  - blocking by default
- `publication_consistency`
  - blocking by default
- `non_critical_observability`
  - record-only by default
- `non_critical_product_parity`
  - record-only by default

This means:

- a changed non-critical gate is not allowed to become a default blocker only because it changed
- the default hotfix lane must stop only on blocking gate classes unless an explicit override exists

## Residual Failure Families

Residual failure family 1:

- `phase_c_live_proof_harness_drift`

Status:

- residual process debt

Residual failure family 2:

- `meta_artifact_loop_drift`

Status:

- active process warning

Exact meaning:

- do not create new transition, corpus, contract, or handoff artifacts as a substitute for the next exact behavior-changing or blocker-closing step

Neither residual family reopens Step 1 or Phase C.

## Active Workstream

The active workstream is:

- `Phase D: Separate Product Deployment From Data Publication`

## Exact Next Step

The next exact step is:

- rerun the real proof-only deploy-shell hotfix-lane proof now that `deploy_workspace_integrity` is closed

The next exact unresolved question is:

- whether the real shell now shows the same hotfix-lane behavior that the accepted local integration proof already showed

## Not Allowed From This State

Not allowed from this state:

- reopening Step 1 without a new exact in-scope contradiction
- reopening Phase C without a new exact in-scope contradiction
- creating another corpus refresh instead of rerunning the real shell proof
- widening one exact blocker into a larger artifact loop
- treating changed `non_critical_observability` or `non_critical_product_parity` gates as default blockers in the hotfix lane

## Recommended Next Action

Recommended next action:

- rerun the real proof-only deploy-shell hotfix-lane proof and, if it blocks, fix that one exact blocker directly

## Corpus Rule

Any future command after this point must use:

- `/workspaces/Tao_Financial_Engine/corpora/production_shell_control_corpus_v5.md`

as the current gate-state control surface, not v4.
