# Tao Financial Engine Portfolio Manager Design Document — Deployment v1.0

**Doc ID:** TAO_FINANCIAL_ENGINE_PORTFOLIO_MANAGER_DESIGN_DOCUMENT_DEPLOYMENT_VERSION
**Status:** DEPLOYMENT v1.0
**Effective date:** 2026-06-25
**Author:** wC (web Claude) + c1 (Claude Sonnet 4.6), confirmed by Joseph Forrester
**Supersedes:** any prior portfolio-manager design fragment in docs/

---

## 0. Document Status and Authority

**Authority:** Joseph Forrester (canonical). All parameter changes require explicit approval per KERNEL_PHILOSOPHY.md §8.7.

**This document supersedes:**
- Any prior session's portfolio design fragments in docs/
- Any prior "deployment plan" or "next steps" notes in PROJECT_STATE.md §4 predating 2026-06-25
- The informal walk-forward replay configuration in tools/walkforward_bet_20260624.py (which was an experiment, not a deployment plan)

**Required reviews before merge to main:**
- Joseph Forrester (canonical authority, all sections)
- Engineering review of Gate D2 (Wave 1 filter implementation) against spec §4
- Engineering review of Gate D4 (bookkeeping forward fixes) against audit findings

**Hard-stop constraint:** No live deployment (Gate D7) until all sections marked `STATUS: BUILT-AND-TESTED`. Sections marked `STATUS: NOT BUILT` require code before deployment.

---

## 1. Architecture Overview

The TFE Portfolio Manager is a new-listing structural crystallization detector. The kernel identifies the precise moment a newly-listed asset undergoes geometric phase transition from amorphous to ordered structural state. The portfolio manager enters at that event, holds 20 trading days, and exits on structural decoherence or catastrophic loss.

```
                            ┌─────────────────────────────────┐
                            │         DATA PIPELINE           │
  Polygon daily bars ──────►│  raw bars → L0 SEV stream       │
  (raw, NOT log)            │  (quarantine_historical_kernel.  │
                            │   py :: compute_l0_sev, ln 121)  │
                            └──────────────┬──────────────────┘
                                           │
                            ┌──────────────▼──────────────────┐
                            │       KERNEL LAYERS L0–L4       │
                            │  L1 gate segmentation (τD=0.20) │
                            │  L2 ISF (U_k, IAS_k, regime)    │
                            │  L3 resonance R_k, g_k, URF_k   │
                            │  L4 tuple: D_k,M_k,B_k,U*_k,   │
                            │           C_k,P_k,R_rev_k       │
                            └──────────────┬──────────────────┘
                                           │
                            ┌──────────────▼──────────────────┐
                            │    COGNITIVE SCALARS            │
                            │  x_f, x_m, x_s integrators     │
                            │  s_n = ||nu_core − z_n||        │  ← STATUS: NOT IN PROD
                            │  F_n = γ + λ_s·s_n             │  ← in prod (uf_mdg_snapshot.py)
                            │  Q_5, Q_20, Q_60, chi_n        │
                            └──────────────┬──────────────────┘
                                           │
                            ┌──────────────▼──────────────────┐
                            │       WAVE 1 SELECTION          │
                            │  D_k(t−1)=0 AND D_k(t)=+1      │
                            │  bar_count ≤ 20                 │
                            │  s_n ∈ [0.954, 0.969]          │
                            │  |Δs_n| ∈ [0.67, 0.72]         │  ← STATUS: NOT BUILT
                            └──────────────┬──────────────────┘
                                           │ 372 signals / 5yr
                            ┌──────────────▼──────────────────┐
                            │     CAPITAL ALLOCATOR           │
                            │  equal-weight, max 30 positions │
                            │  equity × 1.5% / trade (v1.0)  │
                            └──────────────┬──────────────────┘
                                           │
                            ┌──────────────▼──────────────────┐
                            │      ORDER SUBMISSION           │
                            │  next-day market open (Alpaca)  │
                            │  bracket: TP ceiling, SL -10%  │
                            └──────────────┬──────────────────┘
                                           │
                            ┌──────────────▼──────────────────┐
                            │     EXECUTION MONITOR           │
                            │  sentinel_monitor.mjs           │
                            │  EXIT-F (−10%), EXIT-R9 (7d),  │
                            │  EXIT-B (D_k↓), EXIT-C (τ),    │
                            │  EXIT-TIME (20d default v1.0)  │
                            └──────────────┬──────────────────┘
                                           │
                            ┌──────────────▼──────────────────┐
                            │        BOOKKEEPING              │
                            │  personal_trade_ledger (RDS)    │
                            │  P&L at fill; equity curve EOD  │
                            └─────────────────────────────────┘
```

**Source of Truth:** This document; docs/TFE-CANONICAL-WAVE1-FINDING-20260625.md (SHA e2030e2).

---

## 2. Empirical Foundation

The deployment design is grounded in one measured result. All constants and sizing in §§4–7 reference this measurement.

