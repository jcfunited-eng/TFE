# Production Shell System Reference v2

Generated: 2026-03-16 UTC
Status: broader control-surface reference
Purpose: provide one evidence-backed reference for rebuild work, cross-chat continuity, and future reconstruction.

## 1. Scope And Current Gate State

This file covers the missing layers that were too thin in `production_shell_control_corpus_v1.md`:

- system layer model
- security layers
- failure mode analysis
- admin console elements
- user-facing layers
- Finviz filter and parity surfaces
- persistence and refresh contracts
- L0-L5 and governance boundaries
- epoch and quote-publication contracts
- repo control corpus and contract-document map
- traced "life in the day" model inputs

Current strict state:

- Step 1 remains closed in narrow scope under the rebuilt Production Shell cutover path.
- Phase C local runtime proof is accepted.
- The Phase C predeploy `runtime_validation` oracle mismatch is repaired and the gate passed on live task definition `234`.
- No accepted Phase C production deploy-proof cycle exists yet.
- The next allowed gate is one controlled Phase C production deploy-proof cycle.

Proof anchors for the current state:

- `/workspaces/Tao_Financial_Engine/backups/runtime/step1-prod-deploy-proof-20260316T004020Z.json`
- `/workspaces/Tao_Financial_Engine/backups/runtime/phase-c-runtime-proof-repair-rerun-20260316T021824Z.json`
- `/workspaces/Tao_Financial_Engine/backups/runtime/runtime-validation-gate-repair-proof-20260316T025538Z.json`

## 2. System Layer Diagram

```
LAYER 0  Security and access control
  Inputs:
    browser credentials, session cookie, MFA code, DB/env secrets
  Process:
    sign-in, session issue/read, role guard, admin guard
  Outputs:
    authenticated user, admin authorization, redirect or deny

LAYER 1  User-facing web surfaces
  Inputs:
    authenticated requests from account, screener, recommendations, watchlist, portfolio, advisor pages
  Process:
    route load, active publication read, published decision read, screener filter application
  Outputs:
    deterministic user-facing pages and API payloads

LAYER 2  Admin web surfaces
  Inputs:
    authenticated admin requests
  Process:
    refresh request, status polling, log/history read, system-status read, quality views
  Outputs:
    operational control and visibility

LAYER 3  Publication middle office
  Inputs:
    snapshot POST request plus explicit Step 1 cutover request contract
  Process:
    run request, candidate bundle, assessment report, publication commit, followup ticket
  Outputs:
    publication_bundle, active_publication_pointer, assessment_report, phase ledger, followup ticket

LAYER 4  Enrichment and non-critical follow-up
  Inputs:
    active pointer-owned publication identity, quote-cache followup ticket, parity probe configs
  Process:
    quote cache refresh, profile overrides, Finviz overlay build, parity probes, analytics
  Outputs:
    non-critical artifacts and admin diagnostics

LAYER 5  Serving persistence and runtime data
  Inputs:
    publication tables, runtime decisions, runtime symbols, snapshot rows, quote rows
  Process:
    postgres reads, publication resolution, decision/provenance reads
  Outputs:
    current serving bundle, runtime rows for UI/API surfaces

LAYER 6  Governance and validation
  Inputs:
    publication state, assessment reports, governance contracts, admin rulebook, validator config
  Process:
    oracle_integrity, runtime_validation, governance coverage checks, provenance parity checks
  Outputs:
    pass/fail gates, contract violations, residual debt records

LAYER 7  Research and model semantics
  Inputs:
    UF engine structural outputs, L0-L4 ladder semantics, optional legacy L5 learning lane, epoch/quote contracts
  Process:
    structural classification, policy scoring, future family gating, admin-only governance analysis
  Outputs:
    decision provenance, family-coverage contracts, future expansion constraints
```

## 3. Security Layers

### 3.1 Auth Entry And Session Contract

Primary sign-in entry:

- code path: `/workspaces/Tao_Financial_Engine/web/src/app/api/auth/sign-in/route.ts`
- request input type:
  - `username: string`
  - `password: string`
  - `mfaCode: string`
  - `next: string`
- accepted content types:
  - `application/json`
  - form post
- success output:
  - JSON or redirect
  - signed session cookie `tfe_session`

