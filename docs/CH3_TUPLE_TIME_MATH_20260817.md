# The tuple-across-time evaluation — my math beside the spec math

Filed 2026-08-17 at Joe's demand ("SHOW ALL YOUR MATH AND THE SPEC MATH
NEXT TO IT SO WE SEE YOU ARE NOT FUCKING UP"). Pipeline in Joe's stated
order: time series → kernel → tuple → dimensionalized across time →
structure seen. Kernel formulas quoted from tools/ch4_uf_kernel_v2.py
(implements UF-Spec v1.3.0 §§2–7, §11 + merged TFE spec ch05/ch06;
conformance audit docs/CH4_KERNEL_SPEC_CONFORMANCE_AUDIT_20260729.md).
Evaluation discipline from the Joint-Field Reconstruction constitution
(docs/UF_Spec_v1_3_JointField_Reconstruction_NONCANONICAL.tex).
Implementation of this pass: tools/ch3_kernel_tuple_time.py.

## Step 1 — series flows into the kernel (spec §2, L0)

| Spec | Implemented (verbatim from the kernel) |
|---|---|
| Normalized log field | F(t) = ln(c(t) + 1e-8) |
| Field motion | ΔF(t) = F(t) − F(t−1) |
| Local variance, trailing window W=20 | σ(t) = mean over the last 20 bars of (F − mean F)² |
| Curvature (interior) | κ(t) = \|F(t+1) − 2F(t) + F(t−1)\| |
| Attention/relevance | r(t) = v(t) / median(v, trailing 20) |
| Negative space is a state | N(t) = 1 iff σ<1e−6 ∧ \|ΔF\|<1e−6 ∧ κ<1e−6 |
| Structural boundary (§2, adaptive) | step²(t) = Σ over the six-tuple (F,ΔF,σ,κ,r,N) of (component change)²; boundary iff step²(t) > mean of trailing-20 step² OR N flips |
| Per-bar structural action | perV(t) = \|ΔF\| + σ + κ (registry weights = 1) |

## Step 2 — gates (spec §3, L1)

| Spec | Implemented |
|---|---|
| Gate = span between boundaries | [t_a, t_b): T = t_b − t_a |
| Gate integrals | V = Σ perV over the gate; R = Σ r over the gate |
| Lattice cells, three pinned scales | P = (⌊T/h₁⌋, ⌊V/h₂⌋, ⌊R/h₃⌋) at (1,1,1),(2,2,2),(4,4,4); C = #distinct cells |
| Gate mean-state and drift | μ = per-bar means of (ΔF, σ, κ); δ_g = ‖μ − μ_prev‖ |

## Step 3 — contrast and structure (spec §§4–5, L2)

| Spec | Implemented |
|---|---|
| Contrast vs own recent history | CV = (T,V,R) − mean of trailing 5 gates |
| Self-scaling saturation (no external constants) | x̂ = x/(x+m), m = mean of x over trailing 5 gates |
| Structure | S = (σ̂ + κ̂ + r̂)/3 |
| Coherence weight | w = (χ̂ + S)/2, χ_density = V/T |
| Unresolvedness | U = 0.1·C + 0.1·δ_g + 0.2·N_gate |
| Anomaly damping (graded, #14) | if U>0.8 or δ_g>2.0: w ← 0.5·w |
| Regimes, pinned bands 0.25/0.75 | (σ̂,κ̂) → CHAOTIC/VOLATILE/STABLE/TRANSITIONAL |

## Step 4 — resonance (spec §6, L3)

| Spec | Implemented |
|---|---|
| Five-term resonance functional | R_res = [w + ĈV + S + 1/(1+C) + (1−U)]/5 |
| Hysteresis | Hyst = 1 iff \|R_res − R_res,prev\| > 0.20 |
| Admissibility and the unresolved field | adm = 1 iff U ≤ 0.75 ∧ Hyst = 0; URF = adm·R_res |

## Step 5 — the deep recursions (spec §7, L4)

| Spec | Implemented |
|---|---|
| Displacement of the unresolved field | ΔR = URF_k − URF_{k−1}; D_k = sgn(ΔR) with the kernel's pinned dead-band ε = 0.00073 |
| Second difference | M = URF_k − 2·URF_{k−1} + URF_{k−2} |
| Effective unresolvedness | U* = U + 0.1·Hyst + 0.1·IAS |
| Reversal | Rev_k = 1 iff D_k·D_{k−1} < 0 |
| Bounded balance recursion | B_k = clip(B_{k−1} + 0.1·(1−U*)·ΔR − 0.1·U*, −1, 1) |
| Validation plane | S_UF = [coh + (1−h̄) + (1−var B) + (1−ū*) + (1−drift̂)]/5 over trailing 5 gates |

## The tuple (what flows out of the kernel, per bar)

(S_UF, R_res, URF, F_n, χ_n, Q_20, x_f, x_m, x_s, ρ_n, s_n,
 B_k, U*_k, D_k, Rev_k, gate_count, regime, action, event_type)

Degeneracies measured on all 12,695 events and disclosed: action ≡
HOLD, χ_n ≡ 1 on every event; B_k < 0 always (sign carries nothing).

## Step 6 — dimensionalized across time (mine; authority = the
joint-field constitution: structures are exact sign facts, no fitted
thresholds, contradictions retained, quotient losses named)

T1(t) — one step into the event:
  ( sgn[S_UF(t) − S_UF(t−1)], sgn[R_res(t) − R_res(t−1)],
    sgn[URF(t) − URF(t−1)], D_k(t), Rev_k(t) )
T2(t) — the three-bar approach:
  ( sgn[S_UF(t) − S_UF(t−3)], sgn[R_res(t) − R_res(t−3)],
    sgn[URF(t) − URF(t−3)], event_type(t−1), event_type(t) )

The form is the kernel's own: D_k is ALREADY sgn of a one-step change
of URF — T1/T2 extend that exact construction to the tuple's other
coordinates. A trajectory where S_UF rises while URF falls is its own
class — a retained contradiction, never averaged away.
Named losses: magnitudes; the coordinates not in T1/T2 (F_n, Q_20,
x_f, x_m, x_s, ρ_n, s_n, B_k, U*, gate_count, regime — regime is
filed separately per event); depth beyond 3 bars.

## Step 7 — the structure seen (joint-field constitution)

Frequencies over exact trajectory classes ONLY — "of the N events
whose tuple moved exactly this way into the spike, g kept pumping" —
derive ≤ 2021-12-31, confirm frozen 2022+, claims need n ≥ 50 in
derive and are judged solely on confirm. No scalar authority: no
weighted sum, no score, no distance appears anywhere in the
evaluation. Universe imbalance across the split (store coverage
triples) disclosed. Replay-skipped events counted and filed.
