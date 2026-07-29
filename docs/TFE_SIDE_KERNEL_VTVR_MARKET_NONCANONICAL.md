# TFE Side Kernel — Joint Market VTVR Reconstruction (NON-CANONICAL)

**Date:** 2026-07-28
**Status:** Non-canonical research artifact. Grants and inherits no authority.
**Companion to:** the Guala "UF Side Kernel VTVR v2 — A Non-Canonical
Vector–Time–Volume–Relation Reconstruction" (2026-07-27), applied to the TFE
domain following the same walk-up discipline.

## Why this exists

An evaluation of the production TFE kernel (`uf_core` L0–L4) against the
original UF v1.3 intent found the same flattening Sol found in Guala's
kernel, present at every layer:

| Original-intent dimension | Production TFE kernel |
|---|---|
| **Vector** — all entities enter as one simultaneous vector | One scalar (Close) per ticker; ~2,100 isolated single-wire kernels; the joint market field never exists |
| **Time** — exact causal time enters the laws | `dt=1` hard-coded; a segment's duration is its bar count; weekend gap ≡ adjacent tick |
| **Volume** — componentwise swept volume per entity per time | Traded volume never enters the kernel; internal "V_k" is a 3-β weighted sum collapsed to one number per segment |
| **Relation** — complete pair-relation field, never replaced by a scalar | No pair relations anywhere (impossible with N=1); SPY correlation bolted on post-kernel as one scalar |
| **No scalar replacement** | Violated at every hand-off: gates→3 scalars, resonance = 5-λ weighted sum, engine exports last-row + blended means (S_UF = 0.5A+0.5B) |

The production code is ~faithful to its own spec (v1.4.0 skeleton, 4/6
documented) — but that skeleton had already collapsed the joint field before
any code was written. The flattening is inherited, not a coding error.

## What the side kernel is

`tools/isolated_market_vtvr_side_kernel.py` — an isolated, exact,
deterministic reconstruction of the original intent for market data:

- N stocks enter as **one joint vector** per causal time (2 ≤ N ≤ 64,
  2 ≤ M ≤ 2048, O(M·N²) retained in full; exceeding bounds is an error,
  never a silent cut).
- **Exact rational arithmetic** end to end (`fractions.Fraction`); real
  captures parse JSON numbers directly into Fractions — no float ever
  touches a price.
- **Exact causal time** enters the laws (swept volume `|Δx̂|·Δt`, velocity,
  acceleration). A weekend gap is structurally three times a daily gap.
- **Complete pair-relation field** at every time over all N(N−1)/2 edges,
  including the oriented-area **wedge** relation `x̂ᵢ⁻x̂ⱼ − x̂ⱼ⁻x̂ᵢ` — exact
  lead–lag structure between stocks, which the production per-ticker kernel
  cannot represent at any layer.
- **Layer receipts**: SHA-256 over canonical JSON per layer plus one bound
  experience receipt. Two identical runs are byte-identical.
- **L4 = seven full fields** (Displacement, Motion, Reversal, Availability,
  Cohesion, Pressure, Breathing) retaining every time/vertex/edge index.
  Cohesion authority is the full edge field — never a count, mean, or norm.

Declared grouping (non-ratified): one group over all N stocks, so the
group-gain quotient removes exactly a market-common rescale (currency
redenomination). Single-stock splits and negative gain are declared
calibration concerns for future work.

## Walk-up contracts — all passing

`tests/test_isolated_market_vtvr_side_kernel.py` (pytest, 6/6 on
2026-07-28):

1. **Joint field & determinism** — byte-identical receipts across runs;
   4 components and 6 edges retained at every time through L4.
2. **Exact time enters the laws** — a weekend gap scales swept volume 3×.
3. **Common positive gain** — ×7 on all prices changes `H_raw` but not
   `H_VTVR` (raw custody kept; structural view invariant).
4. **Lead–lag delay** — delaying two of four stocks by one causal step
   changes `H_VTVR` and produces nonzero wedge relations (the market analog
   of the interaural-delay contract).
5. **Different waveform** — differs in Vector, Volume, and Relation.
6. **Bounds are errors, not truncation.**

## Authenticated joint capture — real data

