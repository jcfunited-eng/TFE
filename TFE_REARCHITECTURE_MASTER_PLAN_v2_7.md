# TFE Re-Architecture Master Plan v2.7

Generated (UTC): 2026-03-14T00:00:00Z
Workspace: `/workspaces/Tao_Financial_Engine`
Status: Controlled architecture reset plan
Purpose: Replace the current coupled refresh/deploy/publication path with a commercial-grade deterministic advisor architecture that fits TFE's resource limits.

## 1. Decision

TFE must stop evolving the current monolithic refresh/publish path by incremental patching.

The system will be re-architected into separate operational planes with explicit contracts:

1. Source Plane
2. Assessment and Publication Plane
3. Serving Plane
4. Enrichment Plane
5. Product Deployment Plane

This plan is the authoritative execution order for that re-architecture.

## 2. System Class

TFE is a financial advisor platform.

It is not:

1. a high-frequency trading platform
2. an exchange co-location system
3. a Bloomberg Terminal clone
4. a proprietary private-network market-data utility

TFE should adopt the commercial patterns that matter for an advisor platform:

1. normalized multi-source data intake
2. canonical data truth
3. in-memory hot serving for current active artifacts
4. deterministic assessment and publication
5. asynchronous non-critical enrichment
6. resilient deployment and failover
7. automation across front, middle, and back office functions

TFE should not make ultra-low-latency trading infrastructure its primary architecture target.

## 3. Why Re-Architecture Is Required

The current production behavior has demonstrated these non-acceptable properties:

1. Production deployment can be blocked by unrelated UI parity gates.
2. Publication can be blocked behind quote-cache enrichment.
3. Runtime phase state can require log inference instead of durable contract state.
4. Refresh, enrichment, validation, and publication are too tightly coupled.
5. Production troubleshooting takes too long because critical-path truth is fragmented across logs, routes, runtime rows, and artifacts.
6. The system does not cleanly separate advisor functionality from terminal-style data concerns.

These are architecture failures, not isolated bugs.

## 4. External Commercial Patterns To Adapt

The external material reviewed supports these patterns:

1. low-latency providers normalize many feeds behind one interface and reduce client-side integration burden
2. real-time financial analytics systems rely on parallel processing, in-memory or cached hot data, ordered timing, and explicit observability
3. wealth-advisor technology stacks are commonly organized as front office, middle office, and back office, with automation and workflow efficiency as first-class goals

Relevant sources:

1. A-Team market-data overview: `https://a-teaminsight.com/blog/the-top-low-latency-data-feed-providers/`
2. Supermicro real-time analytics infrastructure overview: `https://learn-more.supermicro.com/data-center-stories/high-performance-infrastructure-real-time-financial-analytics`
3. AVP wealth-tech operating model overview: `https://avpcap.com/the-future-of-financial-advice-technologys-role-in-the-market/`

## 5. Commercial Adaptation Profile For TFE

### 5.1 Adopt Now

TFE should adopt these patterns immediately:

1. source tiering and normalization behind one canonical data contract
2. one canonical securities and reference-data truth
3. one canonical publication bundle for investor serving
4. in-memory hot serving of the active publication bundle
5. conflated display semantics for fast-changing market views
6. parallel execution only for independent planes and bounded workloads
7. explicit current-phase state and per-phase durable ledger rows
8. front-office, middle-office, and back-office separation in the system design
9. redundancy at the cloud/service level before exotic low-latency infrastructure

### 5.2 Adopt Later If Scale Requires It

TFE may adopt these patterns later:

1. GPU-backed optimization or simulation workloads
2. regional failover beyond current single-region recovery posture
3. specialized high-throughput feed handlers for premium market-data products
4. stronger edge caching and regional replicas

### 5.3 Not A Primary Target For TFE

TFE should not optimize around these as first-line architecture goals:

1. exchange co-location
2. direct market access infrastructure
3. FPGA packet processing
4. proprietary private global backbone networking
5. microsecond trading latency as the principal success metric

## 6. Target Architecture

### 6.1 Architecture Backbone

TFE shall operate under this deterministic backbone:

`source -> normalize -> assess candidate -> publish immutable bundle -> serve active bundle`

Everything outside that backbone shall be treated as non-critical follow-up work unless the specification explicitly marks it publication-critical.

### 6.2 Front / Middle / Back Office Mapping

#### Front Office

Purpose:
Advisor-facing and client-facing experiences.

Examples:

1. recommendations
2. portfolio advisor surfaces
3. proposal generation
4. report generation
5. dashboards
6. alerts

#### Middle Office

