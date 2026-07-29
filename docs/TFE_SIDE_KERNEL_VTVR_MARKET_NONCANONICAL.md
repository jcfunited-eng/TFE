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

## Boundaries honored

- No import from `uf_core`, the L5 layer, the refresh pipeline, or
  `dsf_ai_service` (Guala substrate untouched).
- No production persistence, no deployment, no trading claim.
- Like VTVR v2: the four passing contracts and one capture grant **no
  canonical authority**. The next lawful walk-up, if pursued, would be
  repeated captures across regimes and a falsification design for whether
  the retained relation field improves structural perception — before any
  talk of wiring it to decisions.
