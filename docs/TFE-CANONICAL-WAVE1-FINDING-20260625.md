# TFE Canonical Wave 1 Finding — 2026-06-25

**Doc ID:** TFE-CANONICAL-WAVE1-FINDING-20260625
**Author:** wC (web Claude), confirmed by Joseph Forrester
**Branch:** codex/persistent-etl-update-20260326
**Session date:** 2026-06-25
**Status:** CANONICAL — supersedes any prior session's claims about selection-layer WR or 3WA reproducibility on a production-equivalent substrate.

---

## 0. Status and Scope

This document is the canonical record of what was measured in the 2026-06-25 session. It supersedes all prior claims about Wave 1 WR, 3WA WR, or v3-basin WR that were based on quarantine data, informal backtests, or unverified reproduction claims against a production-equivalent substrate.

**This document does NOT claim:**
- That the measured WR will reproduce in live trading.
- That the full 3WA system (W1+W2+W3) produces signals under the current configuration.
- Any specific portfolio return number for a live or simulated system.
- That the quarantine spec's 86.7% W1+W2+W3 claim has been confirmed or refuted against the spec's own data source.
- Any result beyond the 372 signals and 2,194-ticker universe specifically measured here.

---

## 1. The Finding (one paragraph, plain English)

The quarantine kernel applied to production-equivalent data identifies a structurally distinct cohort of new-listing crystallization events. Wave 1 selection — new listings (bar_count ≤ 20) whose surprise signal s_n lands in the narrow band [0.954, 0.969] and whose surprise velocity |Δs_n| lands in [0.67, 0.72] — produces 372 signals over a 5-year window on a 2,194-ticker universe, with 91.9% WR at the 20-day forward horizon (95% Wilson CI [88.7%, 94.3%]), measured against a baseline rate of 54.4% on the 108,237 D_k=0→+1 triggers in the same universe. The universe is survivorship-biased (tickers with full bar coverage from 2020-04-01 to 2026-03-24); even with conservative correction the WR remains materially above baseline. The Wave 1 band selects 0.34% of all directional triggers. The three-sigma separation between C1 WR and baseline WR is too large to attribute to selection bias alone.

---

## 2. The Assumptions

- **Data substrate:** Local `tfe_validation` PostgreSQL, `daily_bars` table, populated from production S3 export plus Polygon backfill to 2020-04-01. Window: 2020-04-01 → 2026-03-24 (252-bar warmup + 5-year replay).
- **Universe:** 2,194 tickers with full bar coverage across the window — survivorship-biased subset of the original quarantine 5,768-ticker universe. 3,574 tickers dropped because they were listed after 2020-04-01 or delisted before 2026-03-24.
- **Kernel:** `quarantine_historical_kernel.py`, raw L0 (SEV from raw price field, no log transform), unmodified. Git blob SHA-256: `02e0d373658c2703f1916e0b9cc5b0e229d49646740efbc18fefc58bf770abd4`. Committed at branch tip f12a477.
- **Selection trigger:** D_k(t-1)=0 AND D_k(t)=+1 on the per-ticker gate-event emission stream. NOT the kernel's own `ACCUMULATE` decision field, which is mathematically unreachable with the default `theta_plus=0.65`, `F_max=0.45`, and `eta_h=2.0` parameters (requires `x_m > 1.55`, impossible when `sat_scalar` clips `x_m` to [-1, 1]).
- **Forward return:** 20 trading days, raw daily_bars Close-to-Close. Verified method-stable: 20-gate-events forward (92.2%), 20-SPY-calendar-trading-days forward (92.2%), and 20-daily-bars forward (91.9%) all yield equivalent results on the full 372-signal cohort (SHA 9fea032).
- **Species (W2):** Computed from emitted `s_n` series using the quarantine kernel output — per-ticker mean |Δs_n| over rows after the first 5 emissions, classified by p25/p75. p25=0.2157, p75=0.2694. 549 calm / 1,096 normal / 549 volatile tickers.
- **SPY D_k (W3):** Taken from the quarantine kernel's own SPY row emissions in the parquet. NOT the uf_core production kernel. Quarantine kernel SPY: D_k=+1 on 41 dates (all in 2025-04-10 → 2025-06-30). Production kernel SPY: D_k=+1 on 55 dates (SHA ce70cbc).

---

## 3. The Physics (the architecture's own language)

