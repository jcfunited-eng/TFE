# TFE 5.3 Implementation Plan v2.5

**Status:** controlled implementation plan aligned to TFE Specification v2.5  
**Scope:** current TFE instantiation only  
**Goal:** increase competitiveness without destabilizing CP-0 while preserving the distinction between current production behavior and thesis-faithful future L5 behavior.

---

## 1. Current state snapshot (order preserved)

Completed / adopted:
- **A1** code-truth to spec gap matrix = complete
- **A3** decision provenance persistence = complete / green
- **A4** typed fallback ladder = complete / green
- **A4.1** exact-match recovery audit = complete
- **A4.2** exact-path alignment = adopted in CP-0
- **A5.1** admin/internal rulebook coverage surface = complete
- **A5.2** long-side decomposition = complete
- **A5.3** long-side subfamily contract readiness = complete
- **A5.4Q** quote-family field contracts = complete, but source freshness/publication alignment remain blocked
- **A5.4S** structural recency and epoch contract definitions = complete
- **A5.5R/E** activation-readiness artifacts = complete

Not complete / still blocked:
- **Structural recency activation** blocked by missing snapshot materialization fields
- **Epoch-assisted activation** blocked by unstable numeric `regime_code`, missing `gap_state` enum, and missing sidecar projection join
- **Quote-family activation** blocked by quote freshness / publication alignment
- **Lane Q stale-data remediation** approved conceptually, but no completed result artifact has yet been incorporated into this plan revision

Non-goals for this plan revision:
- no new full-universe benchmark run
- no h20/h60 continuation from the stopped large run
- no broad production behavior rewrite
- no conflation of CP-0 with CP-2

---

## 2. Immediate implementation priority stack

### P1. Structural recency realization (highest local ROI)
Implement the missing snapshot/runtime fields needed to activate the already-defined recency-assisted family.

Build:
- `steps_since_*` member registry in code truth
- snapshot materialization wiring for those fields
- runtime transport wiring
- admin/internal activation-readiness verification

Required outputs:
- `structural_recency_member_registry_latest.json`
- `structural_recency_snapshot_materialization_verification_latest.json`
- `structural_recency_runtime_transport_verification_latest.json`
- `structural_recency_admin_activation_readiness_latest.json`

Acceptance gates:
- snapshot rows contain the declared recency members
- runtime transport preserves those members without null inflation
- no ranking changes
- no allocator changes
- activation remains admin/internal first

### P2. Quote freshness / publication alignment remediation (parallel lane)
Run the stale quote/freshness root-cause and remediation lane in parallel with P1.

Build:
- `quote_freshness_root_cause_latest.json`
- `quote_publication_alignment_latest.json`
- `quote_freshness_remediation_plan_latest.md`
- `quote_freshness_fix_verification_latest.json` (if a safe low-risk fix is implemented)

Goals:
- determine whether the blocker is producer, scheduler, publication binding, runtime read path, or timestamp/threshold logic
- restore publication alignment with the active snapshot
- restore freshness within the validation window
- keep quote-family activation blocked until these are green

### P3. Epoch readiness realization (after P1)
Only after structural recency is materially wired should epoch-assisted work proceed.

Build:
- stable `regime_code` contract
- `gap_state` enum
- sidecar projection join contract and implementation
- admin/internal readiness for epoch-assisted family

Outputs:
- `epoch_state_enum_registry_latest.json`
- `epoch_projection_join_impl_latest.md`
- `epoch_admin_activation_readiness_latest.json`

---

## 3. CP-0 protection rules

1. No production ranking change unless explicitly approved.
2. No portfolio allocator semantic change unless explicitly approved.
3. Reader strict mode remains off unless separately approved.
4. Quote-family activation remains blocked until freshness/publication alignment are fixed.
5. Strategy-family activation remains admin/internal first.
6. Every behavior-changing step must preserve exact/fallback/provenance observability.

---

## 4. Rulebook build sequence

### Stage R1 — dominant family hardening
Continue improving the already-dominant long-side family only after its blocked dependencies are satisfied.

Current ready family contracts:
- `accumulation_core`
- `hold_discipline_core`
- `hold_only_no_add_discipline`

Current blocked family contracts:
- `valuation_protected_accumulation` (quote freshness blocked)
- `survivability_capital_preservation_protected_accumulation` (quote freshness blocked)
- `margin_quality_discipline` (quote freshness blocked)
- `recency_sensitive_accumulation` (missing recency materialization)
- `epoch_assisted_accumulation` (missing stable epoch transport)

### Stage R2 — activation-readiness, not activation-by-default
Each family must declare:
- required ladder level
- hard-block conditions
- explanation fields
- proof-plane placement
- activation scope (admin-only / internal / production)

---

## 5. Competitiveness program

The competitiveness problem is currently understood as a combination of:
1. compressed temporal representation in CP-0
2. narrow active rulebook breadth
3. quote freshness/publication misalignment
4. missing structural recency transport
5. missing epoch-state transport
6. proof-plane immaturity

Accordingly, the competitiveness work order is:
1. structural recency realization
2. quote freshness remediation in parallel
3. epoch realization
4. quote-family activation readiness after freshness is fixed
5. promotion-gate upgrade
6. three proof-plane upgrade
7. CP-2 offline canary work

---

## 6. What not to do next

- Do not run another giant benchmark job first.
- Do not activate quote families while quote freshness is stale.
- Do not activate epoch-assisted family before recency work and epoch join semantics are implemented.
- Do not treat CP-0 current success as proof of CP-2.
- Do not rewrite production around CP-2 ideas before CP-0 competitiveness chokers are cleared.

---

## 7. Next explicit tasks

### Task N1
**Structural recency realization**

### Task N2
**Quote freshness root-cause + remediation**

### Task N3
**Epoch enum + sidecar projection join**

### Task N4
**Admin/internal activation readiness for recency-assisted family**

### Task N5
**Admin/internal activation readiness for quote families once freshness is green**

---

## 8. Exit criteria for this plan revision

This v2.5 plan is considered materially advanced when:
- structural recency fields are present and transported end-to-end
- quote publication alignment is restored or conclusively root-caused
- epoch state contracts are no longer blocked by undefined enums / absent join
- at least one blocked competitive family moves to admin/internal activation readiness

At that point, a v2.6 plan should be issued.
