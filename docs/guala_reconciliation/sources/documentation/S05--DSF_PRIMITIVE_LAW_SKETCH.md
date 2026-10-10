# DSF Primitive Law Sketch

Purpose:
- state a mathematical sketch for primitive DSF interpretation
- keep the law separate from the correction contract
- replace fixed heuristic coefficients with symbolic parameters
- constrain those parameters from primitive acceptance geometry instead of tuning by feel
- recast the seam problem as a smooth function-of-coverage problem rather than premature coefficient selection

Status:
- draft

Scope:
- primitive surface only
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

This document is:
- a primitive law sketch
- equation-level
- reduced to the approved primitive surface
- a symbolic candidate law, not a finished derivation

This document is not:
- full governed L5
- CP-0 production policy
- a final oracle
- proof that the current coefficients are derived from DSF

## 1. Primitive Coordinates

Let:

- `s = S_UF`
- `r = R_UF`
- `u = U_star_k`
- `d = D_k`
- `m = M_k`
- `q = B_k`
- `rev = R_rev_k`
- `c = C_k`
- `p = P_k`

Define the reserve margins:

- `s_res = s - u`
- `r_res = r - u`

Define weakest reserve coverage:

- `w = min(s_res, r_res)`

Define reserve asymmetry:

- `a = |s - r|`

Define the second coverage coordinate:

- `w_2 = w + a`

Interpretation:
- `w` is the weakest-reserve coverage relation
- `w_2` tells whether the stronger side still carries positive reserve
- `a` is reserve imbalance, not a decision authority by itself

## 2. Trajectory Geometry

The trajectory side should be read as one coupled geometry, not as separate votes.

Required meaning:
- positive direction alone is not enough
- reversal remains special and suppresses continuation strongly
- contested positive motion is allowed
- rupture is not just negative direction; it is adverse motion plus topology break or exhaustion agreement

So the trajectory law must distinguish:
- coherent forward motion
- contested but still admissible motion
- rupture-like motion

## 3. Load Geometry

Conflict and persistence belong to bounded dissipation, not hard vetoes.

Required meaning:
- higher load reduces admissibility
- load alone does not decide the label
- load modifies the meaning of coverage and trajectory

## 4. Basin Coordinates

This primitive sketch uses three continuous coordinates:

Coverage topology:
- governed by `(w, w_2)`

Trajectory admissibility:
- governed by forward, contested, and rupture geometry together with `rev`

Load:
- governed by bounded conflict and persistence dissipation

The law should remain smooth in these coordinates.

## 5. Basin Meaning

`Accumulate`
- coverage remains viable
- forward trajectory is admissible
- rupture is not governing
- load does not invalidate the state

`Hold`
- viable stillness, or
- contested but non-collapsing motion, or
- near-boundary coverage with insufficient rupture agreement

`Avoid`
- coverage failure with sufficient rupture/load agreement, or
- strongly adverse rupture geometry

## 6. Required Continuity

The law must not behave as a hard sign gate on `w`.

Specifically:
- `w > 0` may support `Accumulate`
- `w = 0` may support `Hold`
- small negative `w` in one-sided constructive states must not force `Avoid` by sign alone

So the transition near `w = 0` must depend on:
- deficit magnitude
- rupture agreement
- load agreement

not on sign alone

## 7. One-Sided Versus Double-Sided Failure

One-sided failure:
- `w < 0`
- `w_2 > 0`

Double-sided failure:
- `w < 0`
- `w_2 <= 0`

Required meaning:
- double-sided rupture-like states must remain able to land in `Avoid`
- one-sided constructive states must not be treated as equivalent to double-sided rupture by default

## 8. Mathematical Shape Requirements

The primitive law should satisfy these shape requirements:

- continuity near the weak-coverage edge
- monotone worsening under stronger double-sided failure
- strong suppression under reversal-supported rupture
- bounded load influence
- no single-field decision authority

The law must not be:
- a threshold ladder
- a weighted scorecard acting as hidden authority
- a bucket override table

Additional constructive requirement:
- strong covered constructive, low-load, non-reversal states must prefer `Accumulate` over `Hold`

## 9. Honest State Of Coefficients

The current runtime coefficients such as `0.5` and `0.75` are not yet derived DSF constants.

They are currently:
- phenomenological coefficients
- meaningful in intended geometry
- not yet principled by derivation

So this sketch promotes them to symbols and now goes one step further:

- the seam problem should be treated as identification of a smooth function envelope
- not selection of one coefficient point too early

## 10. Acceptance Boundary

This sketch is constrained by:
- [DSF_PRIMITIVE_INTERPRETATION_RECOVERY.md](/workspaces/Tao_Financial_Engine/DSF_PRIMITIVE_INTERPRETATION_RECOVERY.md)