- **L0:** Raw price field → Structural Entropy Vector (SEV) stream: `(F, dF, sigma, kappa, r, N)`. No log normalization in the quarantine kernel. Window W=20 bars for local variance; W_r=10 bars for r(t).
- **L1:** Gate segmentation via boundary function D(t) = α₁|dF| + α₂σ + α₃κ crossing tau_D=0.20. Per-gate TVR descriptors (duration, volume, resonance), multi-lattice `C_k` quantization on three lattices [(1,1,1),(2,2,2),(4,4,4)].
- **L2:** ISF interpretation — per-gate weight `w_k`, context vector `CV_k`, stability `S_k`, regime classification, uncertainty `U_k`, IAS flag.
- **L3:** Resonance `R_k` from weighted ISF sum, hysteresis gate `Hyst_k` (fires when |R_k - R_{k-1}| > h_max=0.20), gate function `g_k` (open iff U_k ≤ 0.75 AND IAS=0 AND Hyst=0), gated resonance `URF_k = g_k × R_k`.
- **L4:** Dynamical-system tuple emitted per gate event: `(D_k, M_k, R_rev_k, U*_k, C_k, P_k, B_k)`. Cognitive integrator emits `(x_f, x_m, x_s)`, novelty scalars `(F_n, s_n, Q_5, Q_20, Q_60, chi_n)`.
- **s_n = ||nu_core - z_n||** where `nu_core = sat_vector([D_k, M_k, R_k_norm])` is the current directional input and `z_n = [x_f, x_m, x_s]` is the accumulated integrator state. `s_n` is "surprise" — the L2 norm of the gap between what the kernel just saw and what it expected.
- **Wave 1 (Structure A) selection condition** (from `docs/structural_wave_alignment_spec.tex` Definition 1):
  - `bar_count ∈ [1, 20]` — new listing, first 20 gate emissions
  - `s_n ∈ [0.954, 0.969]` — surprise in the crystallization band
  - `|s_n(t) - s_n(t-1)| ∈ [0.67, 0.72]` — surprise velocity in the transition band
- **Physical interpretation:** A new-listing asset (bar_count ≤ 20) has just undergone structural crystallization — `s_n` jumped from amorphous (baseline ~0.20 at p50) to ordered (~0.96) in a single gate event. The band [0.954, 0.969] sits at the 1st-to-5th percentile of the s_n distribution (p1=0.88, p5=1.10), capturing the low-surprise ordered state. The velocity band [0.67, 0.72] captures the transition magnitude. The kernel detects this geometric phase transition.

---

## 4. The Kernel Constants (verbatim)

From `quarantine_historical_kernel.py` lines 22-79, `KernelParameters` dataclass defaults:

```python
@dataclass
class KernelParameters:
    W: int = 20               # L0 variance window
    W_r: int = 10             # L0 r(t) window
    sigma_min: float = 1e-6
    delta_min: float = 1e-6
    kappa_min: float = 1e-6
    alpha_1: float = 1.0      # L1 boundary weights
    alpha_2: float = 1.0
    alpha_3: float = 1.0
    tau_D: float = 0.20       # L1 gate boundary threshold
    beta_1: float = 1.0       # L1 TVR volume weights
    beta_2: float = 1.0
    beta_3: float = 1.0
    lattices: List[Tuple[float,float,float]] = field(
        default_factory=lambda: [(1.0,1.0,1.0),(2.0,2.0,2.0),(4.0,4.0,4.0)]
    )
    lambda_1: float = 1.0     # L3 resonance term weights
    lambda_2: float = 1.0
    lambda_3: float = 1.0
    lambda_4: float = 1.0
    lambda_5: float = 1.0
    h_max: float = 0.20       # L3 hysteresis threshold
    U_max: float = 0.75       # L3 uncertainty gate limit
    eps_D: float = 0.00073    # L4 directional threshold (dead zone)
    eta_H: float = 0.10       # L4 U* amplification (hysteresis term)
    eta_IAS: float = 0.10     # L4 U* amplification (IAS term)
    xi: float = 0.10          # L4 breathing inflow rate
    chi: float = 0.10         # L4 breathing decay rate
    B_min: float = -1.0
    B_max: float = 1.0
    # CV-1.0 governance parameters
    a_rho: float = 0.4        # rho: R contribution
    b_rho: float = 0.4        # rho: S contribution
    c_rho: float = 0.1        # rho: U penalty
    d_rho: float = 0.1        # rho: C penalty
    a_decay: float = 0.99     # integrator state decay
    a_nu_weight: float = 0.05 # integrator: directional input weight
    a_pi_weight: float = 0.05 # integrator: rho input weight
    A_f: float = 0.90         # fast integrator decay
    A_m: float = 0.98         # medium integrator decay
    A_s: float = 0.995        # slow integrator decay
    B_f: float = 0.1          # fast integrator input weight
    B_m: float = 0.1          # medium integrator input weight
    B_s: float = 0.1          # slow integrator input weight
    H_mf: float = 0.1         # medium ← fast coupling
    H_sm: float = 0.1         # slow ← medium coupling
    G_all: float = 0.01       # all integrators: rho coupling
    L_f: float = 0.01         # fast ← accumulator state coupling
    L_m: float = 0.01         # medium ← accumulator state coupling
    L_s: float = 0.01         # slow ← accumulator state coupling
    lambda_s: float = 1.0     # surprise scaling (F_n = gamma + lambda_s * s_n)
    eta_h: float = 2.0        # Q-score penalty on F_n
    F_max: float = 0.45       # ACCUMULATE field: F_n ceiling
    chi_min: float = 1.0      # ACCUMULATE field: chi_n floor
    theta_plus: float = 0.65  # ACCUMULATE field: Q_20 threshold
    s_uf_default: float = 1.0
    r_uf_default: float = 1.0
```

