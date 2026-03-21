# TFE 5.3 Current Implementation Plan v2.0
**Document ID:** TFE-5.3-PLAN-2.0  
**Status:** Controlled implementation plan for the current TFE instantiation  
**Scope:** Current TFE instantiation only. This plan is **not** the normative system specification. It exists to complete the live AWS cycle, isolate migration regressions, measure thesis conformance, and implement the next L5 canaries without polluting the main specification.

---

## 1. Purpose

This plan directs GPT-5.3-Codex (or equivalent implementation agent) to:
1. preserve and complete the current AWS run;
2. package the resulting artifacts deterministically;
3. isolate regression introduced by the laptop→AWS and non-DB→DB transitions;
4. measure whether the current L5 implementation is actually structurally temporal;
5. implement one thesis-faithful L5 canary based on a structural event tape and shared long/mid/short memory;
6. execute one hard benchmark / kill-test using artifact-backed comparators only.

This plan assumes:
- the live AWS run is the **Pragmatic Serialized Baseline v0**;
- unsupported historical benchmark claims are not to be reused without artifacts;
- no semantic changes are to be made to canonical UF L0–L4.

---

## 2. Guardrails

1. **Do not touch the live AWS run while it is active**, other than health monitoring, checkpoint/resume, or failure-safe recovery.
2. **Do not modify canonical UF L0–L4 semantics.**
3. **Do not silently add heuristics.** Every heuristic must be named, justified, versioned, and logged.
4. **Do not launch another full-universe rerun** until the post-run audits in this plan are complete.
5. **Do not treat the current serialized/per-horizon implementation as a definitive test of the DSF-AI thesis.**
6. **Do not use unsupported benchmark language** in summaries, reports, or release notes.

---

## 3. Deliverables

The implementation agent shall produce the following controlled outputs.

### 3.1 Current-run package
- `current_run_result_pack_latest.json`
- `current_run_stage_loss_latest.json`
- `current_run_environment_fingerprint_latest.json`
- `current_run_artifact_index_latest.json`

### 3.2 Claims/evidence cleanup
- `claims_ledger_latest.md`
- `evidence_inventory_latest.json`

### 3.3 Migration regression isolation
- `migration_baseline_manifest_latest.json`
- `migration_gold_slice_manifest_latest.json`
- `critical_path_repo_parity_latest.json`
- `environment_fingerprint_parity_latest.json`
- `runtime_snapshot_freshness_debug_latest.json`
- `migration_parity_report_latest.json`
- `migration_stage_diffs_latest.json`

### 3.4 Thesis conformance / temporal-use audit
- `temporal_use_audit_latest.json`
- `multiscale_memory_ablation_latest.json`
- `thesis_conformance_report_latest.json`

### 3.5 Thesis-faithful L5 canary
- `structural_event_tape_manifest_latest.json`
- `l5_shared_field_canary_manifest_latest.json`
- `l5_shared_field_canary_results_latest.json`
- `l5_state_trace_samples_latest.json`
- `l5_reservoir_canary_results_latest.json` (optional but recommended)

### 3.6 Benchmark package
- `commercial_benchmark_matrix_latest.json`
- `instantiation_decision_latest.md`

---

## 4. Phase 0 — Live AWS Run Completion and Capture

### 4.1 Objective
Safely complete or resume the current AWS cycle and preserve every significant artifact.

### 4.2 Required actions
1. Keep checkpoint/resume enabled for all evaluation stages.
2. Preserve all stage logs, manifests, return codes, and checkpoint directories.
3. At completion of each stage, record:
   - start timestamp,
   - end timestamp,
   - return code,
   - artifact path(s),
   - digest(s),
   - row/timestamp counts (where applicable),
   - stage status.
4. If the run fails, resume from the earliest valid checkpoint rather than restarting the entire pipeline.

### 4.3 Required result classification
Label the resulting run:
- **Pragmatic Serialized Baseline v0**

Do not label it:
- thesis-faithful,
- definitive,
- or final DSF-AI proof.

### 4.4 Packaging
After the run completes:
- collect h5/h20/h60 reports,
- merge horizon reports,
- collect stage-loss accounting,
- collect full provenance/environment manifest,
- compute hashes for row-trace, temporal dataset, reports, and merged outputs.

---

## 5. Phase 1 — Claims Ledger and Evidence Inventory

### 5.1 Objective
Separate verified facts from prototype-only claims and invalid/unsupported claims.

### 5.2 Required states
- **Verified**
- **Prototype-only**
- **Invalid / unsupported**

### 5.3 Automatically classify as invalid/unsupported unless artifacts are found
- ARIMA/LSTM/Transformer/PPO comparative return tables
- “competitive with trained deep models”
- any WallStreetZen or similar comparator claim
- any percentage claim lacking a named artifact package

