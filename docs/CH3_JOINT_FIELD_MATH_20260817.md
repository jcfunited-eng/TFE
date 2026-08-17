# CH3 joint-field shadow — the math, beside the spec's math

Filed 2026-08-17. Demanded by Joe: "SHOW YOUR MATH AND THE SPEC MATH."
Spec: UF v1.3 Joint-Field Reconstruction (docs/UF_Spec_v1_3_JointField_
Reconstruction_NONCANONICAL.tex; ratified by Joe as THE spec 2026-08-18
conversation). Implementation: tools/ch3_joint_field_shadow.py,
tools/ch3_joint_field_gates.py — adversarially audited (5 agents);
causality REFUTATION FAILED (clean); one declaration mismatch found and
corrected (both quotients now filed).

## 1. Spec math → projection math, line by line

| Spec (joint-field reconstruction) | Financial projection (implemented) |
|---|---|
| Field custody: exact rationals per vertex | x_k = round(10^4 · c_k) ∈ ℤ, price in ten-thousandths of a dollar. Quantization disclosed: ~13k of 15.7M closes sit off the grid, max residue half a step. |
| Displacement Δ_k = x_k − x_{k−1} | D_k = x_k − x_{k−1} (integer) |
| Curvature κ_k = Δ_k − Δ_{k−1} | K_k = x_k − 2x_{k−1} + x_{k−2} (integer) |
| Per-scale dispersion σ^(s)_k over causal window I_{k,s}; the signature uses only sgn(σ^(s)_k − σ^(s)_{k−1}) | VS(s,k) = s·Σ_{i∈I} x_i² − (Σ_{i∈I} x_i)², I = the s bars ending at k. Identity: VS(s,k) = s²·σ²(s,k). Equal window lengths ⇒ sgn(σ²_k − σ²_{k−1}) = sgn(VS_k − VS_{k−1}) exactly, in pure integer arithmetic (no square roots, no floats). |
| Causal dyadic scales S_T = {1,2,4,…} | s ∈ {2, 4, 8, 16, 32} trading days (scale 1 has no dispersion; upper bound declared) |
| Negative space N (quiescence is a state, not zero) | N_k = 1 iff x_k = x_{k−1} = x_{k−2} = x_{k−3}. Degenerate inside this event set (the +8% gate forces D_k > 0) — retained for fidelity, always 0. Disclosed. |
| Signature Σ^(s)_k = (sgn Δ, sgn κ, sgn δσ^(s), N) | Σ_k = ( sgn K_k ; sgn dVS(2,k), …, sgn dVS(32,k) ; N_k ). sgn D_k omitted: the event filter fixes it +1 — the quotient-loss disclosure the spec requires. |
| Gates: maximal contiguous intervals of unchanged signature; duration T_G is part of TVR | Build run B(t) = max{ b : dVS(s,k) > 0 for ALL s, for the b consecutive bars ending at t } — the age of the current all-rising configuration. Dyadic duration classes {0, 1, 2–3, 4–7, 8+}. |
| L4 D-field: atom-wise sign displacement of consecutive structures | Q_B_declared components sgn(dVS(s,t) − dVS(s,t−1)) (value displacement) and, separately filed, Q_B_persistence components sgn(sgn dVS_t − sgn dVS_p) (sign persistence; 0 = the motion kept its sign = gate continuation). The first run computed persistence while declaring value-displacement — the audit caught it; both are now filed under their true names. |
| No scalar authority; comparisons are frequencies over exact discrete structures | Every result is a count: n_grenade/n_class per exact signature string, derive half and frozen half separately, class claims need n ≥ 50 in derive. No weighted sum exists anywhere in the analysis. |
| Label-blind, source-disjoint validation | Structures built before labels touched; derive ≤ 2021-12-31 (shadow) / ≤ 2023-12-31 (gates round, moved split disclosed), confirm frozen on later years only. Universe imbalance across the split (coverage triples) disclosed. |
| Shadow discipline: beside canonical, both filed, no auto-winner | Canonical full chain (replay_symbol_v2, weighted): filed ch3_kernel_full_chain.json. Shadow: filed ch3_joint_field_shadow.json / _gates.json. |