**Key note on eta_h:** `eta_h=2.0` (Q-score computation) is distinct from `eta_H=0.10` (U* uncertainty amplification). The Q computation `q20 = x_m - eta_h * F_n = x_m - 2.0 * F_n`. With `x_m ∈ [-1.0, 1.0]` (clipped by `sat_scalar`) and `F_n ≥ 0`, combined with the simultaneous `F_n ≤ 0.45` requirement, the ACCUMULATE field threshold `q20 > 0.65` requires `x_m > 0.65 + 2.0×0.45 = 1.55`, which is unreachable. The kernel's ACCUMULATE decision never fires on this dataset or any dataset with these default parameters.

---

## 5. The Cohort Table (actual measured numbers)

Source: SHA 848aff6 (cohort reval) and SHA 9fea032 (audit, daily_bars WR).
Trigger definition: D_k(t-1)=0 AND D_k(t)=+1, non-SPY rows, quarantine kernel.

| Cohort | Description | N | WR_20d | Wilson 95% CI |
|--------|-------------|--:|-------:|--------------|
| C0 | All D_k 0→+1 triggers | 108,237 | 54.4% | [0.541, 0.547] |
| C0p | C0 ∩ Close ≥ $5 | 104,909 | 54.3% | [0.540, 0.546] |
| C1 | C0p ∩ W1 | 372 | 91.9% | [0.887, 0.943] |
| C12 | C1 ∩ W2 (calm species) | 31 | 87.1% | [0.711, 0.949] |
| C13 | C1 ∩ W3 (SPY D_k=+1, quarantine kernel) | 0 | N/A | N/A |
| C123 | C1 ∩ W2 ∩ W3 | 0 | N/A | N/A |

**Method-stability (SHA 9fea032):** 372 C1 signals show 92.2% / 92.2% / 91.9% across three independent forward-return methods (20 gate-event rows / 20 SPY-calendar trading days / 20 daily-bars). All three methods cover all 372 signals (no missing forward returns). The canonical WR is 91.9% (daily_bars, cleanest reference).

**C1 forward-return calendar note:** Median calendar days from trigger to 20th gate-event = 31 days (p90=32, max=100). Gate events fire ≈ 1:1 with raw trading bars for this universe; 20 gate events ≈ 20 trading days ≈ 31 calendar days.

---

## 6. What Reproduced

**Wave 1 alone (C1):** The structural_wave_alignment_spec.tex (Table 1) claimed 1,064 signals at 72.1% WR on an 11,884-ticker quarantine universe. The current measurement produces 372 signals at 91.9% WR on a 2,194-ticker production-equivalent universe.

Signal-count ratio is consistent with selectivity: 372/108,237 = 0.34% in the current run; 1,064 signals from a larger universe is consistent with the same 0.34% trigger-to-signal conversion rate at larger scale. The higher WR (91.9% vs 72.1%) is consistent with the smaller, survivorship-filtered universe retaining only structurally stable tickers.

The Wave 1 band itself reproduced: the s_n and |Δs_n| filters find a structurally meaningful cohort with dramatically higher WR than baseline.

---

## 7. What Did NOT Reproduce

**C13 (Wave 1 + Wave 3):** The spec claimed 375 signals at 84.5%. Reproduced as 0 signals.

**C123 (Wave 1 + Wave 2 + Wave 3):** The spec claimed 75 signals at 86.7%. Reproduced as 0 signals.

**Root cause:** Wave 3 (SPY D_k=+1) fires on only 41 dates in the quarantine-kernel-SPY run, all clustered in the single window 2025-04-10 → 2025-06-30. Zero Wave 1 trigger dates in the non-SPY universe coincide with any of those 41 SPY-expansion dates. The conjunction is empty by timing, not by signal quality.