**Cohort C1 result (the deployment justification):**
- N = 372 signals over 5 years on 2,194-ticker production-equivalent universe
- WR_20d = **91.9%** (20 daily-bars forward return method, cleanest reference)
- Wilson 95% CI: **[88.7%, 94.3%]**
- Measurement period: 2021-04-01 to 2026-03-24
- Forward-return method stability: 91.9%–92.2% across three independent methods (20 gate-events / 20 SPY-calendar trading days / 20 daily-bars) on all 372 signals — SHA 9fea032

**Baseline C0 (null):**
- N = 108,237 D_k=0→+1 triggers, WR_20d = 54.4%, Wilson 95% CI [0.541, 0.547]
- C1 selects 0.34% of triggers; WR is 37.5 pp above baseline

**Universe caveats:**
- Survivorship-biased: 3,574 of 5,768 quarantine tickers dropped (listed after 2020-04-01 or delisted before 2026-03-24)
- Conservative post-correction WR envelope: 80–90% (not measured; based on partial survivorship adjustment)
- Live trading will measure something else; cite live WR only, not backtest figure, for investor-facing claims

**Full cohort table:**

| Cohort | Description | N | WR_20d | Wilson 95% CI |
|--------|-------------|--:|-------:|--------------|
| C0 | All D_k 0→+1 triggers | 108,237 | 54.4% | [0.541, 0.547] |
| C0p | C0 ∩ Close ≥ $5 | 104,909 | 54.3% | [0.540, 0.546] |
| **C1** | **C0p ∩ W1** | **372** | **91.9%** | **[0.887, 0.943]** |
| C12 | C1 ∩ W2 (calm species) | 31 | 87.1% | [0.711, 0.949] |
| C13 | C1 ∩ W3 (SPY D_k=+1) | 0 | N/A | N/A |
| C123 | C1 ∩ W2 ∩ W3 | 0 | N/A | N/A |

C13 = C123 = 0 because the quarantine kernel's SPY D_k=+1 fires on only 41 dates, all in 2025-04-10 → 2025-06-30; none coincide with Wave 1 trigger dates. W3 is not used as a v1.0 selection condition (§15).

**Source of Truth:** tools/wave_cohort_reval_20260625_summary.json (SHA 848aff6); tools/wave_c1_audit_20260625_summary.json (SHA 9fea032); docs/TFE-CANONICAL-WAVE1-FINDING-20260625.md (SHA e2030e2).

---

## 3. Kernel Specification

**STATUS: BUILT — quarantine_historical_kernel.py; NOT IN PROD for s_n emission**

### L0 — Raw SEV Stream

`compute_l0_sev()` — quarantine_historical_kernel.py line 121

```
For each bar t:
  dF_t     = F_t − F_{t−1}
  sigma_t  = mean((F_window − F_bar)²)   [window W=20]
  kappa_t  = |F_{t+1} − 2F_t + F_{t−1}|
  r_t      = psi_r(F[t-W_r:t])            [W_r=10]
  N_t      = 1 iff sigma<σ_min AND |dF|<δ_min AND kappa<κ_min, else 0
```

**Raw prices, NOT log.** Production uf_mdg_snapshot.py uses log(F+ε) — this divergence from the quarantine kernel is documented in KERNEL_PHILOSOPHY.md §5. The Wave 1 measurement (SHA 848aff6) used the quarantine kernel with raw prices. Any production s_n computation must also use raw prices.

### L1 — Gate Segmentation

`segment_l1_gates()` — quarantine_historical_kernel.py line 153

```
Boundary function: D(t) = α₁·|dF| + α₂·σ + α₃·κ
Gate fires when: D(t) ≥ τ_D = 0.20   [strict ≥; not >]
Per-gate: TVR = (T, V, R), C_k = |{quantized lattice points}|
Multi-lattice: (1,1,1), (2,2,2), (4,4,4)
delta_g = ||μ_k − μ_{k−1}|| (gate transition magnitude)
```

### L2 — ISF Interpretation

`compute_l2_isf()` — quarantine_historical_kernel.py line 202

```
w_k   = V_k / V_max
S_k   = 1 / (1 + C_k + delta_g)    [clipped 0–1]
U_k   = 0.1·C_k + 0.1·delta_g + 0.2·N_gate   [clipped 0–1]
IAS_k = 1 iff U_k > 0.80 OR delta_g > 2.0, else 0
Reg_k = "TRANSITIONAL" if C_k > 1, else "STABLE"
```

### L3 — Resonance

`compute_l3_resonance()` — quarantine_historical_kernel.py line 228

```
Z     = λ₁ + λ₂ + λ₃ + λ₄ + λ₅  = 5.0
R_k   = (1/Z) · (λ₁·w + λ₂·||CV||/CV_max + λ₃·S + λ₄·1/(1+C) + λ₅·(1−U))
Hyst_k = 1 iff |R_k − R_{k−1}| > h_max=0.20, else 0
g_k   = 1 iff U_k ≤ U_max=0.75 AND IAS=0 AND Hyst=0, else 0
URF_k = g_k · R_k
```

### L4 — Dynamical Tuple

`compute_l4_dsf()` — quarantine_historical_kernel.py line 262