Purpose:
Assessment, controls, compliance, publication, and advisor workflow governance.

Examples:

1. candidate assessment
2. validation gates
3. publication activation
4. suitability and policy controls
5. market-data quality monitoring

#### Back Office

Purpose:
Operational records, reconciliation, billing/supporting data, retention, and archival controls.

Examples:

1. records retention
2. deployment records
3. source-package archives
4. reconciliation outputs
5. audit trails

### 6.3 Operational Planes

#### Source Plane

Purpose:
Acquire, normalize, and version raw inputs.

Critical output:
One immutable source package and one immutable normalized package.

Examples:

1. raw market data package
2. raw fundamentals package
3. raw account/reference package
4. normalized securities master
5. normalized structural snapshot input

#### Assessment and Publication Plane

Purpose:
Build one candidate publication from one exact normalized input set, assess it, and publish it atomically if and only if it passes.

Critical output:

1. candidate bundle
2. assessment report
3. immutable publication bundle
4. atomic active pointer change

#### Serving Plane

Purpose:
Serve recommendations, portfolio, watchlist, screener, admin status, and related investor surfaces from the active publication bundle only.

Critical output:

1. user-facing deterministic responses tied to one publication identity

#### Enrichment Plane

Purpose:
Perform non-critical follow-up work after publication or in parallel when explicitly safe.

Examples:

1. quote cache refresh
2. profile overrides
3. screener metadata overlays
4. UI parity probes
5. analytics and quality probes

This plane must not block publication unless a dependency is explicitly designated publication-critical in the spec.

#### Product Deployment Plane

Purpose:
Deploy application/runtime code to production independently of data publication.

Critical output:

1. new task definition
2. new image
3. deployed commit identity
4. progressive rollout evidence

Unrelated UI probes must not block emergency runtime recovery or publication pipeline fixes unless they are explicitly classified as critical-path safety gates.

## 7. Canonical Runtime Objects

The re-architecture shall standardize these canonical objects:

1. `source_package`
2. `normalized_package`
3. `candidate_bundle`
4. `assessment_report`
5. `publication_bundle`
6. `active_publication_pointer`
7. `phase_ledger`
8. `deployment_record`
9. `hot_serving_cache`

Each object must have:

1. immutable identity
2. creation timestamp
3. producer identity
4. exact input dependency identities
5. exact output schema
6. explicit failure code and failure detail when generation fails

## 8. Deterministic Contracts

### 8.1 Publication Contract

Publication must satisfy all of these:

1. Candidate bundle must be built from one exact normalized package.
2. Assessment must evaluate that exact candidate bundle.
3. Publish must create one immutable publication bundle.
4. Activation must be one atomic pointer change.
5. Serving must read only the active publication bundle.
6. Enrichment must not be allowed to redefine publication truth after activation.

### 8.2 Serving Contract

Serving must satisfy all of these:

1. No route may mix active publication state with raw latest runtime rows.
2. No route may recompute investor-facing decision truth from local policy files.
3. Every route must expose the active publication identity and serving state.
4. If serving is blocked, the route must expose exact blocking reason code and detail.
5. The hot serving cache must be derived from the active publication bundle, not from ad hoc runtime state.

### 8.3 Refresh and Phase Contract

Every refresh run must durably record:

1. `run_id`
2. `phase_name`
3. `input_contract`
4. `process_status`
5. `started_at`
6. `completed_at`
7. `last_heartbeat_at`
8. `output_contract`
9. `failure_code`
10. `failure_detail`

Critical phases:

1. `snapshot_rebuild`
2. `quote_cache_refresh`
3. `profile_overrides_refresh`
4. `runtime_postgres_sync`
5. `validation_gate`
6. `publication_activation`

### 8.4 Source Contract

TFE source handling must satisfy all of these:

1. raw vendor or internal input is versioned before transformation
2. normalization is deterministic
3. each normalized package cites all source package identities
4. canonical serving never reads raw vendor data directly

## 9. Data Sourcing Model

### 9.1 Source Tiers

TFE shall use a tiered sourcing model.

#### Tier 1

Primary market, price, or reference source used for production-critical normalized truth.

#### Tier 2

Secondary or backup source used for reconciliation, backfill, fallback, or enrichment.

#### Tier 3

Internal operational data used for advisory workflows, portfolios, accounts, preferences, and reports.

### 9.2 Canonical Normalization

All Tier 1 and Tier 2 data must be transformed into one canonical normalized contract before it is used by assessment or publication.

TFE should copy the commercial pattern of a single normalized interface, not the commercial pattern of ultra-expensive feed plumbing.