That contract requires:
- preserve genuine collapse
- preserve constructive viability
- correct the narrow one-sided constructive defect
- forbid heuristic drift

## 11. Closed-Form Symbolic Appendix

This appendix defines one symbolic primitive law family on the approved surface.

### 11.1 Coverage

Define:

- `pos(x) = max(x, 0)`
- `neg(x) = max(-x, 0)`
- `edge_support = pos(w_2) - pos(w)`
- `double_deficit = neg(w_2)`
- `edge_window = 1 / (1 + pos(w) + edge_support)`

Define a seam response on the covered side:

- `g(w)` for `w >= 0`

Required seam-response meaning:
- `g(w)` is smooth
- `g(w)` is monotone nonincreasing on the covered side
- `g(0)` is high enough to preserve seam-side `Hold`
- `g(w)` decays fast enough so covered constructive states can release into `Accumulate`

This seam response is the more fundamental object.

A parametric representation is optional and secondary.

If a parametric family is needed later, one admissible family is:

- `g(w) = theta_0 + theta_1 / (1 + lambda * w)`

with:
- `theta_0 >= 0`
- `theta_1 >= 0`
- `lambda > 0`

But the mathematical target is the seam response itself, not the coefficient triple.

Define symbolic coverage coordinates:

- `cov_acc = pos(w) + alpha * edge_support`
- `cov_hold = (beta * pos(w) + g(pos(w)) * edge_support) * edge_window`
- `cov_avoid = neg(w) * (1 + kappa * double_deficit)`

where:
- `alpha > 0`
- `beta >= 0`
- `kappa >= 0`

Required meaning:
- coverage remains smooth through `w = 0`
- one-sided failure does not collapse instantly into the same geometry as double-sided failure
- the edge contribution to `Hold` can stay available at and below zero weak coverage
- that same edge contribution can decay on the covered side
- double-sided failure worsens faster than one-sided failure when `kappa > 0`

### 11.2 Trajectory

Define:

- `d_pos = pos(d)`
- `d_neg = pos(-d)`
- `m_pos = pos(m)`
- `m_neg = pos(-m)`
- `q_pos = pos(q)`
- `q_neg = pos(-q)`

Define symbolic trajectory coordinates:

- `traj_forward = (d_pos + mu_m * m_pos + mu_q * q_pos) / Z_f`
- `traj_contested = rho_c * (d_pos + nu_m * (1 - m_neg) + nu_q * (1 - q_neg)) / Z_c * (1 - rho_r * rev)`
- `traj_rupture = d_neg + xi_m * m_neg + xi_q * q_neg + xi_r * rev`

where:
- `mu_m, mu_q > 0`
- `nu_m, nu_q > 0`
- `rho_c > 0`
- `0 < rho_r <= 1`
- `xi_m, xi_q, xi_r > 0`
- `Z_f, Z_c > 0`

Required meaning:
- contested positive motion stays available
- contested motion is weaker than clean forward motion in the same strong constructive state
- reversal enters rupture directly and continuation adversely
- strong negative carry matters, but mild carry damage does not dominate by itself

### 11.3 Load

Define bounded drags:

- `conflict_drag = c / (1 + c)`
- `persistence_drag = p / (1 + p)`
- `conflict_calm = 1 - conflict_drag`
- `persistence_calm = 1 - persistence_drag`

Define total load:

- `load = omega_c * conflict_drag + omega_p * persistence_drag`

where:
- `omega_c >= 0`
- `omega_p >= 0`
- `omega_c + omega_p = 1`

Required meaning:
- load is bounded in `[0, 1)`
- load modifies admissibility
- load alone does not decide the label

### 11.4 Basin Tendencies

Define symbolic basin tendencies:

- `accumulate_tendency = cov_acc * traj_forward * (1 - rev) * (1 - psi_a * load)`
- `hold_tendency = cov_hold * max(traj_contested - psi_h * traj_rupture, 0) * (eta + (1 - eta) * persistence_calm)`
- `avoid_tendency = cov_avoid * (1 + phi_r * traj_rupture) * (1 + phi_l * load)`

where:
- `0 <= psi_a < 1`
- `psi_h >= 0`
- `0 <= eta <= 1`
- `phi_r >= 0`
- `phi_l >= 0`

Required meaning:
- `Accumulate` comes from viable coverage plus admissible forward motion
- `Hold` remains available near the coverage edge if contested motion survives and rupture is not governing
- `Avoid` strengthens under failed coverage with rupture/load agreement

### 11.5 Label Selection Rule

Define:

- `decision = argmax(accumulate_tendency, hold_tendency, avoid_tendency)`

Tie rule:
- if two or more basin tendencies are exactly equal at the maximum, choose `Hold`

Required meaning:
- the law resolves true ambiguity conservatively
- exact zero weak coverage can remain in the `Hold` basin
- the decision rule is explicit, not left to implementation taste

