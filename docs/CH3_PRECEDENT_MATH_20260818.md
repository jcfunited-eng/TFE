# Precedent sweep + energy context — the math, beside the spec's law

Filed 2026-08-18 at Joe's demand. Companion to
docs/CH3_TUPLE_TIME_MATH_20260817.md (kernel L0-L4 formulas) and
docs/CH3_JOINT_FIELD_MATH_20260817.md. Implementations:
tools/ch3_energy_context.py, tools/ch3_field_state_precedent.py.

## Energy context (Joe: individual lifetime / group / system)

| Quantity | Exact definition | Spec authority |
|---|---|---|
| Individual lifetime energy position | L(t) = #{k in [61, t) : URF(k) < URF(t)} / #{k in [61, t)} — a count-rank of today's stored tension within the stock's own prior life; classes Q1 [0,.25) Q2 [.25,.5) Q3 [.5,.75) Q4 [.75,1] | counting facts, no scalar authority; causal (prior bars only) |
| Individual lifetime action position | same count-rank for a(t) = \|ln c(t) − ln c(t−1)\| | same |
| Group (v1: same-day cohort) | n_unc(day) = # qualifying uncovered spikes that calendar day; dyadic classes {1, 2-3, 4-7, 8-15, 16+} | group = other vertices, joint field; correlation families deferred (family_heat mask bug disclosed) |
| System breadth | share of herd-covered names with gband >= 1 that day; classes {100, [75,100), [50,75), [25,50), [0,25)} | the market-wide field's saturation state; the 100% state is a known distinct regime (~39% of decade days) |
| System supply | # of ALL qualifying spikes that day (covered + uncovered), dyadic | system energy expressed as event production |
| Quotients | J = (L-quarter ; cohort ; breadth), and marginals M1..M6, all declared pre-run | frequencies over exact structures |

## Field-state precedent sweep (the 70-readings taxonomy frozen)

Facts per event t, all causal at the event close, kernel outputs only:

    urf0_run       = # consecutive bars ending at t with URF = 0
    bars_since_cl  = # bars since gate_count last incremented
    closures20     = gate_count(t) − gate_count(t−20)
    urf0_frac20    = # bars with URF = 0 in t−19..t
    rres_slope3    = sgn[R_res(t) − R_res(t−3)]
    rres_d3        = R_res(t) − R_res(t−3)          (value, for v1.1)
    rres_below_max = R_res(t) < max R_res over t−5..t−1
    fn_dir         = sgn[F_n(t) − F_n(t−1)]
    price_leak     = sgn[c(t−1) − c(gate start)]
    attn_alive     = sgn[v(t−1) − median(v, trailing 20 at t−1)]

Classes v1 (first match wins; constants 3/10/20/6 are declared
translations of the readers' words, fixed before scoring):

    BLOCKED     := bars_since_cl >= 10  or  urf0_run >= 3
    BLOCK_LIVE  := BLOCKED ∧ rres_slope3 >= 0 ∧ price_leak > 0 ∧ attn_alive >= 0
    BLOCK_DEAD  := BLOCKED ∧ (rres_slope3 < 0 ∨ attn_alive < 0)
    ADMIT_CHEAP := closures20 >= 3 ∧ urf0_frac20 = 0 ∧ rres_slope3 > 0 ∧ fn_dir <= 0
    SPENT_BACK  := rres_below_max ∧ fn_dir > 0
    CONDUCT     := closures20 >= 6 ∧ urf0_frac20 = 0

v1.1 (DECLARED 2026-08-18 before any sweep result existed): the NESR
worked example exposed a v1 translation defect — "resonance alive/
holding" as a raw 3-bar sign calls a −0.005 wobble on a held 0.40
plateau "falling". The kernel's own notion of unchanged resonance is
drift within one hysteresis width (H_MAX = 0.20, pinned):

    held (v1.1)      := rres_d3 >= −0.20
    BLOCK_LIVE v1.1  := BLOCKED ∧ held ∧ price_leak > 0 ∧ attn_alive >= 0
    BLOCK_DEAD v1.1  := BLOCKED ∧ (¬held ∨ attn_alive < 0)

Both classifications filed; neither replaces the other.

Outcomes (three, declared): grenade = any next-5 close >= 1.20×entry
(the clock); retained = c(t+5) >= c(t); relaxed = c(t+5) <= c(t−1).
Plus fade dollars under the live law per class.

Vehicle scar (junk typing, causal): scar at j iff c(j) >= 1.5·c(j−5)
and min c(j+1..j+10) <= 0.6·c(j); scars known from bar j+10 onward;
classes {0, 1, 2+}. All tables filed uncut and with scars >= 1 removed.

Custody: the 70 taxonomy events are excluded from all counts (list
committed at docs/CH3_JEWELER_SAMPLE_70.json); pre-2022 half is fully
blind to the taxonomy (built on 2024+ events only).

## Worked example — NESR, event 2024-01-02, every number real

    closures20     = 175 − 173 = 2
    bars_since_cl  = 11                (BLOCKED: 11 >= 10)
    urf0_run       = 11 bars, URF(t) = 0.0000   (channel shut)
    rres_d3        = 0.4023 − 0.4071 = −0.0047
    fn_dir         = sgn(2.9082 − 2.9056) = +
    price_leak     = 6.10 − 4.25 = +1.85  (leaking up through the block)
    attn_alive     = 345,824 vs median 47,676 = +
    v1  : rres_slope3 = sgn(−0.0047) = −1  → BLOCK_DEAD  (the defect)
    v1.1: held = (−0.0047 >= −0.20)        → BLOCK_LIVE
    outcome: clock GRENADE; c(t+5) = 7.65 >= 6.60 (retained);
             not relaxed. The readers' canonical live-charge case.
