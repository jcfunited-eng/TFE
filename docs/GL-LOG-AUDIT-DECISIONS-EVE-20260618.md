# GL-LOG-AUDIT-DECISIONS-EVE-20260618

Audit decisions log for findings from GL-RPT-ML-CONTAMINATION-AUDIT-EVE-20260618-07.
Each entry records Joe's adjudication and the implementing brief.

---

## B3 — `homeostasis_pull` (assemblage.py) — REMOVED

**Finding:** Drifts mode_bank vectors back toward random initial state at rate 0.001/tick. Named "synaptic scaling" but does the opposite of what biological synaptic scaling does. Erodes ALL reinforcement uniformly.

**Joe's adjudication:** REMOVE. Approved.

**Implementing brief:** GL-CMD-REMOVE-HOMEOSTATIC-DECAY-EVE-20260618-20

**Commit:** (this commit)

---

## B4 — `decay_modes` (assemblage.py) — REMOVED

**Finding:** Drags mode_strength toward 1.0 baseline at rate 0.001/tick. Above-baseline learning weakens; below-baseline strengths recover up. Homogenization, not biologically motivated decay.

**Joe's adjudication:** REMOVE. Approved.

**Implementing brief:** GL-CMD-REMOVE-HOMEOSTATIC-DECAY-EVE-20260618-20

**Commit:** (this commit)

---

## B7 — `snapshot_initial_modes` / `_initial_mode_bank` (assemblage.py) — REMOVED

**Finding:** Only purpose was populating `_initial_mode_bank` for B3's homeostasis_pull. Orphan once B3 is removed.

**Joe's adjudication:** REMOVE (orphan of B3). Approved.

**Implementing brief:** GL-CMD-REMOVE-HOMEOSTATIC-DECAY-EVE-20260618-20

**Commit:** (this commit)

---

## Remaining findings (NOT addressed in this brief)

- **B1** (gamma self-evolution block) — separate Joe call pending
- **B2** (`gamma_homeostasis`) — separate Joe call pending
- **A1-A4, C1-C5, D1-D6, E, F1-F4, G1-G3** — per-finding approval required

---

— Eve/c1, 2026-06-19
