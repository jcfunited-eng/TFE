# Production Shell Control Corpus v1

## Purpose

This file is the executable control model for the rebuilt `Production Shell` path.

It is not a summary.
It is not a pitch.
It is not allowed to be vague.

Its job is to state, in one place:

- where inputs come from
- how each code block processes them
- what exact outputs it writes
- which store is authoritative
- which store is mirror-only
- which rule checks must pass
- which gate is currently open

If this file drifts from reality, it stops being useful.

## Scope

This corpus covers only:

- rebuilt Step 1 cutover path
- Phase C canonical publication bundle path
- validation and deploy gates that touch those paths

It does not cover:

- DSF-AI core
- recommendation science
- data-vendor work
- later rearchitecture phases beyond current Phase C gate control

## Current Gate State

As of `2026-03-16T02:56:56Z`:

- Step 1 remains closed within its accepted narrow scope.
- Phase C local runtime proof is closed:
  `/workspaces/Tao_Financial_Engine/backups/runtime/phase-c-runtime-proof-repair-rerun-20260316T021824Z.json`
- The predeploy validator mismatch is now closed:
  `/workspaces/Tao_Financial_Engine/backups/runtime/runtime-validation-gate-repair-proof-20260316T025538Z.json`
- The exact next allowed gate is:
  one controlled Phase C production deploy-proof cycle

## Authority Model

### Authoritative stores

For cutover / canonical publication bundle paths:

- `active_publication_pointer`
  - authoritative for active publication truth
- `publication_bundles`
  - authoritative for immutable publication bundle identity and linkage
- `assessment_reports`
  - authoritative for validity prerequisite truth

### Mirror / non-authoritative stores

- `runtime_refresh_runs`
  - mirror/operator-summary only
- `runtime_decisions_latest`
  - metadata only for this path

### Forbidden validity authority on cutover paths

These must not be treated as authoritative for cutover validity:

- `runtime_refresh_runs.validation_status`
- `runtime_refresh_runs.snapshot_publication_id`
- `runtime_refresh_runs.quote_publication_id`
- `runtime_refresh_runs.quote_binding_status`
- `runtime_refresh_runs.is_active_publication`
- `runtime_refresh_runs.optimizer_target_met`
- `runtime_refresh_runs.epoch_library_status`
- `runtime_refresh_runs.epoch_library_confidence_schema`

## Data Store Contracts

### `runtime_refresh_runs`

Purpose:
- operator summary row for the run

Key:
- `run_id: string`

Important fields:
- `mode: string`
- `trigger_source: string`
- `requested_by: string`
- `started_at: timestamp`
- `completed_at: timestamp | null`
- `report_status: string`
- `current_phase: string`
- `current_phase_process_status: string`
- `activation_state: string | null`
- `serving_state: string | null`
- `failure_code: string | null`
- `failure_detail: string | null`

Authority rule:
- mirror only

### `runtime_refresh_run_phases`

Purpose:
- exact per-phase execution ledger

Key:
- `(run_id, phase_name)`

Important fields:
- `input_contract: json | null`
- `process_status: string`
- `started_at: timestamp | null`
- `completed_at: timestamp | null`
- `output_contract: json | null`
- `failure_code: string | null`
- `failure_detail: string | null`

Authority rule:
- authoritative for phase ledger truth

### `candidate_bundles`

Purpose:
- persisted candidate bundle identity and manifest linkage

Key:
- `run_id: string`

Important fields:
- `candidate_bundle_id: string`
- `normalized_package_id: string`
- `policy_set_id: string`
- `model_set_id: string`
- `config_set_id: string`
- `bundle_class: string`
- `requested_run_mode: string`
- `target_environment: string`
- `deterministic_build_timestamp_utc: timestamp`
- `manifest_path: string`
- `manifest_digest_sha256: string`

Authority rule:
- authoritative for candidate identity only

### `assessment_reports`

Purpose:
- persisted validity decision

