# TFE 5.3 Implementation Plan v1.1

## 1. Purpose

This document is the **implementation plan** for 5.3. It is **not** the TFE normative specification. Its purpose is to recover the current TFE instantiation, isolate migration regressions, test whether the present L5 implementation is thesis-faithful, and build the next deterministic L5 canaries without polluting the normative specification with implementation triage.

## 2. Non-Negotiable Constraints

1. **Do not touch the live AWS run while it is active.**
2. **Do not launch another full-universe rerun after the current cycle** until the audits below are complete.
3. **Treat prior months of user validation as real prior work** to be salvaged, not dismissed.
4. **Classify the current live run as** `Pragmatic Serialized Baseline v0`.
5. **L0–L4 remain canonical and imported.** No semantic changes.
6. **SES controls remain mandatory** for any protected structural payload, including PRP-derived event tapes and checkpoints.
7. **No silent heuristics.** Any heuristic must be named, justified, approved, versioned, and auditable.
8. **No broad full-repo diff as the first move.** Use targeted parity and runtime diagnostics first.

## 3. Immediate Output Preservation from the Current AWS Run

### 3.1 Required artifacts to preserve

- stage manifests
- h5 / h20 / h60 reports
- merged horizon report
- split checkpoints
- stage-loss accounting
- AWS environment / provenance manifest
- run logs and return codes
- final dataset hashes for rowtrace and temporal dataset

### 3.2 Required classification

Record the current run as:

- `run_family = pragmatic_serialized_baseline`
- `thesis_status = not_yet_thesis_faithful`
- `reason = row/materialized approximation and currently horizon-separated evaluation path`

## 4. Minimum Viable Recovery Pack

**Goal:** salvage the destroyed / scattered chat work in a decision-grade form without launching a weeks-long corpus project.

### 4.1 Build these files

- `vision/recovery/RECOVERY_PACK.md`
- `vision/recovery/RECOVERED_FACTS.json`

### 4.2 Sources to mine

- `LOAD_DIRECTIVE*.md`
- `AWS_RUNBOOK.md`
- added/modified scripts
- manifests
- checkpoints
- runtime logs
- Slack notify log
- current benchmark outputs
- screenshots / notes if locally available

### 4.3 Required sections in `RECOVERY_PACK.md`

1. DSF thesis in 10–15 bullets
2. DSF killers / anti-patterns in 10–15 bullets
3. recovered validations:
   - claim
   - evidence path
   - confidence (`high`, `medium`, `memory_only`)
4. migration changes:
   - laptop → AWS
   - non-DB → DB
   - sparse/runtime → full temporal
   - runtime selection/loading changes
5. current AWS run classification
6. top 5 unresolved questions

### 4.4 `RECOVERED_FACTS.json` schema

Each entry must contain:

- `id`
- `claim`
- `status` = `verified | prototype_only | memory_only | invalid_or_unsupported`
- `evidence_paths`
- `notes`

## 5. Claims Ledger / Evidence Cleanup

### 5.1 Build

- `vision/recovery/CLAIMS_LEDGER.md`
- `vision/recovery/EVIDENCE_INVENTORY.json`

### 5.2 Allowed claim states

- `Verified`
- `Prototype-only`
- `Invalid / unsupported`

### 5.3 Mark as invalid / unsupported unless artifacts exist

- ARIMA / LSTM / Transformer / PPO comparative return tables
- “competitive with trained deep models”
- any claim about beating or matching WallStreetZen or similar tools
- any percentage claim without run artifacts
- any cross-model benchmark without its benchmark package

### 5.4 Mark as prototype-only if artifact exists

- directional / threshold / coherence-gated NASDAQ prototype result

## 6. Migration Regression Isolation

**Goal:** test the narrower claim that AWS + DB-centric migration changed behavior relative to the known-good pre-migration system.

### 6.1 Build

- `migration_baseline_manifest_latest.json`
- `migration_gold_slice_manifest_latest.json`
- `migration_parity_report_latest.json`
- `migration_stage_diffs_latest.json`
- `runtime_snapshot_freshness_debug_latest.json`

### 6.2 Gold slice

Use:

- 25–100 symbols
- contiguous date block
- horizons 5 / 20 / 60
- include symbols affected by UI/runtime issues