## 12. Acceptance Constraints On Parameters

The symbolic parameters must satisfy these invariant constraints.

### 12.1 Covered Constructive Viability

For strong covered constructive, low-load, non-reversal states:

- `accumulate_tendency > hold_tendency`
- `accumulate_tendency > avoid_tendency`

### 12.2 Exact Zero

At exact zero weak coverage with no decisive rupture:

- `Hold` may remain maximal
- `Avoid` must not win by sign alone

### 12.3 One-Sided Negative Edge

For one-sided constructive states with:

- `w < 0`
- `w_2 > 0`
- `d >= 0`
- `rev = 0`
- mild carry damage

the parameter region must allow:

- `hold_tendency > 0`
- or `accumulate_tendency > 0`

and must forbid:

- `avoid_tendency` winning by sign alone when deficit magnitude, rupture, and load are insufficient

### 12.4 Double-Sided Rupture Protection

For double-sided rupture-like states:

- `w < 0`
- `w_2 <= 0`
- adverse motion and/or reversal agreement

the parameter region must preserve:

- `avoid_tendency > hold_tendency`
- `avoid_tendency > accumulate_tendency`

### 12.5 Positive-Side Seam Release

For genuine one-sided covered states with:

- `w > 0`
- `w_2 > 0`
- constructive motion
- no governing rupture

the parameter region must ensure:

- `Hold` does not remain dominant arbitrarily deep into the covered side
- `Accumulate` eventually overtakes `Hold` as positive coverage strengthens

## 13. Local Seam-Derived Feasible Region

This section constrains the seam response from the corrected seam probe:

- [dsf_primitive_seam_continuity_positive_w2_20260320T_latest.json](/workspaces/Tao_Financial_Engine/backups/runtime/dsf_primitive_seam_continuity_positive_w2_20260320T_latest.json)

This is a local derivation only.

It holds:
- near the one-sided seam
- under the current trajectory/load subfamily
- with a strong reserve of approximately `0.04`
- not as a full global solution for all primitive states

If a parametric family is used later, define:

- `gamma_0 = g(0)`
- `g(0.02)`
- `g(0.03)`

These are the identifiable local seam-response values from the seam probe.

The probe does not separately identify:
- `theta_0`
- `theta_1`
- `lambda`

It identifies seam-shape values.

So the seam geometry is seeing:
- the shape of `g(w)`

not:
- the internal decomposition of one parametric family

### 13.1 Zero-Seam Hold Requirement

To keep `Hold` available at the exact seam, the seam response must satisfy:

- `gamma_0 >= 0.65899 * alpha` in the mild-carry high-load seam slice
- `gamma_0 >= 0.63555 * alpha` in the zero-carry high-load seam slice
- `gamma_0 >= 0.71891 * alpha` in the mild-carry low-load seam slice

So the strongest local zero-seam lower bound is:

- `gamma_0 >= max(0.64820, 0.71891 * alpha)`

The constant `0.64820` comes from requiring `Hold` to remain above `Avoid` at the small negative one-sided seam in the mild-carry high-load slice.

### 13.2 Small Negative One-Sided Protection

For the local one-sided seam with `w = -0.01` and `w_2 = 0.04`, the seam response must keep positive-basin support above `Avoid`.

The strongest local lower bound from the corrected probe is:

- `gamma_0 > 0.64820`

This means:
- the seam-side hold response cannot collapse near zero on the negative one-sided side

### 13.3 Positive-Side Release By `w = 0.02`

To make `Accumulate` overtake `Hold` by a local one-sided covered state with `w = 0.02` and `w_2 = 0.04`, the corrected probe implies:

- `0.34375 * (1 + alpha) > 0.52163 * (beta + g(0.02))` in the mild-carry high-load seam slice
- `0.34375 * (1 + alpha) > 0.54087 * (beta + g(0.02))` in the zero-carry high-load seam slice
- `0.5 * (1 + alpha) > 0.69550 * (beta + g(0.02))` in the mild-carry low-load seam slice

So the tightest local covered-side release bound is:

- `g(0.02) < 0.63555 * (1 + alpha) - beta`

### 13.4 Positive-Side Release By `w = 0.03`

For the weaker release requirement that `Accumulate` overtake `Hold` by `w = 0.03` and `w_2 = 0.04`, the corrected probe implies:

- `0.34375 * (3 + alpha) > 0.52163 * (3 * beta + g(0.03))` in the mild-carry high-load seam slice
- `0.34375 * (3 + alpha) > 0.54087 * (3 * beta + g(0.03))` in the zero-carry high-load seam slice
- `0.5 * (3 + alpha) > 0.69550 * (3 * beta + g(0.03))` in the mild-carry low-load seam slice

So the tightest local `w = 0.03` release bound is:

- `g(0.03) < 0.63555 * (3 + alpha) - 3 * beta`

### 13.5 Local Design Meaning

These local inequalities say:

- `g(0)` must stay high enough to preserve `Hold` at and just below the one-sided seam
- but `g(0.02)` must decay enough on the covered side to let `Accumulate` emerge earlier than it does now

So the seam geometry needs:

- a strong enough zero-side seam response
- a fast enough covered-side decay

not:
- a blanket decrease of all hold weight
- or a blanket increase of all accumulate weight

## 14. Local Seam-Response Envelope

The next source of truth is not a parametric family.

The next source of truth is the local admissible envelope for:

- `g : [0, 0.03] -> R_{>=0}`

subject to:

- smoothness
- monotone nonincreasing covered-side behavior
- the local seam inequalities above

So the local envelope is the set of seam responses satisfying:

- `g(0) >= max(0.64820, 0.71891 * alpha)`
- `g(0.02) < 0.63555 * (1 + alpha) - beta`
- `g(0.03) < 0.63555 * (3 + alpha) - 3 * beta`
- `g(0) >= g(0.02) >= g(0.03) >= 0`

This yields immediate local existence conditions:

- `0.63555 * (1 + alpha) - beta > 0`
- `0.63555 * (3 + alpha) - 3 * beta > 0`

And if one wants a nonempty locally monotone envelope with visible release by `w = 0.02`, then a sufficient local compatibility condition is:

- `max(0.64820, 0.71891 * alpha) > 0.63555 * (1 + alpha) - beta`

because then some positive decay from `0` to `0.02` is required rather than optional

The practical meaning is:
- the seam-response envelope is anchored from below at zero
- capped from above at `0.02` and `0.03`
- and forced to decline across the covered seam neighborhood

This is the real local object identified by the seam derivation.

## 15. One Explicit Local Target Shape

This section locks one explicit local target shape derived from:

- the local envelope
- the current runtime seam comparison in [dsf_primitive_runtime_vs_seam_envelope_20260320T_latest.json](/workspaces/Tao_Financial_Engine/backups/runtime/dsf_primitive_runtime_vs_seam_envelope_20260320T_latest.json)

It is not the final law.

It is the local target the next seam rewrite should approximate before any broader claim is made.

For the current runtime comparison, use:

- `alpha = 0.5`
- `beta = 0.5`
- `g_runtime(w) = 0.5 + 0.25 / (1 + 16 w)`

Then the local envelope gives:

- `g(0) >= 0.64820`
- `g(0.02) < 0.453325`
- `g(0.03) < 0.724425`

And the runtime comparison shows:

- `g_runtime(0) = 0.75`
- `g_runtime(0.02) = 0.689394`
- `g_runtime(0.03) = 0.668919`

So the local target should:

- keep the seam-side strength already present at zero
- project the covered-side seam response down to the admissible band by `w = 0.02`
- stay monotone nonincreasing through `w = 0.03`

The minimal local projection target is therefore:

- `G0* = 0.75`
- `G2* = 0.453325^-`
- `G3* = G2*`

where:
- `0.453325^-` means any value arbitrarily close below `0.453325`

Interpretation:
- keep the current zero-side seam strength
- enforce the tight covered-side release bound at `0.02`
- prevent the response from rising again by `0.03`

One admissible local smooth target is any `C^1` monotone interpolation on `[0, 0.03]` through:

- `(0, 0.75)`
- `(0.02, 0.453325^-)`
- `(0.03, 0.453325^-)`

with nonpositive slope everywhere.

This is the cleanest local target now available because:
- it is derived from the envelope
- it incorporates the current runtime comparison directly
- it does not require choosing a global parametric family

## 16. Next Mathematical Target

The next mathematical target is not:
- choose a candidate family casually
- pick one coefficient point from the local feasible region

The next mathematical target is:
- compare the current runtime seam response against the locked local target shape above

Concretely:
- use the target knots `(0, 0.75)`, `(0.02, 0.453325^-)`, `(0.03, 0.453325^-)`
- measure how far the current runtime seam response sits above that target on the covered side
- then rewrite only the seam component of the runtime toward that target

Only after that:
- ask whether a simple parametric form reproduces the target and broader envelope

So the source of truth should be:
- the local seam-response envelope and the locked local target shape

not:
- the chosen parametric family

## 17. Honest Boundary

This sketch is still reduced.

It does not yet specify:
- a final proof that this symbolic law family is the right primitive law
- a solved global parameter derivation
- a global seam-response envelope
- full governed L5 semantics
- production policy behavior
- real-world occupancy across the wider universe

It now states:
- a symbolic primitive law family
- the geometry the runtime should try to realize
- the invariant constraints that should govern any parameter choice
- a local seam-derived feasible region for the seam response itself
- one locked local target shape for the current seam rewrite