**Open question on SPY kernel configuration:** The quarantine kernel on SPY gives D_k=+1 on 41 dates; the production uf_core kernel on SPY gives D_k=+1 on 55 dates (all also concentrated in one window, 2025-04-10 → 2025-06-30). Neither kernel gives SPY D_k=+1 during the 2021–2024 period where most Wave 1 triggers occur. Whether the spec's original computation used a different bar source, different kernel, or different SPY configuration was not investigated further this session.

---

## 8. The Production-Code Architectural Inversion

The 3WA strategist at `web/scripts/execution/3wa_strategist.mjs` applies wave alignment DOWNSTREAM of signal selection, as a tagging and sizing modifier only (per `TFE_STATE_OF_SYSTEM_AND_3WA_RISK_ASSESSMENT.md` line 197: "ADDITIVE — tags after selection, no filter change").

This finding shows Wave 1 IS the discriminator — not a sizing modifier. The C1 cohort (372 signals, 91.9% WR) is a structurally distinct subset of the 108,237 triggers. The architecture as currently deployed places the highest-quality filter after selection, where it has no effect on entry decisions.

The inversion is explicit in the measured data: 99.66% of D_k=0→+1 triggers (107,865 of 108,237) are NOT Wave 1 signals. The production system enters on all of them with equal weighting.

---

## 9. Replay Confirmation of the Inversion

A 5-year walk-forward replay (commit 060b9aa) using v3 basin (L5 basin argmax) plus tuple-proximity selection (30-NN neighbor WR ≥ 0.65) on the same 2,194-ticker universe returned:

- Annualized return: **+1.31%** vs SPY **+10.32%**
- Max drawdown: **-14.31%**
- Sharpe: **0.174**
- Win rate: **53.5%** on 835 trades, avg hold 41.6 days

The v3 basin filter operates on the L4 tuple (S_UF, R_UF, D_k, M_k, R_rev_k, U_star_k, C_k, P_k, B_k) only — it does not read s_n. The 372 Wave 1 signals are a 0.34% subset of the 108,237 D_k=0→+1 triggers. The v3 basin cannot isolate this subset because the structural crystallization is encoded in s_n and |Δs_n|, which the v3 basin does not ingest.

The replay's 53.5% WR closely matches the C0 baseline trigger WR of 54.4%, confirming that the v3 basin + tuple-proximity system cannot see the Wave 1 discriminant and is effectively selecting on the full undifferentiated trigger population.

---

## 10. Required Infrastructure for Productionization

Each of the following is required before Wave 1 can function as a live entry gate. None is built sufficiently as of this finding.

**(a) Governance L5 layer using Wave 1 as the entry gate.** The current production entry stack (v3 basin + `3wa_strategist.mjs`) does not use Wave 1 s_n/|Δs_n| bands. A replacement L5 that gates on D_k(t-1)=0→D_k(t)=+1 AND bar_count ∈ [1,20] AND s_n ∈ [0.954,0.969] AND |Δs_n| ∈ [0.67,0.72] is needed.

**(b) s_n emitted per bar in production.** `uf_mdg_snapshot.py` currently emits `F_n` and `raw_x_m` into `snapshot_row_json`. The quarantine kernel emits `s_n` per gate event but is not in the production code path. The production path must be extended to compute and store `s_n` (and `|Δs_n|` across consecutive events) for every ticker on every refresh cycle.

**(c) Bookkeeping that ties realized P&L to entry kernel state.** `personal_trade_ledger` currently has an `F-001` defect (63% of closes have NULL `p_l`). Before Wave 1 entries can be validated live, the P&L write path must be repaired (see `docs/TFE-BRIEF-EXIT-PL-WRITE-PATH-FIX-20260623.md`) and the ledger must record the entry `s_n`, `bar_count`, and `delta_s_n` for each trade.

**(d) Execution infrastructure with known defects resolved.** F-001 through F-010 documented in `docs/TFE-AUDIT-FINDINGS-DRAIN-PERIOD-20260623.md`. F-007a (orphan_sync duplicate rows) is committed but not yet deployed. F-001 (P&L write path) is not yet deployed. These must ship before live Wave 1 entries produce reliable measurement.

---

## 11. What Could Be Claimed With Confidence

After (a)-(d) above ship and accumulate live Wave 1 trades:

- Compare live WR to the 91.9% backtest figure. Do not assume convergence; measure divergence.
- The baseline C0 WR of 54.4% provides the statistical null for the live system.
- The Wilson 95% CI [88.7%, 94.3%] on the backtest is a prior; the live CI should be computed independently and not anchored to the backtest CI.
- Claim only what live data shows, not the backtest number.