Key:
- `run_id: string`

Important fields:
- `assessment_report_id: string`
- `candidate_bundle_id: string`
- `assessment_rule_set_id: string`
- `disposition: "pass" | "fail"`
- `publication_allowed: boolean`
- `blocking_reason_codes: json`
- `blocking_reason_details: json`
- `report_path: string`

Authority rule:
- authoritative for validity decision

Important constraint:
- same `assessment_report_id` can recur across runs
- therefore same-run matching must use `(run_id, assessment_report_id)`, not `assessment_report_id` alone

### `publication_bundles`

Purpose:
- immutable canonical published object

Key:
- `publication_bundle_id: string`

Important fields:
- `run_id: string`
- `candidate_bundle_id: string`
- `assessment_report_id: string`
- `normalized_package_id: string`
- `policy_set_id: string`
- `model_set_id: string`
- `config_set_id: string`
- `bundle_class: string`
- `target_environment: string`
- `previous_active_publication_id: string | null`
- `activation_audit_id: string`
- `manifest_path: string`
- `manifest_digest_sha256: string`

Authority rule:
- authoritative for published bundle identity and prerequisite linkage

### `active_publication_pointer`

Purpose:
- active publication pointer per environment

Key:
- `target_environment: string`

Important fields:
- `publication_bundle_id: string`
- `run_id: string`
- `created_at: timestamp`
- `updated_at: timestamp`

Authority rule:
- authoritative for active publication truth

### `publication_activation_audit`

Purpose:
- immutable audit of active pointer movement

Key:
- `activation_audit_id: string`

Important fields:
- `target_environment: string`
- `run_id: string`
- `publication_bundle_id: string`
- `previous_active_publication_id: string | null`
- `new_active_publication_id: string`
- `assessment_report_id: string`

Authority rule:
- authoritative audit trail only

### `deferred_followup_jobs`

Purpose:
- durable non-critical follow-up handoff

Key:
- `followup_job_id: string`

Important fields:
- `run_id: string`
- `publication_bundle_id: string`
- `phase_name: "quote_cache_refresh"`
- `classification: "non_critical_follow_up"`
- `status: "deferred" | "launched" | "failed"`
- `publication_manifest_path: string`
- `ticket_path: string`

Authority rule:
- authoritative for follow-up ticket truth only

## Object Contracts

## 1. Entry Path

Code:
- `/workspaces/Tao_Financial_Engine/web/src/app/api/admin/refresh/route.ts`

Input source:
- HTTP `POST /api/admin/refresh`
- request JSON body
- cutover env:
  - `TFE_STEP1_CUTOVER_MODE`
  - `TFE_STEP1_CUTOVER_REQUEST_CONTRACT_JSON`

Accepted input shape for cutover snapshot path:
- `mode: "snapshot"`
- optional explicit Step 1 contract fields in request body or env contract:
  - `normalizedPackageId: string`
  - `policySetId: string`
  - `modelSetId: string`
  - `configSetId: string`
  - `bundleClass: string`
  - `dependencyClassificationRegister: object`
  - `targetEnvironment: string`
  - `assessmentRuleSetId: string`

Process rules:
- if cutover enabled and mode=`snapshot`, dispatch new Step 1 path
- do not spawn legacy Python runner for that path
- if cutover disabled, legacy path may still handle snapshot

Output:
- JSON response including:
  - `dispatchPath`
  - `legacyRunnerDispatched`
  - `result.runId`
  - `result.publicationBundleId`
  - `result.followupStatus`

Failure output:
- HTTP error response with explicit message

## 2. Step 1 Orchestrator

Code:
- `/workspaces/Tao_Financial_Engine/web/src/lib/step1/orchestrator.ts`

Input type:
- `Step1OrchestratorInput`

Required fields:
- `normalizedPackageId: string`
- `policySetId: string`
- `modelSetId: string`
- `configSetId: string`
- `bundleClass: string`
- `dependencyClassificationRegister: object`
- `targetEnvironment: string`
- `requestedBy: string`
- `assessmentRuleSetId: string`

