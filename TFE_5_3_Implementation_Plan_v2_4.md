# TFE 5.3 Implementation Plan v2.4

**Status:** controlled implementation plan aligned to TFE Specification v2.4  
**Scope:** current TFE instantiation only  
**Goal:** increase competitiveness without destabilizing the functioning application while building a thesis-faithful next-generation L5 offline.

---

## 1. Executive intent

This plan separates work into two lanes:

- **Lane A — Protect and deepen CP-0 (current production L5)**
- **Lane B — Build and test CP-2 (thesis-faithful L5) offline**

The immediate objective is **not** to replace the current application. The immediate objective is to:
1. preserve current production value,
2. identify exactly what is choking competitiveness,
3. improve CP-0 where the ROI is highest,
4. build a real CP-2 sidecar that can later compete for promotion.

---

## 2. Core constraints

1. Do **not** destabilize the currently functioning application.
2. Do **not** resume the stopped large h5/h20/h60 run.
3. Do **not** launch another full-universe benchmark before the focused diagnosis and CP-0 improvements are complete.
4. All heuristics must be explicit, versioned, justified, and auditable.
5. Every change must declare whether it applies to:
   - **CP-0 Current Production**
   - **CP-1 Transitional Hybrid**
   - **CP-2 Thesis-Faithful Target**
6. No unsupported benchmark claims may be published or reused.

---

## 3. The competitiveness choke points to solve

Working diagnosis:

1. **Temporal compression ceiling**  
   L4/L5 structural continuity is compressed into cell keys, recency surrogates, serialized rows, and advisor-side recomputation.

2. **Epoch asymmetry**  
   Epoch/recency is materially active, but too much of the useful signal appears to flow through compressed epoch state instead of true structural memory.

3. **Fallback blur**  
   Candidate-key fallback chains preserve availability but obscure the distinction between exact and degraded coverage.

4. **Rulebook deficit**  
   The production financial strategy/rule layer is not yet broad enough to compete with commercial advisor systems.

5. **Proof deficit**  
   Structural quality, live operational quality, and commercial competitiveness are not yet reported in one coherent proof model.

6. **Lost-edge uncertainty**  
   Pre-move strong performance may have depended on behaviors not preserved or not visible in the current system.

---

## 4. Lane A — Protect and deepen CP-0

### A1. Code-truth to spec gap matrix

**Purpose:** reconcile current production code-truth with the normative v2.4 spec.

**Build:**
- `current_l5_code_truth_to_spec_gap_latest.json`
- `current_l5_code_truth_to_spec_gap_latest.md`

**For each capability:**
- present in code?
- present in spec?
- target-only in spec?
- missing in spec?
- migration risk?
- production risk if changed?

**Must include:**
- refresh/oracle/runtime sync path
- policy learning / promotion gates
- runtime snapshot loading
- advisor decision recomputation
- fallback chains
- portfolio allocator behavior

---

### A2. Epoch decomposition and structural recency analysis

**Purpose:** identify which epoch components are actually carrying signal.

**Work:**
1. Complete the epoch decomposition microprobes.
2. Split epoch block into at minimum:
   - regime code,
   - structural recency (`steps_since_*`),
   - gap state,
   - company/news/catalyst epoch,
   - macro/sector sphere-of-impact epoch.
3. Measure each component’s contribution to:
   - action flip rate,
   - outcome-over-index,
   - mean excess,
   - fallback behavior.

**Outputs:**
- `epoch_component_importance_latest.json`
- `epoch_component_importance_latest.md`
- `epoch_registry_v1.json`

---

### A3. Persist decision provenance instead of recomputing everything at request time

**Purpose:** make advisor behavior traceable and reduce runtime ambiguity.

**Implement:**
- populate runtime decision provenance fields instead of leaving them null,
- persist exact selected key, selected fallback level, selected policy artifact/run id,
- persist stale/degraded reasoning fields,
- preserve request-time recomputation only as a controlled compatibility fallback.

**Outputs:**
- schema migration and runtime bridge update
- `runtime_decision_provenance_contract_latest.md`

---

### A4. Typed fallback ladder

**Purpose:** separate real coverage from degraded coverage.

**Implement fallback levels:**
- L0 exact structural key
- L1 exact core / relaxed suffix
- L2 exact regime+recency core / relaxed structural buckets
- L3 abstain/hold only
- L4 no recommendation / degraded mode

**Requirements:**
- persist selected level,
- expose level in recommendations and quality/admin reports,
- use fallback-adjusted metrics in promotion and competitiveness reporting.

**Outputs:**
- `fallback_ladder_specification_latest.md`
- runtime and admin API updates

---

### A5. Expand the competitive financial strategy / rulebook

**Purpose:** increase commercial usefulness without abandoning structural governance.

**Implement governed strategy families:**
- long-side accumulation and hold discipline,
- short-side / downside families,
- double-bottom / double-top / pivot / squeeze / crossover setup families,
- insider / ownership rules,
- company-specific news / catalyst rules,
- sector / macro / war / rates / build-cycle / commodity rules,
- survivability / margin / valuation / capital-preservation rules,
- explicit abstention / suppression logic.

**Deliverables:**
- controlled registries for:
  - strategies,
  - setups,
  - informational events,
  - sector/sphere coupling,
  - exclusion rules,
  - approved heuristics.