Session contract:

- code path: `/workspaces/Tao_Financial_Engine/web/src/lib/auth-session.ts`
- cookie name: `tfe_session`
- payload type:
  - `v: number`
  - `username: string`
  - `iat: number`
  - `exp: number`
- integrity:
  - HMAC SHA-256 over base64url payload
- secret sources:
  - preferred: `TFE_SESSION_SECRET`
  - fallback: local secret file `tfe_session_secret.bin`

Residual security risk already documented in repo:

- file: `/workspaces/Tao_Financial_Engine/auth_triage_latest.md`
- issue: no shared `TFE_SESSION_SECRET` in ECS can break sessions across overlapping tasks or scale-out

### 3.2 Server Guard Layer

Code path:

- `/workspaces/Tao_Financial_Engine/web/src/lib/server-auth.ts`

Control rules:

- `requireServerUser(path)` redirects unauthenticated requests to `/sign-in?next=...`
- `requireServerAdminUser(path)` allows only admin role, else redirects to `/account?error=admin_required`

### 3.3 Admin Route Security

Admin pages guarded by `requireServerAdminUser`:

- `/workspaces/Tao_Financial_Engine/web/src/app/admin-console/page.tsx`
- `/workspaces/Tao_Financial_Engine/web/src/app/admin-console/refresh-log/page.tsx`

User pages guarded by `requireServerUser`:

- `/workspaces/Tao_Financial_Engine/web/src/app/account/page.tsx`
- `/workspaces/Tao_Financial_Engine/web/src/app/screener/page.tsx`
- `/workspaces/Tao_Financial_Engine/web/src/app/recommendations/page.tsx`

## 4. User Layers And Admin Console Elements

### 4.1 User-Facing Layer

Primary user surfaces:

- `/workspaces/Tao_Financial_Engine/web/src/app/account/page.tsx`
- `/workspaces/Tao_Financial_Engine/web/src/app/screener/page.tsx`
- `/workspaces/Tao_Financial_Engine/web/src/app/recommendations/page.tsx`
- `/workspaces/Tao_Financial_Engine/web/src/app/watchlist/page.tsx`
- `/workspaces/Tao_Financial_Engine/web/src/app/portfolio/page.tsx`
- `/workspaces/Tao_Financial_Engine/web/src/app/portfolio-advisor/page.tsx`
- `/workspaces/Tao_Financial_Engine/web/src/app/help/page.tsx`
- `/workspaces/Tao_Financial_Engine/web/src/app/support/page.tsx`

Primary user APIs:

- `/workspaces/Tao_Financial_Engine/web/src/app/api/screener/route.ts`
- `/workspaces/Tao_Financial_Engine/web/src/app/api/recommendations/list/route.ts`
- `/workspaces/Tao_Financial_Engine/web/src/app/api/watchlist/route.ts`
- `/workspaces/Tao_Financial_Engine/web/src/app/api/portfolio/route.ts`

User-serving authority rule:

- active truth must resolve from `active_publication_pointer`
- validity truth must resolve from `publication_bundles` plus `assessment_reports`
- legacy `runtime_refresh_runs` validity fields remain mirror/operator-summary only

### 4.2 Admin Console Layer

Primary admin surfaces:

- `/workspaces/Tao_Financial_Engine/web/src/components/AdminConsoleClient.tsx`
- `/workspaces/Tao_Financial_Engine/web/src/components/AdminRefreshLogsClient.tsx`

Documented admin control elements in code:

- `Snapshot Refresh`
- `Universe + Snapshot`
- `Poll Now`
- refresh lifecycle panel
- refresh log tail
- refresh history report
- system status
- recommendation quality status
- UI background config

Admin console purpose:

- start refresh/publication actions
- read status/log/history
- expose security/system status
- expose quality/admin-only diagnostic surfaces

## 5. Persistence Layer And Authority Stores

### 5.1 Canonical Publication Stores

Authoritative publication stores for the rebuilt path:

1. `active_publication_pointer`
   - authority: active publication truth
   - key shape: one environment resolves to at most one active bundle
2. `publication_bundles`
   - authority: publication identity and manifest metadata
   - includes publication bundle id, run linkage, assessment linkage, manifest digest