Optional fields:
- `runId?: string`
- `requestedAtUtc?: ISO timestamp`
- `followupDesiredStatus?: "deferred" | "launched"`
- `mode?: string`
- `triggerSource?: string`

Process:
- resolve persistence kind:
  - readonly proof store
  - or Postgres
- call in exact order:
  1. `createStep1RunRequest`
  2. `createCandidateBundleRecord`
  3. `createAssessmentReportRecord`
  4. `createPublicationCommitRecord`
  5. `createQuoteCacheFollowupTicket`
  6. write success mirror run row

Output type:
- `Step1OrchestratorResult`

Important outputs:
- `runId: string`
- `requestArtifactPath: string`
- `candidateBundleManifestPath: string`
- `candidateBundleId: string`
- `assessmentReportPath: string`
- `assessmentReportId: string`
- `publicationManifestPath: string`
- `publicationBundleId: string`
- `followupTicketPath: string`
- `followupJobId: string`
- `followupStatus: "deferred" | "launched" | "failed"`

Failure rule:
- fail immediately on first object failure

## 3. Run Request

Code:
- `/workspaces/Tao_Financial_Engine/web/src/lib/step1/run-request.ts`

Input type:
- `Step1RunRequestInput`

Processing rules:
- `run_id` must be non-empty string
- all package/model/config ids must be non-empty strings
- `requested_at_utc` must parse as ISO timestamp
- `dependency_classification_register` must be a non-empty object with classified entries

Writes:
- artifact:
  - `artifacts/runs/<run_id>/step1/request.json`
- row:
  - `runtime_refresh_runs`
- phase row:
  - `runtime_refresh_run_phases` for `candidate_build`

Output:
- `Step1RunRequestResult`

Failure codes:
- `request_invalid`
- `dependency_classification_missing`
- `request_state_persistence_failure`

## 4. Candidate Bundle

Code:
- `/workspaces/Tao_Financial_Engine/web/src/lib/step1/candidate-bundle.ts`

Input type:
- `CandidateBundleRecordInput`

Input source:
- request artifact file

Processing rules:
- request artifact must parse as `Step1RunRequestRecord`
- request artifact `run_id` must match input `run_id`
- candidate identity is deterministic from:
  - `normalized_package_id`
  - `policy_set_id`
  - `model_set_id`
  - `config_set_id`
  - `bundle_class`
  - `requested_run_mode`
  - `target_environment`
  - `dependency_classification_register`
- `candidate_bundle_id` is derived from SHA256 digest
- deterministic build timestamp is derived from digest

Writes:
- artifact:
  - `artifacts/runs/<run_id>/step1/candidate_bundle/manifest.json`
- row:
  - `candidate_bundles`
- phase row:
  - `runtime_refresh_run_phases` for `candidate_build=completed`

Output:
- manifest
- manifest digest
- candidate bundle row
- completed phase row

Failure codes:
- `candidate_input_missing`
- `candidate_build_failure`
- `candidate_manifest_invalid`
- `state_persistence_failure`

## 5. Assessment Report

Code:
- `/workspaces/Tao_Financial_Engine/web/src/lib/step1/assessment-report.ts`

Input type:
- `AssessmentReportRecordInput`

Input source:
- candidate bundle manifest
- `assessmentRuleSetId`
- optional `forcedFailures[]`

Processing rules:
- candidate manifest must parse
- report identity is deterministic from:
  - `candidate_bundle_id`
  - `assessment_rule_set_id`
  - `disposition`
  - `blocking_reason_details`
- `assessment_report_id` is derived from SHA256 digest
- `publication_allowed = true` only when disposition=`pass`
- failure code escalates to `critical_dependency_unsatisfied` if any blocking reason is marked `publication_critical`

Writes:
- artifact:
  - `artifacts/runs/<run_id>/step1/assessment_report.json`