```
delta_R = URF_k − URF_{k−1}
D_k     = +1 if delta_R >  eps_D=0.00073
         = −1 if delta_R < −eps_D
         =  0 otherwise
M_k     = URF_k − 2·URF_{k−1} + URF_{k−2}
Rev_k   = 1 iff D_k · D_{k−1} < 0
U*_k    = clip(U_k + η_H·Hyst_k + η_IAS·IAS_k, 0, 1)
P_k     = |D_k − D_{k−1}|
B_k     = clip(B_{k−1} + ξ·(1−U*_k)·delta_R − χ·U*_k, −1, 1)
```

### Snapshot State Row Variables

`build_state_rows()` — quarantine_historical_kernel.py lines 337–421

```
nu_core = sat_vector([D_k, M_k, R_k_norm])   [clipped to −1..1]
z_n     = [x_f, x_m, x_s]                    [integrator state]
s_n     = ||nu_core − z_n||                   [surprise, ln 376]
F_n     = γ + λ_s · s_n                       [baseline F_n term — quarantine_historical_kernel.py:377]
  where γ = 0.5 · (U*_k + (1 − rho))

Q_20  = dot([0,1,0], z_n) − η_h · F_n = x_m − 2.0·F_n
chi_n = 1.0 iff sign(Q_5)=sign(Q_20)=sign(Q_60), else 0.0
```

### Full Constants Table

Verbatim from quarantine_historical_kernel.py lines 22–79, `KernelParameters` defaults:

| Parameter | Value | Layer | Purpose |
|-----------|------:|-------|---------|
| W | 20 | L0 | Variance window |
| W_r | 10 | L0 | r(t) window |
| sigma_min | 1e-6 | L0 | Null-state threshold |
| delta_min | 1e-6 | L0 | Null-state threshold |
| kappa_min | 1e-6 | L0 | Null-state threshold |
| alpha_1/2/3 | 1.0 | L1 | Boundary function weights |
| tau_D | 0.20 | L1 | Gate boundary threshold |
| beta_1/2/3 | 1.0 | L1 | TVR volume weights |
| lattices | (1,1,1),(2,2,2),(4,4,4) | L1 | Multi-lattice quantization |
| lambda_1..5 | 1.0 | L3 | Resonance term weights |
| h_max | 0.20 | L3 | Hysteresis threshold |
| U_max | 0.75 | L3 | Uncertainty gate limit |
| eps_D | 0.00073 | L4 | Directional dead zone |
| eta_H | 0.10 | L4 | U* hysteresis amplification |
| eta_IAS | 0.10 | L4 | U* IAS amplification |
| xi | 0.10 | L4 | Breathing inflow rate |
| chi | 0.10 | L4 | Breathing decay rate |
| B_min / B_max | −1.0 / 1.0 | L4 | Breathing state bounds |
| a_rho | 0.4 | CV | rho: R contribution |
| b_rho | 0.4 | CV | rho: S contribution |
| c_rho | 0.1 | CV | rho: U penalty |
| d_rho | 0.1 | CV | rho: C penalty |
| a_decay | 0.99 | CV | Integrator state decay |
| a_nu_weight | 0.05 | CV | Integrator: directional weight |
| a_pi_weight | 0.05 | CV | Integrator: rho weight |
| A_f / A_m / A_s | 0.90 / 0.98 / 0.995 | CV | Fast/medium/slow integrator decay |
| B_f / B_m / B_s | 0.1 | CV | Integrator input weights |
| H_mf / H_sm | 0.1 | CV | Cross-integrator coupling |
| G_all | 0.01 | CV | All integrators: rho coupling |
| L_f / L_m / L_s | 0.01 | CV | Accumulator state coupling |
| lambda_s | 1.0 | CV | Surprise scaling |
| **eta_h** | **2.0** | CV | **Q-score F_n penalty** (≠ eta_H=0.10) |
| F_max | 0.45 | CV | ACCUMULATE field F_n ceiling |
| chi_min | 1.0 | CV | ACCUMULATE field chi_n floor |
| theta_plus | 0.65 | CV | ACCUMULATE field Q_20 threshold |
| s_uf_default | 1.0 | CV | Default S_UF |

**ACCUMULATE field note:** The kernel's own `Decision == "ACCUMULATE"` is unreachable with these defaults. `Q_20 > theta_plus=0.65` requires `x_m > 0.65 + eta_h·F_n = 0.65 + 2.0·F_n ≥ 1.55` since `F_n ≥ F_min > 0`. But `sat_scalar` clips `x_m` to `[−1.0, 1.0]`. The Wave 1 selection trigger (D_k: 0→+1) is the correct entry gate. Do not modify `eta_h`, `theta_plus`, or `F_max` to make ACCUMULATE reachable.

**Source of Truth:** quarantine_historical_kernel.py (git blob SHA `02e0d373658c2703f1916e0b9cc5b0e229d49646740efbc18fefc58bf770abd4`).

---

## 4. Selection Layer (Wave 1 as Entry Gate)

**STATUS: NOT BUILT. Requires new file web/scripts/wave1_entry_filter.mjs and Python mirror tools/wave1_entry_filter.py.**

### Accumulate Transition Trigger

For every non-SPY ticker, on every emitted gate event t:

```
is_trigger(i, t) = (D_k_i(t−1) == 0) AND (D_k_i(t) == +1)
```