3. `assessment_reports`
   - authority: publication validity truth
   - validity must resolve from the same-run assessment report plus bundle prerequisite

Canonical contract layer:

- `/workspaces/Tao_Financial_Engine/web/src/lib/publication-bundle-contract.ts`

Read/write users of the contract layer:

- `/workspaces/Tao_Financial_Engine/web/src/lib/step1/publication-commit.ts`
- `/workspaces/Tao_Financial_Engine/web/src/lib/publication-state.ts`
- `/workspaces/Tao_Financial_Engine/web/src/lib/runtime-publication-bundle.ts`

### 5.2 Phase Ledger And Operator Summary

Operator-summary stores:

- `runtime_refresh_runs`
- `runtime_refresh_run_phases`

Rule:

- `runtime_refresh_runs` is mirror/operator-summary only
- `runtime_refresh_run_phases` is phase/observability truth for run lifecycle
- publication-validity authority must not be recovered from legacy `runtime_refresh_runs.validation_status`, `snapshot_publication_id`, `quote_publication_id`, `quote_binding_status`, or `is_active_publication`

### 5.3 Runtime Serving Stores

Persistent runtime stores from `/workspaces/Tao_Financial_Engine/web/src/lib/runtime-db.ts`:

- `runtime_decisions_latest`
- `runtime_decisions_history`
- `runtime_symbols`
- `runtime_symbols_history`
- `runtime_decision_provenance_latest`

Supporting runtime read path:

- `/workspaces/Tao_Financial_Engine/web/src/lib/runtime-postgres.ts`

### 5.4 Admin Persistence

Admin operational persistence:

- code path: `/workspaces/Tao_Financial_Engine/web/src/lib/admin-refresh-persist.ts`
- table: `tfe_admin_refresh_persist`
- persisted keys:
  - `status_record_v1`
  - `log_snapshot_v1`
  - `history_snapshot_v1`

Purpose:

- keep admin status/log/history snapshots without blocking refresh operations

## 6. Refresh And Publication Contracts

### 6.1 Existing Snapshot Entry Path

Current existing admin request path:

- route: `/workspaces/Tao_Financial_Engine/web/src/app/api/admin/refresh/route.ts`
- existing request path: `POST /api/admin/refresh` with `{"mode":"snapshot"}`

Cutover rule:

- under `TFE_STEP1_CUTOVER_MODE=enabled`, the existing snapshot request path must dispatch the new Step 1 orchestrator
- it must not dispatch `run_refresh_with_l5_learning.py` for the Step 1 path

### 6.2 Step 1 Object Chain

Code composition path:

- `/workspaces/Tao_Financial_Engine/web/src/lib/step1/orchestrator.ts`

Exact object chain:

1. `createStep1RunRequest`
2. `createCandidateBundleRecord`
3. `createAssessmentReportRecord`
4. `createPublicationCommitRecord`
5. `createQuoteCacheFollowupTicket`

Each object has explicit input/process/output contracts in code and persisted artifacts.

### 6.3 Step 1 Request Contract

Source:

- `/workspaces/Tao_Financial_Engine/web/src/lib/step1/run-request.ts`

Required input fields:

- `normalizedPackageId: string`
- `policySetId: string`
- `modelSetId: string`
- `configSetId: string`
- `bundleClass: string`
- `dependencyClassificationRegister: Record<string, unknown>`
- `targetEnvironment: string`
- `requestedBy: string`
- `assessmentRuleSetId: string`

Primary outputs:

- request artifact `request.json`
- `runtime_refresh_runs` row
- `runtime_refresh_run_phases` row for `candidate_build`

### 6.4 Candidate Bundle Contract

Source:

- `/workspaces/Tao_Financial_Engine/web/src/lib/step1/candidate-bundle.ts`

Rules:

- identity is deterministic for the same normalized package and same policy/model/config identities
- manifest is written under the run artifact tree
- this slice must not touch active publication truth

### 6.5 Assessment Report Contract

Source:

- `/workspaces/Tao_Financial_Engine/web/src/lib/step1/assessment-report.ts`

Rules:

- one report cites exactly one candidate bundle id
- fail case must block publication
- execution timestamps must be real execution time, not synthetic digest time