Deviations from the full spec, owned: single vertex (no group, so the
spec's group-projective normalization is degenerate — raw integer
custody used instead, signs are scale-free); only the D-component of
the seven L4 fields is measured so far; the event filter and grenade
label run in float64, identical to every prior CH3 study (L5 domain
law, outside the kernel; disclosed).

## 2. A worked example — every number real

LIVE (NRG spin-off band $10–20), event day 2025-04-15.

```
closes c[t-8..t]:   7.70  8.04  8.25  8.07  8.09  8.19  8.55  9.51  11.70
integers x[t-8..t]: 77000 80400 82500 80700 80900 81900 85500 95100 117000

D_t = 117000 − 95100 = 21900          (+23.0% day — event gate passes)
K_t = 21900 − 9600  = 12300           curvature +
K_p = 9600 − 3600   = 6000            sgn(K_t − K_p) = +1  (accelerating)

VS(s,k) = s·Σx² − (Σx)²  over the s bars ending at k:
scale  2: … 12 960 000 → 92 160 000 → 479 610 000        rising, rising
scale  4: … 59 640 000 → 503 160 000 → 2 983 230 000     rising, rising
scale  8: … 547 200 000 → 1 652 640 000 → 9 012 640 000  rising, rising
scale 16: … 8 786 011 232 → 13 157 851 232 → 35 139 161 232
scale 32: … 24 637 378 863 → 36 265 835 063 → 88 625 234 864

All five scales rising at t, t−1, t−2  ⇒  build run B = 3
Structure: depth class "2-3", acceleration "a+"  →  the deep-build class.

Label: 1.20 × 11.70 = 14.04. Next five closes:
  11.38  11.06  10.90  10.80  10.88   — never reaches 14.04 ⇒ NOT a grenade.
Fade outcome under the live law: enter short 11.70; harvest line
0.95 × 11.70 = 11.115; first close below it is 11.06 (day 2) ⇒ +5.5%.
```

This one event lands in the class whose decade counts are:
derive 42/228 = 18.4% grenades, frozen 78/388 = 20.1% (base 16.2%) —
this particular one was in the 80% that relax. The class's claim is
those counts, nothing else.

## 3. What survived, what did not (counts, both halves)

- Q_A (event-bar slice): 46 structures, ZERO surviving claims.
- Q_B_declared (value displacement, as first declared): 163 structures,
  ZERO coherent survivors — the fine quotient fragments into noise.
- Q_B_persistence (what the first run measured; retro-declared,
  status = pre-registered live hypothesis): one survivor —
  all-scale build sustained with accelerating curvature:
  15/72 = 20.8% derive, 116/584 = 19.9% frozen (base 11.6/16.0%).
- Gate-depth Q_C (declared fresh, frozen 2024+ untouched at declare
  time): deep build "2-3;a+" 42/228 = 18.4% → 78/388 = 20.1%;
  no-build "0;a−" 99/549 = 18.0% → 166/828 = 20.0%. Two-ended risk.
- Per price stratum: deep build strongest in $80+ (17/50 = 34.0% →
  10/38 = 26.3%); one $40–80 class flipped sign at n = 50 —
  small-count stratum claims filed as noise.
- Canonical flattened chain, same events: best feature D_k separates
  16.2% vs 15.3% frozen (+0.9pp) — nothing. Side-by-side per the
  spec; no auto-winner declared, the counts are the argument.
- Structural cut at t+1 (exit when the after-field shows D+K+V+):
  derive REJECTS (135.7 vs 138.2 per-100-events); not adopted.
  Seeing the grenade at the close is not capturing it — reveal-bar
  law holds again.