where t−1 is the immediately prior gate-event emission for ticker i (NOT the prior calendar day). No trigger for the first emitted row per ticker (no prior D_k exists).

### Wave 1 Condition — Structure A

From docs/structural_wave_alignment_spec.tex Definition 1, lines 203–211 (eq:newlisting, eq:ordered, eq:jump):

```
bar_count_i(t) ∈ [1, 20]                        (eq:newlisting)
s_n_i(t)       ∈ [0.954, 0.969]                 (eq:ordered)
|s_n_i(t) − s_n_i(t−1)| ∈ [0.67, 0.72]        (eq:jump)
```

**Entry signal fires iff:** `is_trigger(i,t) == True` AND all three Wave 1 conditions hold.

**Minimum price gate:** `Close_i(t) >= 5.00` (USD). Applied after W1, before capital allocation.

### Mar 26 Supplementary Cognitive Gates (Stage 2, NOT in v1.0)

From recovered_versions/tfe_l5_mar26_recovered.py:

```
gate_count_i(t) >= 10          (line 15: min_gate_count=10)
F_n_i(t)       <= 1.65
raw_x_m_i(t)   <= 0.50         (= x_m; see uf_mdg_snapshot.py ln 371-373)
R_rev_k_i(t)   == 0
M_k_i(t)       >= 0
B_k_i(t)        > B_k_i(t−1)
```

These are not applied in v1.0. They tighten C1 further when applied (tested against quarantine signals). Reserved as a future lever once C1 baseline is established.

**Source of Truth:** docs/structural_wave_alignment_spec.tex (Definition 1, lines 203–211); recovered_versions/tfe_l5_mar26_recovered.py (Stage 2 conditions); KERNEL_PHILOSOPHY.md §5 (physics interpretation).

---

## 5. Capital Allocation

**STATUS: PARTIALLY BUILT — capital_allocator.mjs exists; equal-weight per-position model requires update.**

### v1.0 Allocation Model

Current production code (web/scripts/execution/capital_allocator.mjs line 11):
```javascript
const RISK_PCT_DEFAULT = 1.5;   // 1.5% of vault equity per trade
const RISK_PCT_MAX     = 5.0;
```

This yields `$1,500` per position on a $100K portfolio. This is NOT equal-weight/30.

**v1.0 design target:** Equal-weight, equity / 30 per position at signal emission time.

```
alloc_i = vault_equity_at_signal / max_concurrent_positions
        = vault_equity_at_signal / 30
```

`capital_allocator.mjs` requires update to implement this model. Until then, 1.5% default applies.

### Position Capacity Gate

Maximum concurrent open positions: 30.
Source: web/scripts/execution/3wa_strategist.mjs line 233:
```javascript
computeRegimeExposure(spyDk, openCount, 30, 0)
```

### Other Constraints

- Cash always permitted; no leverage; no shorts in v1.0.
- No rebalancing of existing positions on new signal day.
- If `alloc_i > available_cash`, skip the signal for this cycle (do not borrow).

**Stage 2 sizing (deferred, NOT in v1.0):** W1+W3 entries get 1.5× standard; W1+W2+W3 entries get 2× standard. Requires W3 to be validated first (C13 = 0 in current measurement).

**Source of Truth:** web/scripts/execution/capital_allocator.mjs (current); §2 of this document (target design).

---

## 6. Order Submission

**STATUS: BUILT — entry_timing_watcher.mjs, alpaca_bridge.mjs**

- **Entry timing:** Next-day market open after signal emission. NYSE calendar from market_calendar.mjs; holiday-aware through 2030.
- **Order type:** Bracket (OCO) DAY order via Alpaca REST (alpaca_bridge.mjs line 517: `order_class: "bracket"`).
- **Bracket SL:** −10% from entry price (hard-wired exit, same as EXIT-F floor). Source: alpaca_bridge.mjs line 587: `CH2_STOP_LOSS_MULT = 1.0`.
- **Bracket TP ceiling:** Wide (not intended as exit trigger; sentinel handles real exits). Source: alpaca_bridge.mjs line 586: `CH2_TAKE_PROFIT_MULT = 1.0`.
- **Bracket minimum width:** 5% (alpaca_bridge.mjs line 588: `CH2_MIN_BRACKET_PCT = 0.05`).
- **ATR source:** 14-day ATR from daily bars; minimum 2% of price fallback (alpaca_bridge.mjs line 170).
- **No after-hours entries.** Market-open only.

**Source of Truth:** web/scripts/execution/entry_timing_watcher.mjs; web/scripts/execution/alpaca_bridge.mjs; web/scripts/execution/market_calendar.mjs.

---

## 7. Exit Logic

**STATUS: PARTIALLY BUILT. EXIT-F and EXIT-R9 and EXIT-B active. EXIT-TIME (20d default) NOT BUILT. EXIT-A and EXIT-H are removed from production and must be reinstated or replaced.**

All exits evaluated in this exact order per sentinel cycle (market hours):

### EXIT-F — Catastrophic Floor (always active)

```
if (current_price − entry_price) / entry_price ≤ −0.10:
    market sell immediately
```

Source: sentinel_monitor.mjs line 762–818. Fires during market hours only (line 773). Cannot be disabled for Wave 1 positions. Threshold −0.10 applies to signal_class CH2 (line 777).

