# DSF Primitive Full-Field Sortable V3 Preview

This file records the audit-only DSF full-field sortable v3 preview.

It is not canonical.
It does not modify runtime.
It does not use transport, helper signals, price, volume, or external metadata.

Approved primitive field surface:
- `S_UF`
- `R_UF`
- `D_k`
- `M_k`
- `R_rev_k`
- `U_star_k`
- `C_k`
- `P_k`
- `B_k`
- `bar_count` only as passive row metadata

Approved tie rule:
- `TIE_EPS = 1e-12`
- absolute tolerance only
- no relative tolerance
- no rounding heuristic
- if two or more basins are within `TIE_EPS` of the max, decision = `Hold`

Approved preview formula:

`M_hat = max(-1.0, min(1.0, M_k))`

`s = S_UF - U_star_k`

`r = R_UF - U_star_k`

`core = min(max(s, 0.0), max(r, 0.0))`

`edge = max(max(s, 0.0), max(r, 0.0)) - core`

`live = core + beta * edge`

`contested = (1.0 - beta) * edge`

`balance = core / (core + edge + 1e-12)`

`rupture = max(-max(s, r), 0.0)`

`D_nonadverse = (1.0 + D_k) / 2.0`

`D_adverse = max(-D_k, 0.0)`

`M_continue = (1.0 + M_hat) / 2.0`

`M_bend = (1.0 - M_hat) / 2.0`

`motion = (motion_weight * (D_nonadverse ** motion_power) + (1.0 - motion_weight) * (M_continue ** motion_power)) ** (1.0 / motion_power)`

`adverse_break = D_adverse * M_bend`

`reversal_break = R_rev_k * ((1.0 - balance) ** reversal_balance_power)`

`carry_break = (-B_k) * R_rev_k * ((1.0 - balance) ** carry_balance_power) * (1.0 - adverse_break)`

`burden = burden_scale * (C_k / (1.0 + C_k)) * (P_k / (1.0 + P_k))`

`break_agreement = max(adverse_break, reversal_break, carry_break)`

`Accumulate_basin = live * motion * (1.0 - R_rev_k) * (1.0 - adverse_break) * (1.0 - burden)`

`Hold_basin = contested * (1.0 - break_agreement) + live * R_rev_k * balance + live * (1.0 - R_rev_k) * ((1.0 - motion) * (1.0 - adverse_break) + motion * burden)`

`Avoid_basin = rupture + (live + contested) * break_agreement`

Preview parameters to reproduce:
- `beta = 0.5822062466501764`
- `motion_weight = 0.5854903101631882`
- `motion_power = 1.1841456593345179`
- `reversal_balance_power = 20.521505855173686`
- `carry_balance_power = 3.855189811929401`
- `burden_scale = 0.008137131392678132`

Simplification contract:
- one axis at a time only
- no formula family change
- preserve exact counts and `9/9` anchors if possible
- otherwise allow at most `±5` total `L1` count drift while preserving `9/9` anchors
- prefer simpler parameter values only after behavior is preserved

Selected simplification result from the approved sweep:
- keep `beta = 0.5822062466501764`
- keep `motion_weight = 0.5854903101631882`
- keep `motion_power = 1.1841456593345179`
- simplify `reversal_balance_power` to `16`
- keep `carry_balance_power = 3.855189811929401`
- simplify `burden_scale` to `0.0078125`

That simplified candidate preserves:
- `rows = 5413`
- `Accumulate = 133`
- `Hold = 1132`
- `Avoid = 4148`
- anchors `9/9`