## 10. Hot Cache And Conflation

TFE shall implement a hot serving cache, but only for the active publication bundle.

Conflation rule:

1. fast-changing source updates may be conflated for advisor-facing display
2. conflation must preserve the latest valid state
3. conflation must not rewrite publication truth

This is the commercial adaptation of terminal-style display efficiency without turning TFE into a tick-by-tick HFT platform.

## 11. Resilience Baseline

The minimum resilience target for TFE is:

1. deterministic deployment records
2. source and publication artifact retention
3. recoverable runtime state
4. cloud-level redundancy before specialized hardware redundancy
5. ordered time and durable event sequencing

Multi-AZ and recoverable cloud service design are in scope now.
Colocation, FPGA, and private backbone networking are not in scope now.

## 12. Release Policy

TFE shall use separate gate classes.

### 12.1 Critical Release Gates

These gates may block deployment:

1. build failure
2. packaging failure
3. migration failure
4. runtime boot failure
5. security failure
6. publication safety failure

### 12.2 Non-Critical Release Gates

These gates must not block emergency runtime correction by default:

1. screener UI parity
2. non-critical UX parity
3. recommendation quality probes not tied to runtime safety
4. asynchronous enrichment probes

These may still fail the release record, but they must not prevent shipping a clearly scoped critical-path recovery without explicit override policy.

## 13. Implementation Order

### Phase 0: Immediate Production Containment

Deliverables:

1. deploy the existing commit line that contains:
   - full-universe quote-cache defer/follow-up
   - runtime `bs4` dependency
   - canonical refresh phase ledger
2. prove that production failure classification comes from ledger truth

Acceptance:

1. any remaining failure is phase-exact
2. publication is no longer blocked behind non-critical quote-cache work for full-universe runs

### Phase A: Split Critical Path From Non-Critical Work

Deliverables:

1. publication no longer waits on quote-cache enrichment for full-universe runs
2. enrichment runs as follow-up lane
3. runtime image dependency failures surface as exact phase failures

Acceptance:

1. full-universe publication can complete while enrichment continues separately
2. enrichment failure is ledgered without blocking publication unless declared critical

### Phase B: Complete Canonical Phase Ledger

Deliverables:

1. runtime refresh phase child table
2. current-phase mirror on `runtime_refresh_runs`
3. admin route reads ledger directly

Acceptance:

1. any live run can be identified to one exact phase
2. no critical phase failure requires log-tail inference

### Phase C: Formalize Publication Bundles

Deliverables:

1. immutable publication bundle identity
2. bundle manifest
3. atomic activation pointer
4. exact bundle prerequisites

Acceptance:

1. one environment has at most one active publication
2. all investor routes serve that same active publication

### Phase D: Separate Product Deployment From Data Publication

Deliverables:

1. release gate classes
2. hotfix lane
3. deployment record with deployed commit and image identity

Acceptance:

1. unrelated UI parity failures cannot block critical runtime hotfix rollout by default

### Phase E: Formalize Source And Normalized Packages

Deliverables:

1. versioned source package manifests
2. normalized package manifests
3. deterministic identity rules

Acceptance:

1. candidate assessment always cites exact source and normalized package identities

### Phase F: Complete Front/Middle/Back Office Boundary Contracts

Deliverables:

1. front-office serving contracts
2. middle-office publication and control contracts
3. back-office record, reconciliation, and archival contracts

Acceptance:

1. each function is assigned to one office boundary and one operational plane

### Phase G: Final Spec And Conformance Program

Deliverables:

1. controlled v2.7 specification
2. traceability matrix
3. conformance tests
4. release criteria

Acceptance:

1. architecture, code, and operations have one controlled spec baseline

## 14. First Active Workstream

The first active workstream shall be:

`Split the publication critical path from non-critical enrichment and enforce ledger-first phase truth.`

This is the first workstream because it addresses the current production failure class directly and creates the observability needed for every later phase.

## 15. What i5.4 Should Build First

The first implementation unit under this plan is:

1. get the already-built defer-plus-ledger-plus-runtime-dependency fix live in prod
2. prove the live system now reports phase truth without log inference

This is not the final architecture. It is the first controlled cutover step toward it.

## 16. Spec Authoring Rule

The v2.7 specification shall not be written as aspirational marketing language.

Each section must contain:

1. purpose
2. inputs
3. outputs
4. invariants
5. state transitions
6. failure semantics
7. conformance criteria
8. traceability targets

## 17. Recommendation

The recommended path is:

Write the v2.7 spec in parallel with the re-architecture, but execute the implementation in the phase order above and keep only one active workstream at a time.