### EXIT-R9 — Minimum Hold Guard (7 calendar days)

```
if age_days < 7:
    suppress all LOSING exits (EXIT-A, EXIT-B, EXIT-C, EXIT-TIME)
    allow WINNING exits regardless
    EXIT-F still always fires
```

`MIN_HOLD_DAYS = 7` — sentinel_monitor.mjs line 112. Production data (May 26 audit): 85% of D_k collapse exits recovered at 10-20 days; optimal hold projects 67.1% WR from 41.3%. Source: TFE_AUDIT_MAY26_2026.md line 94-98.

### EXIT-A — Structural Acceleration Complete

**STATUS: REMOVED from production (sentinel_monitor.mjs line 868). Must be reinstated for v1.0.**

Design for v1.0:
```
if S_UF_i(t) >= 0.75 AND P&L >= 0:    (winning position)
    market sell at next open
```

Historical implementation at sentinel_monitor.mjs line 832 (comment references). Was removed because it "capped winners at +3.25% avg / 4.4 days" — this happened under CH2/CH3 signal classes where holds were shorter. Wave 1 positions have a structural basis for early exit when acceleration is complete. Reinstate with the winning-position-only constraint.

### EXIT-H — Structural Harvest (midpoint profit take)

**STATUS: REMOVED from production (sentinel_monitor.mjs line 936). Retain as REMOVED in v1.0. Replaced by EXIT-TIME.**

Was: exit at +5% gain when τ_out midpoint reached. Removed because it mechanically capped winners. EXIT-TIME at 20d covers the horizon without a profit-cap.

### EXIT-B — Directional Collapse (active in production)

```
if D_k_i(t) ≠ +1:
    if age_days >= 7 OR P&L >= 0:
        market sell at next open
    else:
        hold (EXIT-R9 guard active on young losing positions)
```

Source: sentinel_monitor.mjs lines 877-882. For Wave 1 positions (entered on D_k: 0→+1), EXIT-B fires when D_k leaves +1 — symmetric with the entry trigger.

### EXIT-C — τ Exhaustion (active in production)

```
tau_out = floor(tau_in / 3)
if age_days > tau_out:
    if age_days >= 7 OR P&L >= 0:
        market sell at next open
    else:
        hold (EXIT-R9 guard)
```

Source: sentinel_monitor.mjs lines 887-966. τ_in = consecutive D_k≠+1 compression days; τ_out = recovery window. Structural energy dissipated → close.

### EXIT-TIME — 20-Day Default

**STATUS: NOT BUILT. Must be added to sentinel_monitor.mjs for v1.0.**

```
if age_days >= 20:
    market sell at next open
```

This is the primary exit for Wave 1 positions in v1.0 since the structural exit assessment (EXIT-STRUCTURAL) is not yet built. The 20-day horizon matches the C1 WR measurement (SHA 9fea032).

### EXIT-STRUCTURAL — Full-Tuple Deterioration (Stage 2, NOT IN v1.0)

Spec exists at docs/structural_exit_assessment_spec.tex (Horse/Herd/Distance). Code not built. Deferred to Stage 2. EXIT-TIME covers the exit horizon until then.

### Deprecated Exits

- **EXIT-D** (trailing profit ratchet): REMOVED. Capped winners at first pullback past +5%. Source: sentinel_monitor.mjs line 925.
- **EXIT-S** (structural similarity threshold): REMOVED. Used EXIT_CUT_WR=0.50 / EXIT_HOLD_WR=0.55 with no derivation. Source: sentinel_monitor.mjs line 857.
- **SPY flip exit** (sentinel_monitor.mjs line 651): Not applied to Wave 1 positions. Wave 1 entry does not use SPY D_k as gate; symmetrically, SPY D_k flip should not exit a Wave 1 position that was entered on structural crystallization alone.

**Audit basis for deprecations:** TFE_AUDIT_MAY26_2026.md line 62-63: Day-0 exits WR=24.2% vs held >0 days WR=57.4%. Aggressive intraday exits caused the production drain. EXIT-TIME at 20d is the correct horizon for Wave 1 (measured in §2).

**Source of Truth:** web/scripts/execution/sentinel_monitor.mjs (current exits); TFE_AUDIT_MAY26_2026.md (deprecation justification); docs/structural_exit_assessment_spec.tex (Stage 2 spec).

---

## 8. Data Pipeline

**STATUS: PARTIALLY BUILT. s_n emission is NOT in production snapshot.**

- **Bar source:** Polygon daily bars. Raw prices for kernel computation. Adjusted bars for equity valuation and forward return labeling.
- **Nightly refresh:** run_refresh_with_l5_learning.py — triggers pre-market kernel recompute, emits kernel tuple to runtime_decisions_history.
- **Universe maintenance:** Weekly; IPOs added by ticker add-list; delistings auto-closed at last available price.
- **Bar window:** Minimum 20 bars (L0 window W=20) for SEV computation; 252 bars for stable L4 convergence.

### REQUIRED CHANGE: s_n Emission to Production Snapshot