- row:
  - `assessment_reports`
- phase row:
  - `runtime_refresh_run_phases` for `assessment_gate`

Output:
- report artifact
- report row
- phase row

Failure codes:
- `assessment_input_missing`
- `assessment_rule_failure`
- `critical_dependency_unsatisfied`
- `assessment_state_persistence_failure`

## 6. Publication Commit

Code:
- `/workspaces/Tao_Financial_Engine/web/src/lib/step1/publication-commit.ts`

Input type:
- `PublicationCommitRecordInput`

Input source:
- assessment report artifact
- candidate bundle manifest path from assessment evidence
- prior active pointer

Processing rules:
- assessment report must parse
- publication may proceed only if:
  - `disposition = pass`
  - `publication_allowed = true`
- candidate bundle manifest evidence must exist
- canonical publication bundle manifest is built through `publication-bundle-contract.ts`
- publication commit must write one transaction containing:
  - `publication_bundles` row
  - `active_publication_pointer` row
  - `publication_activation_audit` row
  - `publication_commit` phase row

Writes:
- artifact:
  - `artifacts/publications/<publication_bundle_id>/manifest.json`
- rows:
  - `publication_bundles`
  - `active_publication_pointer`
  - `publication_activation_audit`
- phase row:
  - `runtime_refresh_run_phases` for `publication_commit`

Output:
- manifest
- manifest digest
- publication bundle row
- pointer row
- activation audit row
- phase row

Failure codes:
- `assessment_not_pass`
- `publication_bundle_write_failure`
- `activation_pointer_write_failure`
- `activation_audit_write_failure`
- `state_persistence_failure`

## 7. Canonical Publication Bundle Contract Layer

Code:
- `/workspaces/Tao_Financial_Engine/web/src/lib/publication-bundle-contract.ts`

Input sources:
- pointer row
- bundle row
- assessment row
- persisted manifest bytes

Processing rules:
- manifest identity is derived from:
  - `run_id`
  - `candidate_bundle_id`
  - `assessment_report_id`
  - `target_environment`
- activation audit identity is derived from:
  - `run_id`
  - `candidate_bundle_id`
  - `assessment_report_id`
  - `target_environment`
  - `previous_active_publication_id`
- read-side prerequisite check must match:
  - `assessment_reports.run_id = publication_bundles.run_id`
  - `assessment_reports.assessment_report_id = publication_bundles.assessment_report_id`
- candidate is valid only if:
  - `assessment.disposition = pass`
  - `assessment.publication_allowed = true`

Output type:
- `PublicationBundleContractResolution`

Important outputs:
- `publicationBundleId`
- `assessmentReportId`
- `candidateValid: boolean`
- `blockingReasonCode`
- `blockingReasonDetail`
- `manifestDigestSha256`

Failure codes:
- `RUNTIME_SOURCE_NOT_POSTGRES`
- `POSTGRES_NOT_CONFIGURED`
- `ACTIVE_POINTER_MISSING`
- `ACTIVE_POINTER_INVALID`

## 8. Publication State Reader

Code:
- `/workspaces/Tao_Financial_Engine/web/src/lib/publication-state.ts`

Input sources:
- canonical publication bundle contract resolution
- runtime snapshot context
- runtime quote context
- mirror/operator-summary metadata

Processing rules:
- under cutover, call canonical contract resolution
- derive:
  - `validationStatus`
  - `activationState`
  - `servingState`
- active publication validity must come from:
  - pointer
  - bundle
  - same-run assessment
- not from legacy run-header validity fields

Output type:
- `CanonicalPublicationState`

Important outputs:
- `snapshotPublicationId`
- `quotePublicationId`
- `quoteBindingStatus`
- `validationStatus`
- `activationState`
- `servingState`
- `blockingReasonCode`
- `blockingReasonDetail`

## 9. Investor Serving Bundle Reader

