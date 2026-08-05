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

## B1 — `GAMMA_DRIFT` + drift-toward-default in self-evo (assemblage.py) — REMOVED

**Finding:** Self-evolution block adds `drift = (GAMMA_DEFAULTS[k] - sec.gamma[k]) * GAMMA_DRIFT` to every gamma update. This pulls gamma values back toward hard-coded defaults, preventing genuine field-shape accumulation from experience.

**Joe's adjudication:** REMOVE. Approved.

**Implementing brief:** GL-CMD-REMOVE-GAMMA-ANTI-ADAPTATION-EVE-20260619-25

---

## B2 — `gamma_homeostasis` + `_initial_gamma` (assemblage.py) — REMOVED

**Finding:** `gamma_homeostasis(rate=0.001)` drifts gamma toward `_initial_gamma` snapshot every 20 ticks. Same `(1-rate)*x + rate*initial_x` anti-learning pattern as B3.

**Joe's adjudication:** REMOVE. Approved.

**Implementing brief:** GL-CMD-REMOVE-GAMMA-ANTI-ADAPTATION-EVE-20260619-25

---

## Remaining findings (NOT addressed)

- **A1-A4, C1-C5, D1-D6, E, F1-F4, G1-G3** — per-finding approval required

---

— Eve/c1, 2026-06-19