The quarantine kernel computes `s_n = ||nu_core − z_n||` at line 376. The production `build_snapshot_state_row()` in uf_mdg_snapshot.py computes `surprise` at line 455:

```python
# uf_mdg_snapshot.py line 455 (existing):
surprise = float(np.linalg.norm(nu_core - z_n))
F_n_val = float(gamma + (_KP_lambda_s * surprise))
```

The `surprise` value exists but is NOT emitted to `snapshot_row_json`. Currently only `F_n` and `raw_x_m` are emitted (line 796). **ACTION REQUIRED:** extend the snapshot at line 796+ to include:

```python
"s_n": F_n_last,       # WRONG — this is surprise, not F_n
# Correct: the surprise variable before F_n computation
"s_n": surprise_last,  # new field: raw surprise value
```

(The variable name in uf_mdg_snapshot.py is `surprise`, not `s_n`; rename during emission for consistency with quarantine kernel output column name.)

Without s_n in the production snapshot, Wave 1 selection cannot execute in the production path.

**Source of Truth:** uf_mdg_snapshot.py (lines 360–462); quarantine_historical_kernel.py line 376; tools/validation_env_refresh.py; run_refresh_with_l5_learning.py.

---

## 9. Bookkeeping and Ledger

**STATUS: BLOCKED on F-001, F-002, F-003 fixes. Deployed migrations 007+008 (HTBK).**

- **Single source of truth:** `personal_trade_ledger` table in production RDS.
- **Provenance chain:** `signal_emission_id → entry_order_id → entry_fill_id → bracket_oco_id → exit_order_id → exit_fill_id`.
- **P&L computation:** `(exit_fill_price − entry_fill_price) / entry_fill_price` at exit-fill time. **NOT** at order submission.
- **Daily mark-to-market:** Post-close EOD price from Polygon, write to equity_curve table.
- **Contaminated ledger:** Current drain-period ledger (19 positions, kill switch ON) must be archived before fresh-ledger initialization.

### Required Fixes Before Fresh Ledger

**F-001 (BLOCKS):** 63% of closes have NULL p_l. Exit P&L not written at fill time. Fix per docs/TFE-BRIEF-EXIT-PL-WRITE-PATH-FIX-20260623.md. Three sequenced deploys: forward fix → backfill → spec update.

**F-002 (BLOCKS):** `sentinel_exit_order_id` holds submit-intent, not fill-truth (47% wrong). Must be overwritten with fill-confirmed exit order at `filled_avg_price` resolution.

**F-003 (BLOCKS):** Duplicate row write paths — 35 groups, 134 rows, ~30% of population since Apr 7. Source: `orphan_sync` ungated reconciliation. F-007a fix committed (SHA 29bf93d) but not yet deployed to ECS — deploy this before any fresh-ledger work begins.

**F-005 (RESOLVED):** HTBK phantom twin — migrations 007+008 deployed 2026-06-24. Verified per SHA efdc3cd.

**Forbidden ledger practices:**
- No NULL p_l on closed positions.
- No duplicate writes (orphan_sync gate must be enforced).
- No DAY TIF on exit orders (use GTC or IOC).
- No substitution of Alpaca portfolio value for ledger P&L.

**Required new fields for Wave 1 entries (not yet in schema):**
- `signal_s_n`: snapshot s_n value at trigger
- `signal_bar_count`: bar_count at trigger
- `signal_delta_s_n`: |Δs_n| at trigger

**Source of Truth:** docs/TFE-BRIEF-EXIT-PL-WRITE-PATH-FIX-20260623.md; docs/TFE-AUDIT-FINDINGS-DRAIN-PERIOD-20260623.md (F-001 through F-010).

---

## 10. Execution Environment and Reliability

**STATUS: BUILT (ECS, RDS, Alpaca paper). F-007a deploy pending.**

- **Deployment target:** AWS ECS (`tfe-web-cluster`, `tfe-web-service-lb`). Task definition `tfe-web-task` (current: :551).
- **Database:** AWS RDS PostgreSQL (`tfe-prod-postgres.c6vogauo4y6b.us-east-1.rds.amazonaws.com`).
- **Trading API:** Alpaca paper → Alpaca live (after Gate D6).
- **Kill switch:** `TFE_ENTRIES_HALTED='1'` in ECS task definition environment. Currently ON. Must remain ON until Gate D5 (fresh ledger).

### Process Model

| Process | File | Cadence | Purpose |
|---------|------|---------|---------|
| Sentinel daemon | sentinel_daemon.mjs | Continuous, market hours | Exit monitoring |
| Sentinel monitor | sentinel_monitor.mjs | Every 60s (market hours) | Exit execution |
| PEE-1 runner | pee1_runner.mjs | Every 15 min (market hours) | Entry submission |
| Overnight refresh | run_refresh_with_l5_learning.py | Nightly | Kernel recompute, snapshot emission |

### Reliability Requirements

- **F-007a orphan_sync guard** (sentinel_monitor.mjs line 544): committed SHA 29bf93d, NOT YET DEPLOYED. This must be the first ECS deploy before any other work. Without it, `orphan_sync` continues writing duplicate rows every cycle while kill switch is ON.
- **Cross-process kill cooldown:** DB-persisted 15-min window prevents duplicate kills after sentinel exits a position. Source: pee1_runner.mjs (kill_cooldown check).
- **NYSE holiday calendar:** market_calendar.mjs — computed rules, verified through 2030, 37 test cases.