**Outputs:**
- `strategy_registry_v1.json`
- `setup_registry_v1.json`
- `information_event_registry_v1.json`
- `sector_sphere_coupling_registry_v1.json`
- `heuristics_registry_v1.json`

---

### A6. Upgrade promotion gates to optimize commercial quality

**Purpose:** stop rewarding improvements that look good only in narrow technical metrics.

**Add to current non-regression gates:**
- exact-key coverage floor,
- fallback-quality floor,
- strategy-family minimum quality,
- sector breadth sanity,
- degraded-mode frequency ceiling,
- provenance completeness floor,
- no-improvement-via-more-fallback rule.

**Outputs:**
- `promotion_gate_v2_spec.md`
- evaluator and admin quality updates

---

### A7. Build the three proof planes

**Purpose:** separate unlike evidence types.

**Implement reporting for:**
1. **Structural Quality Plane**
2. **Operational Quality Plane**
3. **Commercial Competitiveness Plane**

**Outputs:**
- `proof_plane_structural_latest.json`
- `proof_plane_operational_latest.json`
- `proof_plane_competitive_latest.json`
- unified admin/report surface

---

### A8. Lost-edge recovery audit

**Purpose:** recover the causal behavior that may have driven stronger pre-move results.

**Focus on:**
- snapshot selection and dedupe,
- quote/profile cache influence,
- recency / epoch behavior,
- policy-promotion thresholds,
- advisor degraded-mode behavior,
- runtime sync behavior,
- fallback chain behavior.

**Outputs:**
- `lost_edge_recovery_audit_latest.json`
- `lost_edge_recovery_interpretation_latest.md`

---

## 5. Lane B — Build CP-2 offline

### B1. Structural event tape sidecar

**Purpose:** stop forcing L5 to consume only serialized rows.

**Build:**
- `structural_event_tape_builder.py`
- `structural_event_tape_manifest_latest.json`

**Event classes must include:**
- gate open/close,
- resonance peak/trough/flip,
- collapse/instability warnings,
- negative-space onset/release,
- recency transitions,
- epoch activations/deactivations,
- approved domain-rule events,
- cross-core agreement/disagreement events.

---

### B2. CP-2 shared-state canary

**Purpose:** test thesis-faithful L5 with a shared structural memory.

**Build:**
- one shared state,
- explicit fast/mid/slow memory,
- event-driven updates only,
- one latent field,
- three terminal horizon heads (5/20/60).

**Variants:**
- sparse shared-state dynamical field,
- fixed reservoir + lightweight readout,
- selective state-space profile if needed.

**Outputs:**
- `cp2_shared_state_canary_latest.json`
- `cp2_state_trace_latest.json`
- `cp2_vs_cp0_gold_slice_latest.json`

---

### B3. Thesis conformance gate

**Purpose:** prove whether CP-2 is actually structurally temporal.

**Required tests:**
- ordered sequence vs shuffled / reversed / current-only,
- short/mid/long masking,
- negative-space removal,
- epoch removal,
- cross-core disagreement sensitivity,
- event-admission sensitivity.

**Outputs:**
- `cp2_temporal_conformance_latest.json`
- `cp2_multiscale_memory_ablation_latest.json`
- `cp2_conformance_verdict_latest.md`

---

## 6. Prioritization order (single coherent sequence)

### Immediate highest-ROI sequence

1. **A1 Code-truth to spec gap matrix**
2. **A2 Epoch decomposition and structural recency analysis**
3. **A3 Persist decision provenance**
4. **A4 Typed fallback ladder**
5. **A5 Expand competitive financial strategy/rulebook**
6. **A6 Upgrade promotion gates**
7. **A7 Build proof planes**
8. **A8 Lost-edge recovery audit**
9. **B1 Structural event tape sidecar**
10. **B2/B3 CP-2 canary and conformance gate**

This sequence supersedes the earlier confusing list combinations.

---

## 7. Deliverables to update alongside implementation

Update as controlled artifacts:
- `TFE Specification v2.4`
- `TFE Spec Internal Review v2.4`
- `AWS_RUNBOOK.md`
- `LOAD_DIRECTIVE_NEXT_CHAT.md`
- `TFE_TODO_LIST.md`
- controlled registries and proof-plane outputs listed above

---

## 8. Stop / Go criteria

### Stop if:
- a production change would reduce provenance or blur exact-vs-fallback semantics,
- a change increases fallback while claiming better quality,
- a change introduces undeclared heuristics,
- CP-2 experiments start to destabilize CP-0.

### Go if:
- provenance is strengthened,
- epoch sensitivity becomes explainable,
- fallback is typed and measurable,
- strategy/rulebook breadth improves,
- proof planes are coherent,
- CP-2 canary shows genuine structural-temporal benefit.

---

## 9. Final commercial decision rule

After Lane A hardening and Lane B canaries, run one artifact-backed benchmark matrix comparing:
- CP-0 production L5,
- best pragmatic hybrid,
- CP-2 canary,
- simple non-DSF baseline,
- standard ML baseline,
- external comparator on overlapping sample,
- SPY / buy-and-hold.

If TFE still does not materially outperform practical alternatives on artifact-backed results, classify this instantiation as:

**non-competitive**

This is a product decision, not a thesis decision.