`tools/run_market_vtvr_capture.py` (read-only, market-data API only).
First capture, 2026-07-28: N=4 (MSBI, HDB, PHM, TRMB — live CH2 holdings),
M=40 simultaneous daily observations (2026-06-01 → 2026-07-28), 6 edges
per time, full receipts emitted (`H_experience =
e6060166668a6e3c851e79a7d75b086ef24bae989b1071263e5a1b69f8810dc3`).

The relation field immediately showed structure invisible to production:
the strongest oriented-area (lead–lag) edge in the window is **PHM~TRMB**
(2026-07-01), followed by **HDB~PHM** and **MSBI~PHM** — i.e., the
homebuilder led/lagged the industrial and the banks around specific dates.
Production TFE has no representation in which that fact can exist.

## Widened test — pre-registered walk-forward falsification (2026-07-28)

`tools/vtvr_leadlag_walkforward.py`. Protocol frozen before first run:
30 declared tickers (10 live holdings + 20 liquid large caps), 328
simultaneous daily observations, 60/40 in-sample/out-of-sample split,
two mechanical rules (R1: trade the top-10 |wedge| spreads in the
direction chosen by in-sample persistence; R2: harvest the top-10 frozen
in-sample lead-correlation pairs), 5 bps/position-day cost haircut.
Success bar: OOS net expectancy > 0 AND hit rate > 51%.

**Result: NOT CONFIRMED — on both rules.**

| | R1 (wedge spreads) | R2 (lead pairs) |
|---|---|---|
| OOS positions | 1,310 | 1,309 |
| Hit rate | 47.2% | 49.5% |
| Net per position | −19.7 bps | −8.7 bps |
| Cumulative | −25.8% | −11.5% |

Measurement findings (reported regardless of outcome):
- **M1 wedge persistence = 50.1%** — at daily scale the relation field's
  sign is a coin flip step-to-step (near-martingale).
- **M2**: every strong in-sample lead correlation was negative
  (cross-pair mean reversion), and none of it survived out-of-sample.

Honest interpretation: the joint field provably retains more structure,
but its two simplest daily harvests carry no tradeable edge on this
window — consistent with the kernel philosophy's own doctrine that raw
kernel output is not a return predictor and edge lives in the L5
translation. The result constrains, it does not condemn: daily bars are
the coarsest causal scale, and exact-time lead–lag phenomena are
documented at intraday scales this test never touched. Lawful next
walk-ups, in order of promise: (a) the same falsification at minute
scale, (b) the relation field as a *confirmation filter* on existing
CH2/CH3 decisions rather than a standalone signal — each pre-registered
the same way.

## Structural forward study — 120-bar window (2026-07-28)

`tools/vtvr_structural_forward_study.py`: 30 tickers, 754 simultaneous
days (2024-01 → 2026-07), 574 evaluation dates. Five joint-field
descriptors per stock per date from the trailing 120 bars (leadership,
cohesion, breathing, reversal, pressure), cross-sectional quartiles,
forward 20/60-bar outcomes, every band reported.

Findings:
- **REVERSAL sorts the future monotonically**: smooth structural motion
  beat choppy by **2.66% excess over 60 bars** (Q1 +1.02% → Q4 −1.65%),
  monotone at both horizons in the pooled sample (half-split unstable —
  sign flips in H1).
- **Moderate beats extremes, stably**: the middle band of PRESSURE
  (+1.56%/+2.00% excess by half), COHESION (+0.48%/+2.66%), and
  BREATHING (+0.24%/+0.67%) outperformed both extremes at 60 bars with
  the same sign in BOTH halves.
- No single descriptor passed the frozen Q4−Q1 materiality bar; the
  stable signal lives in the middle bands, which the bar didn't measure.

## Favorable-structure backtest — CALM-COHERENT state (2026-07-28)

`tools/vtvr_favorable_structure_backtest.py`. The composite state the
tables point to — **smooth motion + moderate pressure + moderate
cohesion** ("calm-coherent", ~6.8 of 30 stocks per date) — backtested
CH2-style against the universe over the same 574 dates:

| Horizon | Universe | Calm-coherent | Edge |
|---|---|---|---|
| 20 bars | +1.26%, 55.8% win | +1.57%, 59.0% win | **+0.31%** |
| 60 bars | +3.52%, 59.4% win | +4.46%, 62.5% win | **+0.94%** |

Half-split: H1 −0.78%, H2 **+2.53%** at 60 bars — the state's edge is
regime-dependent on this window and strengthened materially in the most
recent ~14 months. At the last evaluation date the state held NBIX, BDX,
AZZ (three current CH2 holdings), AMZN, JPM, XOM, JNJ, WMT, PEP.