### 5.4 Prototype-only if supported by an actual artifact package
- directional / threshold / coherence-gated NASDAQ prototype result

### 5.5 Required fields per claim
- claim id
- claim text
- status
- evidence paths
- confidence
- notes

---

## 6. Phase 2 — Migration Regression Isolation

### 6.1 Objective
Prove or disprove that the current behavior drift was introduced by migration:
- laptop → AWS
- non-DB-centric → DB-centric
- old runtime path → new runtime path

### 6.2 Gold slice
Construct one gold slice:
- 25–100 symbols
- contiguous date block
- horizons 5, 20, 60
- include symbols affected by stale-runtime or recommendation issues

### 6.3 Baseline package
Assemble the strongest recoverable known-good pre-migration package:
- nearest runnable laptop repo state
- known-good recommendation/runtime artifact
- relevant config
- any linked screenshots or outputs
- any matching row-trace/report

### 6.4 Critical-path repo/runtime parity
Compare only these between laptop and deployed environments:
- recommendation backend/API
- stale snapshot gate
- “latest snapshot” selection query and ordering logic
- timestamp/timezone utilities
- DB models/migrations for snapshots/recommendations
- runtime policy loader
- stage-skip logic
- package/env fingerprint

### 6.5 Runtime snapshot freshness diagnostics
For a gold-slice request and a representative live recommendation request, capture:
- selected snapshot id
- selected snapshot timestamp
- current server UTC
- computed age
- freshness threshold
- timezone source
- exact query/order rule used to select “latest”
- artifact/run id actually served

### 6.6 Parity matrix
Run the maximum feasible subset of:
- A. legacy path + local/file-based
- B. legacy path + AWS
- C. DB-centric path + local
- D. DB-centric path + AWS

### 6.7 Decision rule
**First mismatch wins.**  
Once the earliest divergence is found, stop downstream interpretation and localize the root cause there.

---

## 7. Phase 3 — Thesis Conformance and Temporal-Use Audit

### 7.1 Objective
Determine whether the current L5 is genuinely using structural temporality and shared multi-scale memory, or whether it is effectively old-world ML in disguise.

### 7.2 Frozen setup
Use:
- the exact same frozen h5 data,
- the same split definitions,
- the same artifact versions,
- the same provenance tuple as the current AWS run.

### 7.3 Required audit conditions
A. real ordered sequence  
B. shuffled lag/event order  
C. reversed lag/event order  
D. current-state only  
E. lag/history zeroed or masked  
F. short-memory band removed  
G. mid-memory band removed  
H. long-memory band removed  
I. phase-jitter / change-point shuffle while preserving marginals

### 7.4 Required metrics
For each condition, report:
- outcome_over_index_pct
- mean_excess_vs_spy
- per-split metrics
- aggregate metrics
- delta vs real ordered sequence

### 7.5 Interpretation rules
- If A ≈ B ≈ C ≈ D ≈ E, current L5 is **not structurally temporal**.
- If removing short/mid/long bands barely matters, current L5 is **not using multi-scale memory**.
- If disabling multi-view fusion barely matters where multiple views/cores are active, current L5 is **not meaningfully using the ensemble structure**.

### 7.6 Thesis-conformance classification
Classify the current implementation as:
- **thesis-faithful**
- **pragmatic approximation**
- **non-conformant**

---

## 8. Phase 4 — Thesis-Faithful L5 Canary

### 8.1 Objective
Build one small but real L5 canary that more faithfully matches the DSF-AI thesis.

### 8.2 Mandatory design rules
1. Input is an **ordered structural event tape**, not a primary lagged row table.
2. One **shared internal state** is maintained across long/mid/short memory.
3. 5/20/60 are **heads over shared state**, not independent semantic worlds.
4. No silent heuristics.
5. Any domain rule must be explicitly logged in the heuristics registry.

### 8.3 Implementation tasks
#### A. Structural Event Tape
Build `structural_event_tape_builder.py` to emit events such as:
- gate open / close
- resonance peak / trough / reversal
- negative-space onset / release
- stability threshold crossing
- collapse flag on / off
- regime dwell-time update
- approved domain-rule event
- epoch impact update

#### B. Shared-Field L5
Build `l5_shared_field_canary.py` implementing:
- shared fast/mid/slow memory state,
- coherence field variables (tempo, phase, coherent potential),
- mode-amplitude memory over histories,
- free structural energy / inconsistency gating,
- horizon heads for 5/20/60 at the end only.

