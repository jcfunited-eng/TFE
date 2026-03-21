# Tao Financial Engine (TFE)
# Implementation Plan v2.6
# Target Executor: GPT-5.3 Codex
# Date: 2026-03-10

---

# 1. Purpose

This document defines the **authoritative implementation roadmap** for the Tao Financial Engine (TFE).

The purpose of this plan is to move the system from its current operational state (CP-0) toward a more complete DSF-AI architecture while preserving the stability of the running application.

The plan prioritizes:

1. Eliminating operational blockers (stale data, publication mismatch)
2. Restoring structural correctness in L5 decision logic
3. Expanding rulebook competitiveness
4. Hardening runtime publication infrastructure
5. Enabling DSF-aligned temporal interpretation (recency and epoch)

The plan is explicitly **execution-oriented** and must remain aligned with the **code-truth system state**.

---

# 2. Execution Principles

The following constraints apply to all work executed under this plan.

## 2.1 Protect the running system

The following actions are prohibited unless explicitly approved:

- refresh
- oracle execution
- L5 policy retraining
- ranking changes
- allocator semantic changes
- quote-family activation

These restrictions ensure that development does not destabilize the production advisory environment.

---

## 2.2 Maintain deterministic provenance

Every decision path must remain traceable through:

- structural state generation
- snapshot materialization
- runtime publication
- policy lattice matching
- advisor surface output

---

## 2.3 Prefer bounded operations

Long-running jobs must be:

- chunked
- resumable
- observable
- checkpointed

Unbounded background jobs are not allowed.

---

## 2.4 Preserve publication consistency

User-visible data must always originate from a **single validated publication bundle**.

Readers must never mix:

- snapshot rows
- quote artifacts
- policy artifacts
- provenance artifacts

from different publication identities.

---

## 2.5 v2.6 Serving-Policy Hardening Adoption (Explicit Override)

Investor-facing reader behavior is explicitly hardened in v2.6:

- Recommendations: fail closed on stale, validation failure, missing publication IDs, quote-binding misalignment, or run mismatch.
- Portfolio: same fail-closed serving policy as Recommendations before allocator/benchmark outputs are built.
- Admin Command Deck: same canonical serving-policy state and reasons as investor readers.

This is an explicit v2.6 governance adoption override relative to older v2.5 strict-mode-off/degraded-serving language.

---

# 3. Completed Implementation Phases

The following phases are complete and must be considered the **current system baseline**.

---

## A3 — Provenance Persistence

Status: COMPLETE

Implemented capabilities:

- persisted decision provenance
- deterministic replay parity
- frozen-context decision verification

Result:

Decision provenance is no longer a competitiveness blocker.

---

## A4 — Typed Fallback Ladder

Status: COMPLETE

Delivered functionality:

- deterministic fallback classification
- persisted ladder level
- admin fallback breakdown reporting

Result:

Fallback semantics are fully governed and observable.

---

## A4.1 — Exact Match Recovery Audit

Status: COMPLETE

Findings:

Exact structural matches were previously unreachable due to lattice construction issues.

Primary root causes:

- stability bucket mismatch
- unreachable exact family path

---

## A4.2 — Exact-Path Alignment Adoption

Status: COMPLETE

Implemented anchor:

NO_ST_EXACT_FAMILY_KEEP_CD_PHASE_SPIDER_STRICT

Impact:

- restored large portion of exact structural matches
- zero decision drift during adoption validation

---

# 4. Rulebook Development Phases

---

## A5.1 — Rulebook Coverage Surface

Purpose:

Expose which strategy families are currently active.

Finding:

Production behavior dominated by:

- long-side accumulation discipline
- abstention / suppression

---

## A5.2 — Long-Side Decomposition

Result:

Long-side behavior decomposed into subfamilies:

- accumulation_core
- hold_discipline_core
- hold_only_no_add_discipline

---

## A5.3 — Subfamily Contract Definition

Contracts defined for:

- accumulation_core
- hold_discipline_core
- hold_only_no_add_discipline

Blocked families identified:

- valuation_protected_accumulation
- survivability_protected_accumulation
- margin_quality_discipline
- recency_sensitive_accumulation
- epoch_assisted_accumulation

---

## A5.4 — Field and Event Contracts

Purpose:

Identify data requirements for blocked strategy families.

Findings:

Quote-family fields exist but are blocked by **stale quote source**.

Structural recency and epoch require **runtime field transport**.

---

## A5.5 — Recency and Epoch Activation Readiness

Findings:

Structural recency contracts are ready but fields are not materialized.

Epoch contracts require:

- stable regime_code enum
- gap_state enum
- sidecar projection join

Conclusion:

Structural recency should be activated before epoch.

---

# 5. Active Development Lanes

Three work lanes remain active.

---

# Lane R — Structural Recency Materialization

Goal:

Add recency fields to snapshot rows and transport them into runtime evaluation.

Required additions:

- steps_since_* fields
- structural_recency_schema_version

Implementation targets:

- structural_recency_snapshot.py
- uf_mdg_snapshot.py

Verification outputs:

structural_recency_materialization_verification_latest.json  
structural_recency_materialization_verification_latest.md

---

# Lane Q — Quote Publication Alignment

Goal:

Ensure the live runtime quote artifact matches the active snapshot.

Known root causes:

- publication alignment failure
- refresh bookkeeping gap
- timestamp source mismatch (serving layer)

Resolution strategy:

1. chunked quote publisher
2. publication identity stamping
3. runtime sync verification

Completion criteria:

snapshot_publication_id == quote_publication_id  
freshness_within_SLA == true

---

# Lane E — Epoch System Implementation

Goal:

Implement transport and join semantics for epoch state.

Required work:

- regime_code enum
- gap_state enum
- epoch_schema_version
- sidecar projection join

Epoch activation remains secondary to structural recency.

---

# 6. Publication Architecture Hardening

To prevent future stale-data incidents the runtime architecture must shift to a **publication-consistent serving model**.

Key components:

1. publication registry
2. immutable artifacts
3. active publication pointer
4. activation gate
5. reader hardening

Readers must consume data exclusively from the active publication.

---

# 7. Operational Guarantees

The system must guarantee:

- deterministic provenance
- artifact lineage
- freshness SLA enforcement
- bounded runtime jobs
- resumable publishers
- auditable decision paths

---

# 8. Immediate Execution Order

The next execution steps must occur in this order.

1. Live quote publication alignment verification
2. Structural recency materialization verification
3. Structural recency activation readiness
4. Epoch transport implementation
5. Publication architecture hardening

---

# 9. Explicit Non-Goals

The following remain disabled until explicitly approved:

- refresh execution
- oracle optimizer
- L5 policy retraining
- quote-family activation
- strategy activation
- ranking changes
- portfolio allocator changes

---

# 10. Expected Deliverables

After completion of the next phase the following artifacts must exist.

Structural Recency

- structural_recency_materialization_verification_latest.json
- structural_recency_materialization_verification_latest.md

Quote Publication

- live_quote_publish_run_latest.json
- live_quote_publication_alignment_verification_latest.json

Epoch System

- epoch_state_realization_latest.json
- epoch_state_realization_latest.md

Publication Infrastructure

- publication_registry_contract_latest.md
- publication_activation_gate_latest.md

---

# 11. Final Guidance

The correct development doctrine for TFE v2.6 is:

1. protect production stability
2. resolve operational blockers
3. activate structural recency
4. implement epoch transport
5. harden publication infrastructure

Broad architectural rewrites must not occur until these steps are complete.
