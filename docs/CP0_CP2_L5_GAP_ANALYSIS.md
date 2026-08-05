# CP-0 → CP-2 Gap Analysis: L5 Cognitive Pipeline

## Status: SCOPING DOCUMENT — no code changes

## Purpose
Enumerate what the quarantine cognitive pipeline (CP-2) provides that
production's L5 decision layer (V3 basin) does not, per UF-Spec chapters
6-7 and the quarantine_historical_kernel.py implementation.

## What Production L5 Has (V3 Basin)
- Basin argmax decision from DSF fields (D_k, M_k, R_rev_k, U_star_k, C_k, P_k, B_k)
- S_UF and R_UF stability/resonance scores
- Price filter (Close ≥ $5)
- Stable Titan scaler (D_k=0, S_UF ≥ 0.85, bars ≥ 1000)
- No cognitive/CV-1.0 fields used in decisions

## What Quarantine CP-2 Has (Missing from Production)

### 1. Event Tape
Quarantine kernel processes gate-close events sequentially, maintaining
state across gates. Production processes each symbol as a batch and takes
only the last-gate output. The quarantine approach produces per-date
decisions; production produces one decision per symbol per refresh.

**Gap:** Production cannot evaluate "was this stock Accumulate 3 days ago?"
Only "is it Accumulate right now?"

### 2. Shared Latent Field (CV-1.0 State Variables)
Quarantine maintains three integrators:
- x_f (fast, A_f=0.90)
- x_m (medium, A_m=0.98)
- x_s (slow, A_s=0.995)

Plus attention state a_state[3], rho (coherence), and surprise.
These accumulate across gates and provide temporal memory.

**Gap:** Production has no temporal memory. Each evaluation is stateless
per UF-Spec Section 1.2 ("no internal state carryover between evaluations").
Note: the CV-1.0 integrators technically violate this spec requirement.

### 3. F_n (Cognitive Load)
F_n = gamma + lambda_s * surprise
where gamma = 0.5 * (u_value + (1 - rho))
and surprise = ||nu_core - z_n||

F_n measures how "surprised" the system is by the current gate relative
to its accumulated state. Low F_n = predictable, high = novel.

**Gap:** Production computes F_n via CP-2 in uf_mdg_snapshot.py but does
not use it in decisions (cognitive gate removed 2026-04-27).

### 4. Horizon Heads Q_5 / Q_20 / Q_60
Q_5  = dot([1,0,0], z_n) - eta_h * F_n = x_f - 2*F_n
Q_20 = dot([0,1,0], z_n) - eta_h * F_n = x_m - 2*F_n
Q_60 = dot([0,0,1], z_n) - eta_h * F_n = x_s - 2*F_n

These project the latent state onto three timescale heads, penalized
by cognitive load. Positive Q = momentum at that timescale.

**Gap:** Production does not compute or use horizon heads.

### 5. Cross-Horizon Coherence χ_n
chi_n = 1.0 if sign(Q_5) == sign(Q_20) == sign(Q_60), else 0.0

Measures whether all three timescale heads agree on direction.

**Gap:** Production has no cross-timescale coherence measure.

### 6. Action Mapping Rules
Quarantine: ACCUMULATE if Q_20 > 0.65 AND F_n ≤ 0.45 AND chi_n ≥ 1.0
Production: V3 basin argmax (completely different formula)

**Gap:** Two different decision functions. Not reconcilable without
choosing one.

## Spec Compliance Note
The CV-1.0 integrators (x_f, x_m, x_s with A_m=0.98 etc.) maintain state
across gates within a single evaluation. UF-Spec Section 1.2 states:
"no internal state carryover between evaluations." If each symbol evaluation
is one "evaluation," the integrators are compliant (state resets per symbol).
If each gate is an "evaluation," they violate the spec.

The quarantine kernel clearly treats a full symbol history as one evaluation
(state accumulates across all gates for a symbol). This appears compliant
with the intent of Section 1.2.

## Recommendation
Do NOT touch L5 until the 4-condition backtest results are in. The backtest
will show whether the V3 basin decision formula on the production kernel
(L0-L4) produces a WR worth building on. If it does, L5 work is about
closing the gap. If it doesn't, L5 work is premature — the kernel output
itself needs to improve first.

If and when L5 work begins, the path is:
1. Add event tape (per-date evaluation, not just final gate)
2. Add CV-1.0 integrators (temporal memory)
3. Add F_n and horizon heads
4. Add chi_n coherence
5. Choose between V3 basin and Q_20 decision rule based on backtest data
6. Document chosen rule as the canonical L5 financial adapter decision