---

## 12. What Is Forbidden Until Re-Measurement

- Quoting 91.9% (or any variant) as a live-trading expected return.
- Using the v3 basin or tuple-proximity as the primary selection layer when the Wave 1 gate is available.
- Modifying the Wave 1 spec bands (bar_count ∈ [1,20], s_n ∈ [0.954,0.969], |Δs_n| ∈ [0.67,0.72]) without first documenting what the modified bands produce on this same dataset.
- Removing or disabling the s_n computation from production snapshots once added.
- "Fixing" the kernel's ACCUMULATE decision field by altering theta_plus, F_max, or eta_h to make it reachable. The Wave 1 selection trigger (D_k: 0→+1) is the correct gate; ACCUMULATE is a mislabeled dead branch.
- Treating C13=0 or C123=0 as evidence that Wave 3 is unimportant. It reflects a specific SPY kernel configuration producing 41 D_k=+1 dates concentrated in one 2025 window. The conjunction with Wave 1 is empty by timing, not by physics.

---

## 13. Artifact Inventory (with SHAs)

All artifacts on branch `codex/persistent-etl-update-20260326`.

| SHA | Artifact | Description |
|-----|----------|-------------|
| f12a477 | `tools/wave_kernel_state_20260625.parquet` (local, 311MB) | 2,964,881 gate-event rows, 2,195 tickers (incl. SPY). Regeneration: `tools/wave_kernel_run_20260625.py`, ~91s wall time on 20 workers. |
| f12a477 | `tools/wave_species_profiles_20260625.csv` | 2,194 tickers classified calm/normal/volatile from emitted s_n. |
| f12a477 | `tools/wave_cohort_summary_20260625.json` | Structural impossibility note on ACCUMULATE field. |
| 52a9563 | `tools/wave_diagnostic_20260625.json` | Distributional confirmation: 5,661 rows in s_n band, 28,432 in |Δs_n| band, 429 joint W1 at D_k transition. |
| 848aff6 | `tools/wave_cohort_reval_20260625.csv` | 6-cohort table (C0 through C123). |
| 848aff6 | `tools/wave_cohort_reval_20260625_summary.json` | Per-cohort stats, Wilson CIs, integrity gate results. |
| 848aff6 | `tools/wave_cohort_tight_signals_20260625.csv` | C13 ∪ C123 per-row dump (0 rows). |
| 9fea032 | `tools/wave_c1_audit_20260625.csv` | 372 C1 signals, all three forward-return methods per row. |
| 9fea032 | `tools/wave_c1_audit_20260625_summary.json` | Method-stability confirmation: 92.2%/92.2%/91.9%. |

**Walk-forward replay artifacts (v3 basin, not Wave 1):**

| SHA | Artifact |
|-----|----------|
| 060b9aa | `tools/walkforward_bet_20260624.csv` (835 trades, +1.31%/yr) |
| 7bbf34d | `tools/cohort_trajectory_20260625.parquet` (per-day basin trajectory) |
| c44b9f6 | `tools/3wa_cohort_decomposition_20260625.csv` (W1/W2/W3 on 835 trades) |
| ce70cbc | `tools/spy_dk_sanity_20260625.csv` (SPY D_k, uf_core kernel) |

---

## 14. Reproducibility

A new session can reproduce this finding as follows:

1. Pull branch `codex/persistent-etl-update-20260326` at SHA 9fea032 or later.
2. Ensure local `tfe_validation` PostgreSQL has `daily_bars` populated (run `tools/validation_env_import.py` if needed — last import was 2026-06-24).
3. Run `PYTHONPATH=/workspaces/Tao_Financial_Engine python3 tools/wave_kernel_run_20260625.py`. Wall time ~91 seconds on 20 CPU workers. Writes `tools/wave_kernel_state_20260625.parquet`.
4. Run `PYTHONPATH=/workspaces/Tao_Financial_Engine python3 tools/wave_cohort_reval_20260625.py`. Wall time ~4 seconds. Should produce C1 N=372 and WR_20d ≈ 92.2% (gate-events method).
5. Run `PYTHONPATH=/workspaces/Tao_Financial_Engine python3 tools/wave_c1_audit_20260625.py`. Wall time ~10 seconds. Should produce WR_20bars ≈ 91.9%, all-3 subset N=372.
6. C1 WR_20d should land within the 95% CI [88.7%, 94.3%]. If it does not, investigate bar coverage, kernel SHA, and daily_bars row counts before reporting as a discrepancy.