Code:
- `/workspaces/Tao_Financial_Engine/web/src/lib/runtime-publication-bundle.ts`

Input sources:
- canonical publication bundle contract resolution
- optional runtime metadata

Processing rules:
- investor-serving bundle resolution must return the active pointed `publication_bundle_id`
- if canonical contract is invalid, serving bundle meta must block and record failures

Output types:
- `InvestorActivePublicationBundleResolution`
- `RuntimeServingPublicationBundleMeta`

Important outputs:
- `publicationBundleId`
- `runId`
- `validationStatus`
- `sourcePath`
- `fallbackApplied`
- `fallbackReason`

## 10. Follow-Up Ticket

Code:
- `/workspaces/Tao_Financial_Engine/web/src/lib/step1/followup-ticket.ts`

Input type:
- `QuoteCacheFollowupTicketInput`

Input source:
- publication manifest artifact
- active pointer read

Processing rules:
- classification must be exactly `non_critical_follow_up`
- active pointer must exist for target environment
- active pointer `publication_bundle_id` must match manifest `publication_bundle_id`
- follow-up identity is derived from:
  - `run_id`
  - `publication_bundle_id`
  - `phase_name`
  - `classification`
- publication remains active even if follow-up fails

Writes:
- artifact:
  - `artifacts/runs/<run_id>/step1/followup_ticket.json`
- row:
  - `deferred_followup_jobs`
- phase row:
  - `runtime_refresh_run_phases` for `quote_cache_refresh`

Output:
- ticket artifact
- deferred followup row
- quote_cache_refresh phase row

Failure codes:
- `followup_ticket_write_failure`
- `followup_launch_failure`
- `followup_classification_violation`
- `state_persistence_failure`

## 11. Mirror Run Finalization

Code:
- `/workspaces/Tao_Financial_Engine/web/src/lib/step1/schema.ts`
  via `createStep1SuccessMirrorRunRow`

Processing rules:
- success mirror row summarizes:
  - `report_status="ok"`
  - `activation_state="activated"`
  - `serving_state="allowed"`
  - current phase and follow-up status
- mirror row does not regain cutover validity authority

Important non-authoritative fields on accepted cutover path:
- `validation_status`
- `snapshot_publication_id`
- `quote_publication_id`
- `quote_binding_status`
- `is_active_publication`

These may remain unset or non-authoritative without breaking cutover truth.

## 12. Runtime Validation Gate

Code:
- `/workspaces/Tao_Financial_Engine/web/scripts/run_validation_gate_v1.mjs`
- `/workspaces/Tao_Financial_Engine/tools/run_validation_gate_v1_in_ecs_network.py`

Input sources:
- live runtime tables
- live cutover env
- optional requested run id

Processing rules:
- non-cutover path may still use legacy oracle model
- cutover path must validate from:
  - `active_publication_pointer`
  - `publication_bundles`
  - `assessment_reports`
- cutover validator must not fail only because legacy run-header validity fields are null

Output:
- validation report artifact with:
  - `status`
  - `checks[]`
  - `blocking_reason`

Current known repaired rule:
- `oracle_integrity` now passes for accepted live cutover run `3301a40c-a59a-4839-87fd-c936da6017c2`
  under task definition `234`

## Data Flow Diagram

```text
request body / env contract
  -> route.ts
    -> orchestrator.ts
      -> request.json + runtime_refresh_runs + candidate_build phase row
      -> candidate_bundle manifest + candidate_bundles row
      -> assessment_report.json + assessment_reports row + assessment_gate phase row
      -> publication manifest + publication_bundles row + active_publication_pointer row + publication_activation_audit row + publication_commit phase row
      -> followup_ticket.json + deferred_followup_jobs row + quote_cache_refresh phase row
      -> success mirror runtime_refresh_runs update

read side
  -> publication-state.ts
    -> publication-bundle-contract.ts
      -> active_publication_pointer
      -> publication_bundles
      -> same-run assessment_reports

investor side
  -> runtime-publication-bundle.ts
    -> publication-bundle-contract.ts
      -> same publication_bundle_id

predeploy validation
  -> run_validation_gate_v1.mjs
    -> same accepted cutover authority model
```