**Source of Truth:** web/scripts/execution/sentinel_daemon.mjs; pee1_runner.mjs; market_calendar.mjs; DEPLOYMENT_REFERENCE.md.

---

## 11. Risk Limits and Governance

- **Per-position max loss:** −10% (EXIT-F floor, always active, cannot be disabled).
- **Portfolio max concurrent positions:** 30 (computeRegimeExposure, 3wa_strategist.mjs line 233).
- **Portfolio cash floor:** 5% of equity at all times. If available cash < 5%, no new entries even if signals fire.
- **Daily max new entries:** 5. Prevents over-concentration when multiple new-listing crystallization events cluster (e.g., post-earnings IPO windows).
- **Universe drift:** Weekly review. Any ticker delisted automatically closed at last available Polygon close.
- **Per-asset position cap:** 1/30 of equity. No averaging down. No second position on same ticker while first is open.
- **Parameter authority:** Joseph Forrester is canonical authority for any change to the Wave 1 bands (bar_count, s_n, |Δs_n|), capital allocation model, exit thresholds, or kernel constants. LLM-proposed changes require explicit approval per KERNEL_PHILOSOPHY.md §8.7.

**Source of Truth:** This document; KERNEL_PHILOSOPHY.md §8.

---

## 12. Deployment Sequence

Each gate must be `BUILT-AND-TESTED` before the next begins. No skipping.

### Gate D1 — s_n Emission in Production Snapshot
**STATUS: NOT BUILT**

File: `uf_mdg_snapshot.py`
Change: emit `s_n = surprise` to `snapshot_row_json` alongside `F_n` and `raw_x_m`

Test: 30-day sample of production snapshots. Verify `s_n` values match quarantine kernel output for the same (ticker, date) within 0.001 absolute tolerance on a 50-ticker sample. Confirm `s_n` and `|Δs_n|` (consecutive-row diff) are present in `runtime_decisions_history.snapshot_row_json`.

### Gate D2 — Wave 1 Entry Filter
**STATUS: NOT BUILT**

Files: NEW — `web/scripts/wave1_entry_filter.mjs` and `tools/wave1_entry_filter.py`

Logic: per §4. Input: current `snapshot_row_json` + prior row's `s_n`. Output: boolean is_wave1_signal.

Test: replay against the 2,194-ticker universe using validation env's parquet (SHA f12a477). Must reproduce C1 = 372 ± 5 signals and WR_20d ≥ 88.7% (lower bound of Wilson CI). If WR outside CI, STOP — do not deploy.

### Gate D3 — Exit Logic v1.0
**STATUS: PARTIALLY BUILT**

File: `web/scripts/execution/sentinel_monitor.mjs`

Required changes:
1. Reinstate EXIT-A: `S_UF >= 0.75` fires for winning positions, subject to EXIT-R9 guard for losing positions
2. Add EXIT-TIME: `age_days >= 20` fires for all positions (no EXIT-R9 guard needed — this is a time-based close, not a loss exit)
3. Confirm EXIT-B, EXIT-C, EXIT-F, EXIT-R9 behavior unchanged

Test: dry-run against historical positions (past 30 days). Verify EXIT-A fires on S_UF >= 0.75 examples, EXIT-F fires on −10% examples, EXIT-TIME fires on 20+ day examples. Confirm no EXIT-D or EXIT-S firings.

### Gate D4 — Bookkeeping Forward Fixes
**STATUS: NOT BUILT**

Files: per docs/TFE-BRIEF-EXIT-PL-WRITE-PATH-FIX-20260623.md (F-001, F-002) and F-007a (F-003 gate)

**Must deploy in this order:**
1. F-007a sentinel orphan_sync guard (SHA 29bf93d) — ECS deploy
2. F-001 forward fix (write p_l at exit fill time)
3. F-002 fix (overwrite sentinel_exit_order_id at fill resolution)
4. Verify 100% non-NULL p_l on 10-trade test close sequence
5. Verify sentinel_exit_order_id matches fill_id on same 10 trades

### Gate D5 — Fresh Ledger Initialization
**STATUS: NOT STARTED**

Pre-conditions: Gates D1–D4 PASS; drain positions reduced to 0 (sentinel exits all remaining); migrations 007+008 confirmed deployed (SHA efdc3cd).

Operations:
1. Archive contaminated ledger (rename table, preserve for audit)
2. Initialize new `personal_trade_ledger` at $100K vault equity
3. Zero open positions, zero equity curve entries
4. Kill switch remains ON until Wave 1 filter (Gate D2) is deployed

### Gate D6 — 30-Day Paper Trading
**STATUS: NOT STARTED (requires D1–D5)**

Pass criteria (all must hold simultaneously at end of 30 days):
- Annualized return ≥ +12% on paper
- Maximum drawdown ≤ −15%
- P&L bookkeeping integrity: 100% non-NULL p_l, 0 duplicate writes, 0 NULL entry_order_id on closes
- Wave 1 entries per week: 1–5 (sanity check on signal volume; <1/week suggests s_n emission broken; >5/week suggests filter misapplied)
- 30-day realized WR on closed positions ≥ 75% (conservative live threshold; below the 91.9% backtest with noise margin)