Status: the gate was composed from this window's own band tables, so its
final authority requires forward confirmation on data it has never seen
(running it as a daily observer alongside CH2 is the natural next
walk-up). It is structure-first, threshold-free (rank bands only), and
uses only relation-field quantities production cannot see.

## Structure search, L5 translation, replication, adversarial nulls (2026-07-28)

Free-play mandate over the frozen kernel's outputs (kernel byte-identical
since first commit; walk-up retention contracts green throughout).

**Search** (`tools/vtvr_structure_search.py`): 30 tickers, 1,502 joint
days (2020-07 → 2026-07), 1,322 eligible dates (120-bar entry filter),
54 structural atoms at two scales (W=120, W=30) + field-level herd
context, all single/pair/triple states, 70/30 date split, support ≥ 400.

**Surviving star state — COHERENT LAGGARD**
`BRTH.L:MID & COH.S:HI & LTRND.L:LO` — moderate 120-bar breathing,
top-third 30-bar herd coherence, bottom-third 120-bar leadership trend.

| Test | N | WR@60 | WR@90 | mean fwd90 |
|---|---|---|---|---|
| Cohort A search | 418 | 77.8% | — | — |
| Cohort A holdout | 200–220 | 78.0% | 82.7% | +10.50% |
| **Cohort B (virgin universe)** | 602 | **78.2%** | **79.4%** | **+10.27%** |
| Universe baselines | — | 56–58% | 56–58% | +3.9–4.5% |

Three independent confirmations within half a point at 60 bars. The
holdout also *killed* several equally-strong-in-search rival states
(77–78% search → 31–43% holdout), demonstrating the harness
discriminates luck from structure.

**L5 translation** (`tools/vtvr_l5_translation_study.py`): edge grows
with hold length (55% @20 → 77.7% @60 → 82.7% @90 on holdout); meadow
conditioning (field coherence LO at entry) reached 88.9% @90 (+12.37%)
on cohort A holdout but did not clearly replicate on cohort B (81.1% LO
vs 80.8% HI) — recorded as unproven, not adopted.

**Adversarial destruction nulls** (`tools/vtvr_adversarial_null_test.py`),
per the physics-not-quant doctrine — the edge must vanish when the
structure is destroyed while all return distributions are preserved:

- NULL A (per-stock deterministic shred; relations + time destroyed):
  edge **−15.4pp** at 90 bars — the state becomes an anti-signal.
- NULL B (joint date shred; relations kept, time destroyed):
  edge **−0.2pp** — fully collapsed.

Live-data edge: **+21–23pp**. The state reads real temporal-relational
fabric; it is not a distributional artifact.

**Physical mechanism (stated, falsifiable):** in the group-normalized
field, structural shares are conserved (they sum to 1). A component
whose share has drained (laggard) while it remains dynamically coupled
to the field (high recent coherence) and alive (mid breathing) sits in
a restoring-flow configuration: the conserved, coupled field pulls it
back toward its coupled position. The tables confirm the mechanism's
own failure predictions: laggards that are decoupled or still draining
(high breathing trend) do NOT recover — those states collapsed in
holdout exactly as the mechanism requires.

**Live observer** (`tools/vtvr_daily_observer.py`): appends daily state
memberships to `artifacts/vtvr_observer/observations.jsonl` (gitignored
data); `--score` grades matured observations. First observation logged
2026-07-28 (calm_coherent: BDX, DORM, JNJ, NBIX, PEP, WMT, XOM;
smooth_laggard: WMT; coherent_laggard: empty — the state is selective,
~1.5% of stock-days).

**No-flattening contract:** the kernel file is frozen; all studies are
consumers. Walk-up test 1 asserts complete per-time vector, volume, and
relation retention through L4 — any future flattening fails the suite
loudly before it can ship.

## Boundaries honored

- No import from `uf_core`, the L5 layer, the refresh pipeline, or
  `dsf_ai_service` (Guala substrate untouched).
- No production persistence, no deployment, no trading claim.
- Like VTVR v2: the four passing contracts and one capture grant **no
  canonical authority**. The next lawful walk-up, if pursued, would be
  repeated captures across regimes and a falsification design for whether
  the retained relation field improves structural perception — before any
  talk of wiring it to decisions.