## Logic Flow Diagram

```text
snapshot request
  -> request contract valid?
    -> no: reject, no publication work started
    -> yes
      -> write request state
      -> build deterministic candidate bundle
      -> assess candidate
      -> assessment pass?
        -> no: publication blocked
        -> yes
          -> commit publication bundle + active pointer + activation audit
          -> create deferred follow-up ticket
          -> mirror operator-summary row

read path
  -> pointer exists?
    -> no: pointer missing
    -> yes
      -> bundle exists?
        -> no: pointer invalid
        -> yes
          -> same-run assessment exists?
            -> no: pointer invalid
            -> yes
              -> disposition=pass and publication_allowed=true?
                -> yes: activation allowed / serving allowed
                -> no: serving blocked

deploy path
  -> local proof
  -> local runtime proof
  -> predeploy runtime_validation
  -> only then ECS handoff
```

## Validation Checks And Balances Control

### Rule checks by boundary

#### Request boundary
- non-empty strings required
- ISO timestamp required
- dependency classification object required

#### Candidate boundary
- request artifact must parse
- `run_id` must match
- deterministic identity inputs must be complete

#### Assessment boundary
- candidate manifest must parse
- forced failure entries must include `reasonCode` and `reasonDetail`
- publication allowed only when `disposition=pass`

#### Publication commit boundary
- assessment must pass
- evidence path to candidate manifest must exist
- pointer write, bundle write, and audit write must succeed together

#### Contract read boundary
- pointer must resolve one bundle
- bundle must resolve the same-run assessment row
- same-run assessment must be `pass` and `publication_allowed=true`

#### Validator boundary
- cutover validation must use cutover authorities
- legacy oracle checks must not block accepted cutover path

## Test And Emulation Model

Required order:

1. readonly artifact proof
2. local production-mode server
3. writable local Postgres
4. real `POST /api/admin/refresh` snapshot path
5. authority probe against local Postgres truth
6. live runtime_validation against current ECS revision
7. controlled production deploy-proof cycle

Frozen evidence required per gate:

- exact source state
- touched file hashes
- request payload
- env file
- server startup evidence
- authority probe output
- validator output
- deploy evidence folder

## Failure Registry

### Phase C Failure 1

Artifact:
- `/workspaces/Tao_Financial_Engine/backups/runtime/phase-c-runtime-proof-20260316T014959Z.json`

Exact blocker:
- contract validation failed because assessment prerequisite lookup could bind the wrong run

Root cause:
- `publication-bundle-contract.ts` joined `assessment_reports` on `assessment_report_id` only

Repair proof:
- `/workspaces/Tao_Financial_Engine/backups/runtime/phase-c-runtime-proof-repair-rerun-20260316T021824Z.json`

### Phase C Failure 2

Artifact:
- `/workspaces/Tao_Financial_Engine/backups/runtime/phase-c-prod-deploy-blocker-20260316T023356Z.json`

Exact blocker:
- predeploy `runtime_validation` failed on accepted cutover live run

Root cause:
- validator still enforced legacy oracle assumptions

Repair proof:
- `/workspaces/Tao_Financial_Engine/backups/runtime/runtime-validation-gate-repair-proof-20260316T025538Z.json`

## Current Exact Next Gate

The next allowed move is:

- one controlled Phase C production deploy-proof cycle

The next allowed move is not:

- another validator-only rerun
- another local proof that does not move a gate
- any move that reintroduces legacy `runtime_refresh_runs` validity authority

## Corpus Rule

Any future command in this workstream must:

- cite this corpus
- move one exact gate only
- name the exact authority stores it depends on
- name the exact non-authority stores it forbids
- stop at one exact blocker if that gate fails