### Gate D7 — Live Deployment
**STATUS: NOT STARTED (requires D6 PASS + explicit Joe approval)**

Trigger: Gate D6 PASS + Joseph Forrester explicit go-ahead.
Starting capital: Joseph Forrester's decision.

**Source of Truth:** This document.

---

## 13. Monitoring and Continuous Validation

- **Live W1 signal log:** Every signal emission writes to a `wave1_signals` table with the full kernel snapshot at trigger time (s_n, |Δs_n|, bar_count, D_k, ticker, date, close, signal_sha).
- **Realized WR rolling:** 30-day, 90-day, 365-day windows on closed positions from personal_trade_ledger where signal_source='wave1'.
- **Drift alert threshold:** If 30-day realized WR drops below 70%, trigger alert for Joseph Forrester review. Not auto-suspend; no automated response.
- **Architecture drift:** Nightly comparison of live Wave 1 selections against quarantine-kernel reference run on same bars (tools/wave_cohort_reval_20260625.py or successor). Any divergence > 1 signal/day flagged in monitoring log.
- **Quarterly re-validation:** Re-run tools/wave_kernel_run_20260625.py against updated production-equivalent daily_bars (include new bars since 2026-03-24). Expect WR drift < 5 pp from 91.9% baseline over a 1-year horizon.

---

## 14. Forbidden Modifications (The Lock)

The following are forbidden without explicit Joseph Forrester approval AND a documented physics reason (not a performance reason):

1. **Modifying Wave 1 spec bands** — bar_count range [1,20], s_n range [0.954, 0.969], |Δs_n| range [0.67, 0.72]. These are from structural_wave_alignment_spec.tex Definition 1. Widening them changes what "crystallization event" means, not what the system selects.

2. **Replacing raw L0 with log L0** — The Wave 1 measurement (SHA 848aff6) used raw prices. Log L0 is a different kernel and would require re-running the entire cohort pipeline before any WR claim can be made. See KERNEL_PHILOSOPHY.md §4.

3. **Adding ML, heuristics, smoothing, or stabilization** to any kernel layer — KERNEL_PHILOSOPHY.md §3 names this destruction pattern #2 ("LLM cleans up by replacing physics-grounded filters with score formulas"). The s_n surprise signal must be emitted as computed, not smoothed.

4. **Removing s_n from production snapshots** once added — Wave 1 is dead without s_n.

5. **Replacing Wave 1 with v3 basin or tuple-proximity as primary selection** — The 5-year walk-forward (SHA 060b9aa) returned +1.31%/yr using v3 basin + tuple-proximity. The v3 basin cannot see the Wave 1 discriminant (encoded in s_n, not the L4 tuple). See §2.

6. **Adjusting eta_h, theta_plus, F_max, or any other constant** to make the kernel's ACCUMULATE field reachable. The ACCUMULATE field is a dead branch. The Wave 1 trigger (D_k: 0→+1) is the correct gate.

7. **Disabling EXIT-F** — always active, cannot be removed.

8. **Increasing max concurrent positions above 30** without a measured basis.

9. **Using C13 or C123 as live entry gates** without first resolving why the conjunction is zero on this dataset (§7 of the canonical doc). See KERNEL_PHILOSOPHY.md §8.5.

Cross-references: KERNEL_PHILOSOPHY.md §§4, 8, 8.5, 8.6, 8.7.

---

## 15. What v1.0 Does NOT Do (Stage 2 Roadmap)

The following are excluded from v1.0 deployment and require separate measurement before activation:

**Wave 2 (calm species):** Species classification reads from `species_profiles` when populated but does not filter or size in v1.0. C12 (31 signals, 87.1% WR) is promising but the Wilson CI [0.711, 0.949] is too wide for a sizing decision. Requires more signal volume.

**Wave 3 (SPY D_k=+1):** C13 = 0 signals under the quarantine kernel. Wave 3 is not a selection condition in v1.0. The SPY kernel choice (quarantine vs uf_core) materially changes which dates are D_k=+1 (41 vs 55 dates), and neither overlaps with the 2021–2024 period where most Wave 1 triggers occur. Requires separate investigation.

**Structural exit assessment (Step 3b):** Spec exists at docs/structural_exit_assessment_spec.tex (Horse/Herd/Distance). Code not built. EXIT-TIME (20d default) covers the exit horizon in v1.0.

**Multi-asset:** Futures, FX, crypto — same kernel applies structurally; deferred. Universe maintenance and bar sourcing would require separate work.

**Multi-horizon:** 5d, 60d forward returns. v1.0 trades the 20-day horizon only (matched to the C1 WR measurement).

**Conviction-weighted sizing:** W1+W3 at 1.5× and W1+W2+W3 at 2× — deferred to Stage 2. Requires W3 to be validated first.

---

## 16. Document Change Log

| Date | Author | Change |
|------|--------|--------|
| 2026-06-25 | wC + c1 | Inaugural version. Based on canonical W1 finding at SHA 9fea032. |