### 6.6 Publication Commit Contract

Source:

- `/workspaces/Tao_Financial_Engine/web/src/lib/step1/publication-commit.ts`

Rules:

- one commit transaction writes:
  - immutable publication manifest
  - active pointer row
  - publication activation audit row
- investor and admin reads must resolve the same publication bundle id
- commit path must not read quote-cache artifacts

### 6.7 Followup Ticket Contract

Source:

- `/workspaces/Tao_Financial_Engine/web/src/lib/step1/followup-ticket.ts`

Rules:

- follow-up reads pointer-owned publication identity through `readActivePublicationPointer`
- follow-up must not infer publication identity from `screener-quote-cache.json`
- follow-up failure must leave active pointer, publication bundles, and assessment reports unchanged

## 7. Finviz Filters, Screener Parity, And UI Control Surfaces

### 7.1 Finviz Schema And Filter Surface

Schema files:

- `/workspaces/Tao_Financial_Engine/web/src/lib/screener-filter-schema-v111.ts`
- `/workspaces/Tao_Financial_Engine/web/src/lib/screener-filter-v111.ts`

Filter groups:

- descriptive
- fundamental
- technical
- news
- etf
- all

Advanced filter keys include:

- exchange
- index
- sector
- industry
- country
- marketCap
- dividendYield
- shortFloat
- analystRecom
- optionShort
- earningsDate
- avgVolume
- relVolume
- currentVolume
- trades
- priceBand
- targetPrice
- ipoDate
- sharesOutstanding
- float
- theme
- subTheme

### 7.2 Finviz Metadata Cache

Builder:

- `/workspaces/Tao_Financial_Engine/web/scripts/build_screener_finviz_overview_cache.py`

Current cache artifact:

- `/workspaces/Tao_Financial_Engine/web/data/screener-finviz-overview-cache.json`

Observed top-level fields:

- `generated_at_utc`
- `started_at_utc`
- `source_base_url`
- `total_detected`
- `pages_fetched`
- `row_count`
- `rows`

Observed row fields:

- `companyName`
- `country`
- `industry`
- `marketCap`
- `marketCapRaw`
- `sector`
- `source`
- `updatedAtUtc`

### 7.3 Screener API Parity Path

Main screener API:

- `/workspaces/Tao_Financial_Engine/web/src/app/api/screener/route.ts`

Observed contract responsibilities:

- session-authenticated API read
- publication-state load
- published decision load
- runtime snapshot and quote reads
- advanced filter application
- tab and sort controls
- map payload support

### 7.4 UI Parity And Probe Control

Probe tools:

- `/workspaces/Tao_Financial_Engine/tools/verify_screener_parity_matrix.mjs`
- `/workspaces/Tao_Financial_Engine/tools/run_screener_ui_parity_probe_lane.sh`

Spec and master-plan rule:

- screener UI parity is non-critical by default
- non-critical UX parity is non-critical by default
- unrelated UI parity cannot block critical runtime hotfix or publication recovery by default

Sources:

- `/workspaces/Tao_Financial_Engine/TFE_REARCHITECTURE_MASTER_PLAN_v2_7.md`
- `/workspaces/Tao_Financial_Engine/TFE_Specification_v2_7.tex`

## 8. L0-L5, Governance, Epoch, And Quote-Publication Layers

### 8.1 L0-L4 Structural Layer

Source:

- `/workspaces/Tao_Financial_Engine/INGESTION_LAYER_DB_SCHEMA_extracted.txt`

UF Engine rule:

- UF Engine computes structural truth
- it runs UF Kernel L0-L4
- it is stateless per call
- it does not implement governance or recommendations

The extracted contract explicitly says governance belongs to TFE, not the UF engine.

### 8.2 L5 Learning Layer

Legacy path:

- `/workspaces/Tao_Financial_Engine/run_refresh_with_l5_learning.py`

Current code truth:

- L5 learning is optional
- `--skip-l5-learning` is supported
- targeted mode does not run L5 unless `--run-l5-on-targeted` is set
- quote-cache follow-up can be deferred or launched separately

Implication:

- publication-critical rebuild work must not quietly depend on the legacy L5 lane
- L5 remains a separate governance/learning concern, not current publication authority

### 8.3 Governance And Family Coverage

