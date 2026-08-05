# DSF Primitive Full-Field Sortable V1

This file defines an audit-only sortable DSF full-field primitive candidate.

It is not canonical.
It does not modify runtime.
It does not use transport or helper fields.

Approved primitive field surface:
- `barCount`
- `S_UF`
- `R_UF`
- `D_k`
- `M_k`
- `R_rev_k`
- `U_star_k`
- `C_k`
- `P_k`
- `B_k`

Range handling:
- `D_k` is read directly
- `R_rev_k` is read directly
- `B_k` is read directly
- `M_k` is clamped only as approved:
  - `M_hat = max(-1.0, min(1.0, M_k))`

Tie rule:
- `TIE_EPS = 1e-12`
- absolute tolerance only
- no relative tolerance
- no rounding rule
- any exact tie or numerical near-tie goes to `Hold`

Interpretation:
- support and resonance are read first through `S_UF - U_star_k` and `R_UF - U_star_k`
- `covered_core` is double-covered viable reserve
- `covered_edge` is one-sided live or contested reserve
- `rupture` is double-uncovered break geometry
- `D_k` and `M_k` define forward versus bending geometry
- `R_rev_k` is first-class break geometry
- `C_k` and `P_k` are bounded load and do not create action by themselves
- `B_k` is used in v1 only relationally through `carry_break` because standalone `B_k` semantics remained ambiguous in the prior audit
- this candidate exists only to test whether the primitive can sort rows into `Accumulate`, `Hold`, and `Avoid` on the approved fixed snapshot

Closed-form candidate:

Support / resonance read:
- `s = S_UF - U_star_k`
- `r = R_UF - U_star_k`

Coverage geometry:
- `covered_core = max(min(s, r), 0.0)`
- `covered_edge = max(max(s, r), 0.0) - covered_core`
- `rupture = max(-max(s, r), 0.0)`

Direction / bend:
- `D_pos = max(D_k, 0.0)`
- `D_neg = max(-D_k, 0.0)`
- `M_cont = (1.0 + M_hat) / 2.0`
- `M_bend = (1.0 - M_hat) / 2.0`

Reversal / load / carry:
- `rev = R_rev_k`
- `load = (C_k + P_k) / (1.0 + C_k + P_k)`
- `carry_mag = -B_k`

Relational motion terms:
- `forward_agreement = min(D_pos, M_cont)`
- `break_seed = max(rev, min(D_neg, M_bend))`
- `carry_break = carry_mag * max(rev, D_neg, M_bend)`
- `break_agreement = max(break_seed, carry_break)`

Primitive basin values:
- `Accumulate_basin = covered_core * forward_agreement * (1.0 - break_agreement) * (1.0 - load)`
- `Hold_basin = covered_edge * (1.0 - break_agreement) + covered_core * ((1.0 - forward_agreement) * (1.0 - break_agreement) + forward_agreement * load)`
- `Avoid_basin = rupture + (covered_core + covered_edge) * break_agreement`

Decision:
- `best = max(Accumulate_basin, Hold_basin, Avoid_basin)`
- `near_winners = all basin values where best - basin_value <= 1e-12`
- if at least two basin values are near-winners:
  - `final_decision = Hold`
- otherwise:
  - unique argmax of:
    - `Accumulate_basin -> Accumulate`
    - `Hold_basin -> Hold`
    - `Avoid_basin -> Avoid`

Audit aggregation notes:
- geometry bucket counts are descriptive only
- they do not override the primitive decision
- `covered_forward`, `covered_burdened`, and `covered_break` are assigned only inside covered-core rows by comparing the covered-core basin components
- `one_sided_hold` and `one_sided_break` are assigned only inside covered-edge rows by comparing the edge hold and edge break components
- `rupture` is assigned when `rupture > 0`

Required audit outputs come from:
- `/workspaces/Tao_Financial_Engine/tools/run_dsf_full_field_sortable_v1.py`
