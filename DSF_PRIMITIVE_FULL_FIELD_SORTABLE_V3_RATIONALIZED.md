# DSF Primitive Full-Field Sortable V3 Rationalized

This file records the frozen rationalized primitive candidate from the confirmed sortable v3 family.

Status:
- frozen primitive base

Primitive tuning:
- complete for now

Future work:
- governance only

It is audit-only.
It is not canonical.
It does not modify runtime.
It does not claim full governed L5.

Primitive field surface:
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

Frozen rationalized constants:
- `beta = 37 / 64`
- `motion_weight = 3 / 5`
- `motion_power = 5 / 4`
- `reversal_balance_power = 16`
- `carry_balance_power = 4`
- `burden_scale = 1 / 128`

Shared family contract:
- `M_hat = max(-1.0, min(1.0, M_k))`
- same sortable v3 family
- same `TIE_EPS = 1e-12`
- same fixed snapshot
- same primitive surface only

Field interpretation:
- support and resonance net of `U_star_k` create live reserve geometry
- the `core` / `edge` split creates protected versus contested live structure
- `D_k` and `M_k` create motion and bend geometry
- `R_rev_k` is first-class break geometry
- `B_k` stays relational through `carry_break` only
- `C_k` and `P_k` stay bounded and late through `burden`
- action comes from basin dominance, not a signal ladder

Formula family:

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

Tie rule:
- `TIE_EPS = 1e-12`
- absolute epsilon only
- if two or more basins are within `TIE_EPS` of the max, `decision = Hold`

Frozen proof record:
- `rational_match = 90.52924791086329%`
- `conservative_but_plausible = 5.849582172701926%`
- `suspicious_mismatch = 3.6211699164345257%`
- `zero_basin_fallback = 0.0%`
- `plausible_total = 96.37883008356522%`
- `evaluated_row_count = 502`
- `sample_split_global = 359`
- `sample_split_diagnostic = 143`
- `dropped_or_unscored_rows = 0`
- candidate counts:
- `Accumulate = 133`
- `Hold = 1132`
- `Avoid = 4148`
- anchors `9 / 9`

Mismatch concentration:
- top suspicious symbol: `AIZ` with `2`
- top miss directions:
- `Hold -> Accumulate = 30`
- `Avoid -> Hold = 11`

Why this is more defensible than the raw preview:
- it keeps the same family
- it keeps the same primitive surface
- it adds no helper fields
- it uses rational constants instead of search-shaped decimals
- it preserves the same exact fixed-snapshot behavior
- it cleared the stated accuracy gate on the approved adjudicated sample

Do not misstate:
- do not call this canonical
- do not call this full governed L5
- do not claim full-universe hand-labeled truth proof
- do not reopen primitive tuning unless governance later reveals a concrete primitive failure surface
