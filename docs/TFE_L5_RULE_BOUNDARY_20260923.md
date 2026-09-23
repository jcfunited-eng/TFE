# Full-field L5 rule boundary — 2026-09-23

The requested CH2/CH6 strategy is unfinished. This document records the exact remaining definition question, not a new strategy, mathematical impossibility claim, or claim that the entire repository was exhaustively searched.

Requested architecture: raw input to unchanged L0–L4; complete time-ordered tuple and peer context govern formation, persistence and collapse in L5. Current inspected selectors use scalar basin scores, normalized neighbor distances, condition ladders or compressed signatures. Conflict: yes. None is extended. Recommendations, screener and kernel remain protected. This investigation evaluates source definitions; it does not substitute a reduced decision model for the full field. The next item is to resolve the joint-field formation/collapse relationship before implementing a selector.

## Concrete definitions found

Joseph Forrester's `ADVANCED_LOCALIZED_THERMODYNAMICS___ASYMMETRIC_EXHAUSTION.pdf`, sections 2.1–2.4:

- Quiescence concerns change in displacement approaching zero within tolerance, rather than displacement having a particular sign.
- Compression duration determines potential energy proportionally.
- Ignition is expansion out of quiescence, with stated cognitive bounds.
- `tau_out = floor(tau_in / 3)`, starting at validated ignition.
- Exit is governed by `P_apex - 2*epsilon` or timer expiry.

The inspected text does not give the numerical tolerance, a causal calculation of the future apex, or the complete seven-field formation/collapse relationship. The timer formula alone does not supply those definitions. This does not show the physical framework impossible or authorize replacing it.

## Executable mismatches verified

- `web/scripts/execution/sentinel_monitor.mjs`, approximately 1521–1595: counts historical publication days with `D_k != 1`, rather than adjacent displacement differences. The timer exit is disabled. Publication days are also not automatically consecutive market observations.
- `tools/backtest_simulator.py`, `_compute_tau_out`: repeats the `D_k != 1` interpretation and skips absent historical observations.
- `tfe_5year_backtest.py`, approximately 360–370: sums gate spans where `D_k <= 0`. That is another distinct compression rule.

These implementations are not changed. Enabling or modifying one would not resolve the missing joint-field selection definition.

## Other source candidates inspected and not adopted

- `docs/TFE-CMD-L5-PHYSICS-NATIVE-STACK-WC-20260707-v1.md`: species classes, thresholds and median cycle durations; conflicts with the present no-buckets/no-means requirement.
- `PRIMITIVE_DIRECT_FIELD_STATE_CALC_DRAFT.md`: explicit weighted scalar states; the document itself does not establish its coefficients.
- `DSF_PRIMITIVE_FULL_FIELD_SORTABLE_V1.md`: scalar basin products and argmax; explicitly noncanonical.
- `TFE_Specification_Merged/ch06_l5_governance.tex`: structural event-tape design followed by weighted quality scores, fusion and local summaries; a specification is not executable serving evidence or authority to override the current requirement.
- `tools/ch6_confidence_floor_v3.py`: six exported instruments, missing M/C/P, majority signs, trailing medians and signature frequencies. Not full-tuple evaluation.
- `tools/vtvr_field_analog_engine_v2.py`: noncanonical side-kernel, block means and weighted scalar distances. Not the requested frozen-kernel path.
- `docs/L6_Topological_Constraint_Layer_Spec.tex`: repeats the apex expression; its effective-dimension construction is a separate reduced constraint model, not a causal full-tuple apex estimator.

## Clarification requested

What physical relationship among the complete tuple fields establishes formation and impending collapse? An equation or source-document identifier is enough; the agent will locate, implement and verify it. This asks for the missing physical definition, not developer work.

Reason for requesting clarification: AGENTS.md says, “If a requested feature cannot be mapped directly to the requested architecture, stop and say that direct mapping is missing instead of improvising.” It also forbids guessing and unapproved replacement mechanisms. Prior authorization to create new code does not determine an unspecified physical relationship.

No strategy code, protected source, Guala source or running process was changed in this investigation. No new WR/lift result is claimed.