### 6.3 Parity matrix (run max feasible subset)

- A. legacy path + local/file-based
- B. legacy path + AWS
- C. DB-centric path + local
- D. DB-centric path + AWS

### 6.4 Capture stage-level parity artifacts

For each feasible mode, capture:

- input hashes/counts
- ordered timestamps by symbol
- snapshot metadata
- row-trace hashes/counts
- temporal dataset hashes/counts
- eval split counts
- final recommendation payload / stale-gate reason

### 6.5 Freshness diagnostics must emit

- selected snapshot id
- selected snapshot timestamp
- `now_utc`
- computed `age_sec`
- freshness threshold
- timezone source / parse path
- exact “latest snapshot” selector/query
- sort/order field used
- artifact/run id actually served

### 6.6 Rule

**First mismatch wins.**

Stop downstream interpretation once the earliest divergence is identified.

## 7. Targeted Repo / Runtime Parity

### 7.1 Build

- `critical_path_repo_parity_latest.json`
- `environment_fingerprint_latest.json`

### 7.2 Compare only these critical files / paths

- recommendations backend/API
- stale snapshot gate
- latest snapshot selector/query
- timestamp / timezone utilities
- DB models / migrations for snapshots and recommendations
- runtime policy loader
- stage-skip logic
- env/package locks / fingerprints

### 7.3 Interpretation

- same critical hashes + same env fingerprint + different behavior ⇒ investigate runtime/data/DB selection
- different critical hashes ⇒ targeted code diff justified

## 8. Thesis Conformance Gate

**Goal:** decide whether the current implementation is a valid test of the DSF-AI thesis or merely a pragmatic approximation.

### 8.1 Build

- `tools/thesis_conformance_audit.py`
- `outputs/thesis_conformance_report_latest.json`

### 8.2 Required checks

A. structural continuity preserved?
- ordered structural event stream available?
- transitions, dwell times, and field evolution represented?

B. long/mid/short memory jointly represented?
- one shared state or shared encoder?
- or silently split into separate horizon worlds?

C. temporal order matters?
- if shuffled/reversed/current-only performs similarly, fail conformance

D. negative-space / structural-absence sensitivity present?
- if removing absence-sensitive structure changes nothing, fail conformance

E. heuristics controlled?
- all declared, approved, logged?
- any silent workaround = conformance failure

F. shared-horizon state?
- if thesis says long/mid/short are jointly interpreted, fully horizon-separated modeling is presumed non-conformant unless equivalence is demonstrated

### 8.3 Required classification

Classify each implementation as:

- `thesis_faithful`
- `pragmatic_approximation`
- `non_conformant`

## 9. Temporal-Use Audit

**Goal:** determine whether the current TMA implementation is actually using temporal structure or merely wearing temporal clothing.

### 9.1 Build

- `temporal_use_audit_latest.json`
- `multiscale_memory_ablation_latest.json`

### 9.2 Run on the exact same frozen h5 split setup and data

Compare:

- A. real ordered sequence
- B. shuffled lag / event order
- C. reversed lag / event order
- D. current-state only
- E. lag features zeroed / masked
- F. short-memory band removed
- G. mid-memory band removed
- H. long-memory band removed
- I. phase-jitter / change-point shuffle

### 9.3 For each condition report

- `outcome_over_index_pct`
- `mean_excess_vs_spy`
- per-split metrics
- aggregate metrics
- delta vs real ordered sequence

### 9.4 Interpretation

- If A ≈ B ≈ C ≈ D ≈ E, the implementation is **not structurally temporal**.
- If F/G/H barely matter, the implementation is **not using multi-scale memory**.
- If phase-jitter changes little, the implementation is **not sensitive to structural timing**.

## 10. Thesis-Faithful L5 Canary

**Goal:** build a small, proper L5 canary that matches the thesis more closely than the current serialized baseline.

### 10.1 Build

- `structural_event_tape_builder.py`
- `l5_shared_field_canary.py`
- optional `l5_reservoir_canary.py`
- `l5_canary_manifest_latest.json`
- `l5_canary_results_latest.json`
- `l5_state_trace_samples_latest.json`

### 10.2 Rules