Primary governance coverage source:

- `/workspaces/Tao_Financial_Engine/admin_rulebook_coverage_latest.md`

What it proves:

- many families are still declared but not active
- ladder semantics matter:
  - `require_L0_exact`
  - `allow_L1_relaxed`
  - `safe_only_L2_L3_L4`
- active CP-0 governance is partial and admin/internal in many areas

### 8.4 Blocked Family And Quote Contracts

Blocked family contracts:

- `/workspaces/Tao_Financial_Engine/blocked_family_field_contracts_latest.md`

Quote publication contract:

- `/workspaces/Tao_Financial_Engine/quote_publication_contract_latest.md`

Key quote rule:

- quote-governed eligibility requires explicit same-publication identity alignment
- missing or misaligned quote publication identity must fail closed

### 8.5 Epoch Library And Projection Gap

Epoch contract sources:

- `/workspaces/Tao_Financial_Engine/epoch_state_contract_latest.md`
- `/workspaces/Tao_Financial_Engine/epoch_projection_join_contract_latest.md`
- `/workspaces/Tao_Financial_Engine/epoch_state_runtime_readiness_latest.json`

Current exact truth:

- current snapshot rows have no epoch state
- no epoch sidecar join exists in current runtime sync code truth
- runtime sync currently reads only snapshot and quote artifacts
- epoch sidecar projection is not implemented

Implication:

- epoch-governed families are blocked
- epoch library is a declared future contract layer, not current active serving truth

## 9. Repo Control Corpora And Contract Documents

This repo already contains multiple control/reference documents. They should be treated as different authority classes, not mixed together.

### 9.1 Rebuild Control Corpora

- `/workspaces/Tao_Financial_Engine/corpora/step1_failure_learning_corpus_v1.md`
- `/workspaces/Tao_Financial_Engine/corpora/production_shell_control_corpus_v1.md`
- `/workspaces/Tao_Financial_Engine/corpora/production_shell_system_reference_v2.md`

### 9.2 Domain And Governance Contract Documents

- `/workspaces/Tao_Financial_Engine/admin_rulebook_coverage_latest.md`
- `/workspaces/Tao_Financial_Engine/blocked_family_field_contracts_latest.md`
- `/workspaces/Tao_Financial_Engine/epoch_state_contract_latest.md`
- `/workspaces/Tao_Financial_Engine/epoch_projection_join_contract_latest.md`
- `/workspaces/Tao_Financial_Engine/quote_publication_contract_latest.md`
- `/workspaces/Tao_Financial_Engine/provenance_persistence_parity_latest.md`
- `/workspaces/Tao_Financial_Engine/auth_triage_latest.md`

Rule:

- Step 1 and Phase C control corpora do not replace the domain/governance contracts
- domain/governance contracts do not replace the active publication authority model

## 10. Failure Mode Analysis

### 10.1 Publication Authority Failures

Failure:

- cutover writes new authority tables but readers still validate from legacy run-header fields

Observed instance:

- Step 1 deploy blocker fixed before promotion

Prevention rule:

- under cutover, active truth resolves from `active_publication_pointer`
- validity truth resolves from `publication_bundles` plus `assessment_reports`
- `runtime_refresh_runs` remains mirror only

### 10.2 Persistence Contract Failures

Failures already observed:

- missing local Postgres prerequisite
- `runtime_refresh_runs` insert placeholder mismatch

Prevention rule:

- close persistence prerequisite before runtime smoke
- prove actual row writes, not just build success

### 10.3 Join And Identity Failures

Observed Phase C exact blocker:

- publication-bundle contract matched `assessment_reports` by `assessment_report_id` alone and could bind an older row

Prevention rule:

- same-run prerequisite joins must match `(run_id, assessment_report_id)`
- no ambiguous `LIMIT 1` over non-unique join shapes

### 10.4 Validator Contract Failures

Observed Phase C exact blocker:

- `oracle_integrity` still enforced legacy cutover-invalid fields on live task `234`

Prevention rule:

- runtime validation must have a cutover-aware branch
- predeploy validators must be reconciled before Phase C deploy attempts

### 10.5 Security Failure Modes

Observed/residual:

