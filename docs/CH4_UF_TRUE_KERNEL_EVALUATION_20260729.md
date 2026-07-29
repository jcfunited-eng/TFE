# CH4 True-to-Original UF Kernel — Build + Whole-History Evaluation (2026-07-29)

Mandate (Joe): CH4 = the true-to-original-design kernel, NO L0–L4 internals
flattened, full-history-and-structure evaluation per ticker, correct L5
interpretation governance, paper-only side channel, compared against CH2.
Acceptance bar stated by Joe: a faithful kernel + correct L5 governance
reproduces ~91% WR and ~36.7% profit deterministically, in all SPY
conditions. **This document reports what the faithful implementation
actually produced. Raw. Nothing tuned toward the target.**

## 1. What was built (`tools/ch4_uf_engine.py`, `tools/ch4_uf_replay.py`)

Restored vs the deployed flattened path (which exports only the last
gate's scalars, hardcodes relevance=1.0, substitutes vol/drawdown/polyfit
for L1/L2, and feeds a row-first L5):

- Kernel: the preserved faithful lineage (`quarantine_historical_kernel`),
  pinned `KernelParameters`, real ψ_r relevance, canonical ψ_s/φ_reg/ψ_u/
  φ_ias, full gate trajectory → ISF → resonance (hysteresis+admissibility)
  → DSF recursions. Nothing flattened; every layer's ordered objects kept.
- L5 (ch06 + lineage): event tape over gates, Δτ/ω/φ/ρ, mode amplitude,
  RMM bands (0.90/0.98/0.995), latent field, surprise, free structural
  energy F_n, Q_5/Q_20/Q_60, coherence χ, full action mapping
  (ACCUMULATE/AVOID/ABSTAIN/HOLD), plus the lineage-realized sequential
  governance: **resonance-ignition** primitive (URF admitted after ≥2
  suppressed gates) under the CP-2 cognitive bounds (F_n ≤ 1.65,
  x_m ≤ 0.50, $5 floor) — reconstructed from the preserved system's own
  trade records.
- Causality: every daily action computed from the prefix [0..t] only
  (live-identical). Endpoint-κ rule honored. No normalization ever sees a
  future gate.

## 2. Verification (all passed; adversarial re-audit after the crash)

- **Parity**: gate-for-gate vs the preserved implementation on full
  histories — bit-identical F_n/Q_20/x_m and decisions (0 mismatches,
  1253 gates × 3 symbols); branch coverage confirmed non-vacuous
  (ACCUMULATE and AVOID both exercised).
- **Ignition reconstruction**: 12/12 randomly sampled preserved trades
  (fixed seed) land exactly on gates my engine independently flags as
  ignitions.
- **Causality**: sampled days re-derived from truncated data —
  bit-identical, including specifically ON book-entry signal days.
- **Determinism**: SHA-256 action receipts stable across runs; no RNG.
- One real defect found by the audit in the (unwired, never-run) daily
  runner — stale-price entry when a feed lags — fixed.

## 3. Evaluation (declared before results)

Store: local preserved 5y OHLCV (11,884 symbols, 2021-03-26→2026-03-24;
cross-verified against a second data source, sub-0.1% feed differences).
Universe rule: ≥1250 bars and median close ≥ $5 → **5,016 symbols**, no
hand-picking. Signals: fresh governed transitions. Book: $100k, 10%
slices, max 10 concurrent, exit on first extinction or +20 bars, no costs.
Field modes declared with RAW (lineage) primary, LOG (UF-Spec §2.4
normalization) variant. Event-resolution decomposition (signals on
causally-provable gate-close days) declared and filed alongside.

## 4. Results (raw)

### RAW field (lineage primary)
| Slice | n | WR@20 | mean@20 | WR@60 | mean@60 |
|---|---|---|---|---|---|
| ACCUMULATE (all) | 591 | 38.6% | −0.25% | 33.5% | −0.99% |
| ACCUMULATE (event-res) | 91 | 37.8% | +0.08% | 37.5% | −0.49% |
| AVOID (all) | 198,507 | 51.6% | +0.40% | 51.9% | +0.94% |

Book: 160 trades, WR 42.5%, **−7.29% over 5y** (yearly: −0.8/−4.1/+0.2/
+1.6/−4.8/+0.6). The RAW field is scale-dependent (dollar thresholds →
gate-per-bar on high-priced names); extinction fires on ~half of all
bar-days — noise, no negative edge on the AVOID side.

### LOG field (UF-Spec §2.4)
| Slice | n | WR@20 | mean@20 | WR@60 | mean@60 |
|---|---|---|---|---|---|
| ACCUMULATE (all) | 4,985 | 49.0% | +0.07% | 47.5% | −0.05% |
| ACCUMULATE (event-res) | 220 | 42.5% | −2.11% | 40.8% | −3.80% |
| AVOID (all) | 5,123 | 45.1% | −0.86% | 43.7% | −1.46% |
| **AVOID (event-res)** | **146** | **42.8%** | **−5.55%** | **35.7%** | **−9.52%** |

Book: 584 trades, WR 48.3%, **+18.65% over 5y** (≈ +3.5%/yr; below
buy-and-hold for the era). Yearly: −14.9/+13.2/+40.9/+0.8/−10.2/−3.3.

### The one genuine structural finding
**Resonance extinction at a causally-provable gate boundary (LOG field)
precedes real weakness**: −5.5% @20 bars, −9.5% @60 bars vs an upward
universe baseline, monotone with horizon (n=146). The field's collapse
into suppression is informative; its ignition, under this realization, is
not.

## 5. The preserved 64.66% and why it does not survive

The preserved system's own sequential filter reports 64.66% WR@20 on its
whole-history states. Two contaminations account for the gap to my
causal replay: (i) its states were built once over full histories — L2/L3
normalizations (V_max, CV_max) and interior κ see the future; (ii) its
12k universe includes near-riskless drift instruments (money-market/
treasury ETFs) that "win" trivially. Under strict causality on a clean
rule-universe, the same decision rule scores ~38–43% WR. **The apparent
edge was look-ahead plus composition, not physics.**

## 6. Verdict against the stated bar

~91% WR / ~36.7% profit: **NOT ACHIEVED** by this realization —
Accumulate-side results are indistinguishable from or below coin flip.
By Joe's determinism criterion, this realization of kernel + governance
is therefore **not yet the correct one**. Thresholds were not tuned
toward the target at any point; the discrepancy is filed as fact.

## 7. Open faithfulness variants (discrete, in-repo, declared — NOT run;
each is one evaluation cycle, pending approval)

1. `uf_core` v1.4.0 realization: log field + γ-weighted S, λ-weighted U,
   density-based w, χ/ψ regime bands, structural-activity relevance —
   a second complete in-tree canonical realization of L2/L3.
2. UF-original Adaptive Gate Stabilization (docx §3.1): D(t)=‖ΔSEV‖ with
   τ(t)=τ_0+α·Var(SEV[t−w:t]) — the original design's own scale answer
   (removes the RAW/LOG scale pathology at its root).
3. The extinction finding as a governed AVOID/exit channel (it is the
   only slice with demonstrated forward structure).

Nothing is wired: no runner started, no page published, no book live.
Wiring happens only on explicit approval.