1. input is an **ordered structural event stream**, not a CSV-first lag-table as the primary object
2. use **one shared state**
3. use **one shared temporal encoder / field**
4. derive **three heads only at the end**: 5 / 20 / 60
5. **no semantically separate horizon worlds**
6. **no silent heuristics**
7. approved domain rules only, explicitly logged

### 10.3 Minimum state variables

- fast memory state
- mid memory state
- slow memory state
- stability / robustness context
- negative-space pressure
- regime age / dwell time
- resonance phase
- collapse proximity
- cross-core coherence if multiple cores are active

### 10.4 Minimum outputs

- structural confidence
- action direction
- action persistence tendency
- abstain / insufficient-structure flag

### 10.5 Interpretation

- if shared-field canary beats serialized baseline on the gold slice ⇒ current L5 was architecturally mismatched
- if it still loses cleanly ⇒ the thesis is weakened

## 11. Multi-View / Multi-Core Deterministic Fusion

**Goal:** recover the “multiple cores are allowed” concept in a deterministic, audited implementation.

### 11.1 Build

- `core_view_manifest_latest.json`
- `deterministic_multiview_fusion_latest.json`

### 11.2 Requirements

- all views/cores are explicitly declared
- same input domain, same kernel semantics
- deterministic fusion weights
- explicit disagreement, novelty, and quality metrics
- no silent core spawning in production paths

### 11.3 Optional deterministic spawn/merge only in canaries

If deterministic spawn / merge is tested, it must be:

- bounded
- versioned
- seeded/logged if seeded offsets are used
- disabled by default in controlled benchmarks unless explicitly under test

## 12. Hard Benchmark / Commercial Kill Test

### 12.1 Build

- `commercial_benchmark_matrix_latest.json`
- `instantiation_decision_latest.md`

### 12.2 Compare

- TFE keyed baseline
- best current pragmatic TMA
- thesis-faithful shared-field canary
- simple non-DSF baseline
- standard ML baseline
- external comparator like WallStreetZen on overlapping symbols/dates if accessible
- SPY / buy-and-hold

### 12.3 Kill rule

If TFE does **not materially beat** practical alternatives on **artifact-backed results**, classify the current instantiation as:

- `non_competitive`

This classification applies to the **current instantiation**, not necessarily to DSF-AI as a broader research thesis.

## 13. Heuristics Governance

### 13.1 Build

- `heuristics_registry_latest.json`

### 13.2 Each heuristic entry must include

- name / identifier
- justification
- exact mathematical rule or threshold
- applicability scope
- approver and approval date
- rollback / expiration condition
- associated tests

### 13.3 No silent hacks

No undeclared:

- fallback thresholds
- hidden abstain logic
- hidden batching that changes semantics
- hidden flattening assumptions
- hidden environment-specific overrides

## 14. Operating Order of Work

### Phase A — finish current run untouched

1. let live AWS cycle finish
2. preserve artifacts
3. classify run as `Pragmatic Serialized Baseline v0`

### Phase B — recover and clean evidence

4. build `RECOVERY_PACK`
5. build claims ledger / evidence inventory

### Phase C — isolate migration and runtime drift

6. migration regression isolation
7. targeted repo/runtime parity
8. stale snapshot / latest-artifact diagnostics

### Phase D — test thesis conformance

9. thesis conformance audit
10. temporal-use audit

### Phase E — build next L5 canaries

11. structural event tape builder
12. shared-field L5 canary
13. optional reservoir canary
14. deterministic multi-view fusion canary

### Phase F — benchmark and decide

15. hard benchmark matrix
16. commercial kill rule disposition

## 15. Explicit Do-Not-Do List

Do **not**:

- launch another full-universe rerun after the current cycle before the audits are done
- do a blind full-repo compare first
- use unsupported benchmark language
- call the current pragmatic serialized run a definitive test of DSF-AI
- pollute the normative specification with this implementation triage

## 16. Definition of Success

This implementation plan is successful if it produces:

1. one preserved current AWS baseline package
2. one minimum viable recovery pack
3. one migration parity report identifying either equivalence or the first divergence
4. one thesis conformance report classifying the current implementation
5. one temporal-use audit proving whether temporal structure is actually used
6. one thesis-faithful L5 canary on a gold slice
7. one artifact-backed benchmark matrix and explicit competitive / non-competitive disposition