#### C. Optional reservoir variant
Build `l5_reservoir_canary.py` using:
- structural event tape input,
- fixed sparse recurrent reservoir,
- lightweight deterministic readout.

### 8.4 Gold-slice only
This phase shall run on a gold slice only.  
No full-universe rerun is allowed until the canary is understood.

### 8.5 Comparison set
Compare:
- current pragmatic serialized baseline
- shared-field canary
- reservoir canary (if built)

### 8.6 Interpretation rule
- If the shared-field or reservoir canary beats the serialized baseline on the gold slice, the current L5 was architecturally mismatched.
- If both fail cleanly, the thesis is weakened.

---

## 9. Phase 5 — Financial Governance and Epoch Library Implementation

### 9.1 Objective
Bring the current TFE instantiation closer to the normative spec for financial governance and epoch handling.

### 9.2 Required tasks
1. Build or finalize a controlled **epoch library**:
   - event classes,
   - severity,
   - confidence,
   - persistence,
   - source provenance,
   - 32-channel sphere-of-impact vectors.
2. Implement a deterministic **G32 Coordinator** that fuses active epoch objects into the live macro/domain mosaic.
3. Implement deterministic symbol/sector/industry coupling:
   - sector sensitivity matrix,
   - industry sensitivity matrix,
   - symbol exposure vector.
4. Implement explicit financial-governance scoring:
   - fundamental quality classes,
   - speculation/fragility penalties,
   - investability score.
5. Log every epoch-driven or domain-rule-driven adjustment.

### 9.3 Minimal financial rule classes to implement
- profitability / margin quality
- cash-generation quality
- leverage / coverage stress
- revenue / earnings deterioration
- valuation penalty
- sector-cycle pressure
- macro/war/rates/build-cycle pressure
- explicit abstention or no-output conditions

---

## 10. Phase 6 — Hard Benchmark and Kill Test

### 10.1 Objective
Make the commercial decision on artifact-backed evidence only.

### 10.2 Required benchmark matrix
- TFE keyed baseline
- current pragmatic TMA
- thesis-faithful shared-field TMA canary
- simple non-DSF baseline
- standard ML baseline
- external practical comparator on overlapping symbols/dates if available
- SPY / passive baseline

### 10.3 Rules
1. All comparators must use overlapping symbols/dates and explicit artifact packages.
2. No benchmark claim may be surfaced without a named result artifact.
3. External comparator claims shall be clearly labeled with methodology and sampling limits.

### 10.4 Kill rule
If TFE does not materially beat practical alternatives on artifact-backed results, classify:
- **this instantiation = non-competitive**

This does **not** automatically falsify DSF-AI as a research idea; it falsifies the competitiveness of the current instantiation.

---

## 11. Heuristics Registry

### 11.1 Objective
Prevent silent “just make it work” logic from replacing the thesis.

### 11.2 Every heuristic entry must record
- heuristic id
- name
- exact deterministic rule
- scope
- justification
- approver
- approval date
- rollback / expiration condition

### 11.3 Examples of admissible heuristics
- stale snapshot gating
- invalid data rejection
- mandatory abstention under collapse / SafeMode
- explicit cooldown after structural reversal
- approved sector/epoch hard-block

### 11.4 Examples of non-admissible shortcuts
- undeclared row-first flattening as the primary scientific object
- semantic separation of horizons without justification
- threshold retuning to save a run
- undocumented ticker-specific overrides

---

## 12. Stop / Go Criteria

### Stop if
- the live AWS run is still active and the requested step would alter its semantics;
- an earlier-stage migration mismatch is identified but not yet resolved;
- thesis conformance is still unknown and someone attempts to make definitive benchmark claims.

### Go to next phase only if
- the current phase outputs exist,
- artifacts are hashed and logged,
- the result has been classified,
- and any blocking deviations are either fixed or formally recorded.

---

## 13. Minimum Sequence of Work (Actionable)

1. **Finish / capture the live AWS run**  
2. **Build the current-run result pack**  
3. **Build claims ledger and evidence inventory**  
4. **Run migration regression isolation on a gold slice**  
5. **Run critical-path repo/runtime parity**  
6. **Run temporal-use / thesis-conformance audit**  
7. **Implement structural-event-tape shared-field canary**  
8. **Implement epoch library + G32 + financial-governance scoring where missing**  
9. **Run hard benchmark matrix**  
10. **Issue instantiation decision**

---

## 14. Completion Criteria

This implementation plan is complete only when:
- the current run is classified and preserved,
- migration drift has either been ruled in or ruled out,
- thesis conformance of the current L5 is known,
- the thesis-faithful L5 canary exists and is benchmarked,
- the claims ledger is cleaned,
- and the current instantiation has a formal competitive / non-competitive decision.