- stale DB secret in live task caused auth outage
- no shared `TFE_SESSION_SECRET` remains a residual risk

Prevention rule:

- restart/redeploy after secret rotation
- use shared session secret in ECS

### 10.6 Non-Critical Probe Misclassification

Failure class:

- parity or enrichment probe blocks critical recovery or publication

Spec rule:

- UI parity and non-critical enrichment must not block critical runtime correction by default

### 10.7 Detached Follow-Up Failure Class

Failure class:

- detached follow-up outlives terminal run and mutates shared truth

Prevention rule:

- publication-critical path must end before enrichment dependency is considered safe
- detached stale workers must not retain authority over publication truth

## 11. Checks And Balances Control

### 11.1 Gate Order

Required gate order for publication-critical rebuild work:

1. contract artifact
2. readonly/local proof
3. local build gate
4. local persistence prerequisite
5. local production-runtime gate
6. predeploy validator reconciliation
7. controlled production deploy-proof cycle
8. closure or transition decision

### 11.2 Forbidden Shortcuts

- do not promote readonly proof to deploy recommendation
- do not restore legacy authority to `runtime_refresh_runs`
- do not let non-critical parity probes block critical-path recovery by default
- do not claim live success without exact deploy image, ECS revision, and live request-path proof
- do not claim quote-governed readiness without quote-publication identity alignment

### 11.3 Current Next Gate

Allowed next gate:

- one controlled Phase C production deploy-proof cycle using:
  - accepted local Phase C runtime proof
  - accepted runtime validation repair proof
  - the cutover authority model in this file

## 12. Process And Code Flow Diagram

```
Admin browser
  -> POST /api/admin/refresh {"mode":"snapshot"}
  -> /web/src/app/api/admin/refresh/route.ts
  -> step1_cutover branch when TFE_STEP1_CUTOVER_MODE=enabled
  -> /web/src/lib/step1/orchestrator.ts
      -> run-request.ts
         writes request.json + runtime_refresh_runs + runtime_refresh_run_phases
      -> candidate-bundle.ts
         writes candidate manifest
      -> assessment-report.ts
         writes assessment report
      -> publication-commit.ts
         writes publication bundle + manifest digest + active pointer + activation audit
      -> followup-ticket.ts
         writes deferred follow-up ticket using pointer-owned publication identity
  -> publication-state.ts
     resolves active truth from active_publication_pointer
  -> runtime-publication-bundle.ts
     resolves investor-serving bundle from canonical publication-bundle contract
  -> user APIs
     /api/screener
     /api/recommendations/list
  -> admin validation
     run_validation_gate_v1.mjs
  -> non-critical enrichment/parity
     quote follow-up, Finviz cache, UI parity probes
```

## 13. Test And Emulation Model

Current testable model layers in repo:

### 13.1 Local Publication Runtime Model

Components:

- built local production-mode web server
- writable local Postgres
- existing snapshot POST path
- Step 1 orchestrator
- Phase C publication-bundle contract layer

Accepted local proof anchors:

- `/workspaces/Tao_Financial_Engine/backups/runtime/step1-runtime-gate-proof-20260316T003225Z.json`
- `/workspaces/Tao_Financial_Engine/backups/runtime/phase-c-runtime-proof-repair-rerun-20260316T021824Z.json`

### 13.2 Live Validator Model

Component:

- `/workspaces/Tao_Financial_Engine/web/scripts/run_validation_gate_v1.mjs`

Accepted live gate-repair proof:

- `/workspaces/Tao_Financial_Engine/backups/runtime/runtime-validation-gate-repair-proof-20260316T025538Z.json`

### 13.3 UI Parity Emulation Model

Components:

- `/workspaces/Tao_Financial_Engine/tools/run_screener_ui_parity_probe_lane.sh`
- `/workspaces/Tao_Financial_Engine/tools/verify_screener_parity_matrix.mjs`

Rule:

- parity probe is real and useful, but non-critical unless explicitly promoted by policy

## 14. What This File Still Does Not Prove

This file is a reference model. It does not by itself prove:

- live Phase C production deploy success
- full epoch library implementation
- quote-publication contract completion for quote-governed families
- active governance for the full family registry
- elimination of all legacy paths everywhere

Those require separate proof artifacts, not this document.
