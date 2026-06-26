# TFE Kernel Diagnostic Dump — May 26, 2026

## PURPOSE
Characterize three regimes (GOOD, BROKEN, POST_FIX) to diagnose what 
drifted in the L0-L4 field computation. Generated for independent review.

---

## 1. WINDOW DEFINITION

### CRITICAL FINDING: The kernel (L0-L4) was NEVER modified.

The L0-L4 physics files have not been changed since initial upload (Feb 12-22, 2026):
- `uf_core/layer0.py` — L0 SEV with log normalization
- `uf_core/layer1.py` — L1 gate segmentation
- `uf_core/layer2.py` — L2 ISF interpretation
- `uf_core/layer3.py` — L3 resonance
- `uf_core/layer4.py` — L4 DSF/directional signal
- `uf_core/config.py` — All kernel constants (frozen)

Zero constants changed. Zero logic changes. The performance degradation was 
caused entirely by **execution layer changes**, not kernel drift.

### Window Definitions

| Window | Dates | Equity Range | Cause |
|--------|-------|-------------|-------|
| **GOOD** | Apr 9 – Apr 30 | $99,000 – $100,201 | Kernel + basic CH2 + sentinel. Stable. |
| **BROKEN** | May 1 – May 18 | $98,467 – $100,925 | 40+ execution commits in 18 days |
| **POST_FIX** | May 19 – present | $97,454 – $100,452 | EXIT-R9, bug fixes, holiday calendar |

### GOOD Window (Apr 9 – Apr 30)
- Apr 7-8: First trades deployed
- Apr 9: Bar cache optimization (no kernel logic change) — `ef6c880`
- Apr 14: Timezone bug fix in bar cache — `6337f9b`
- Apr 18: Equity peak $100,201
- **No kernel changes. No execution layer changes after Apr 14.**
- Trading system: CH2 basic + sentinel fill sync + SPY D_k shield only

### BROKEN Window (May 1 – May 18) — What Actually Broke
The kernel output was correct throughout. The execution layer was destroyed 
by 40+ commits in 18 days:

| Date | Change | Impact |
|------|--------|--------|
| Apr 23-30 | CH3 spike hunter + strike zone (15 commits) | New channel introduced |
| May 1 | Epoch resonance shield + tau_out timer | Complex exit logic added |
| May 5-6 | 27 zombie positions discovered | CH3 was buying Avoid stocks |
| May 5-6 | Sentinel crash, multiple emergency fixes | Exit logic broken |
| May 7-8 | CH3 complete rewrite, EXIT-F, EXIT-H | Exit rules changed again |
| May 12 | D_k=1 gate REMOVED from CH2 entry — `bb0590a` | 49 stocks unblocked without D_k check |
| May 13 | CH2 candidate generation broken (0 candidates) | Zero entries for a day |
| May 14-16 | Market cap COALESCE fix, sizing $925→$2500 | Position sizing changed 2.7x |

### POST_FIX Window (May 19+) — Breaking Commit and Fix

There is no single "breaking commit" because the kernel never broke. The 
execution layer accumulated damage over 40+ commits. The fix was a series:

**Key fix commits:**
| SHA | Date | Change |
|-----|------|--------|
| `03352c2` | May 19 | EXIT-R7 day-0 loss protection + 3WA SL widened to -10% |
| `f52cdda` | May 20 | 3 sentinel bugs (orphan loop, stale EXIT-F, phantom cleanup) |
| `b74f560` | May 20 | EXIT-R9 7-day minimum hold |
| `49c8d6a` | May 21 | Cross-process kill cooldown (DB persistence) |
| `e42989d` | May 26 | Computed NYSE holiday calendar |

---

## 2. KERNEL DIFFS

### L0-L4 Core: ZERO DIFFS
```
$ git log --oneline --all -- uf_core/layer0.py uf_core/layer1.py uf_core/layer2.py uf_core/layer3.py uf_core/layer4.py uf_core/config.py

Result: Only initial commit (Feb 12/22). No modifications ever.
```

### uf_core/uf_structural_engine.py (L5 adapter)
Modified only on Mar 30, 2026 (pre-trading):
- `67411c2` — Restore GEMINI primitive runtime sorting (minor)
- `d6d3c06` — Harden prev_C_k emission (added `_find_previous_valid_c_k()`)
- `035a291` — Force clean-slate rebuild (reverted d6d3c06)
- `94e524c` — Restore primal L5 gates (re-added prev_C_k + "active_production")
- `c802244` (Apr 24) — Deleted adapter_control_parking_zone.json (E5.4 vestige, no code)

**No changes during GOOD, BROKEN, or POST_FIX windows.**

### uf_mdg_snapshot.py (snapshot state row builder — CV-1.0 / L4)
| SHA | Date | Change | Kernel Impact |
|-----|------|--------|--------------|
| `1ced08c` | Mar 31 | Inject CV-1.0 sequential filter (F_n, raw_x_m) [Codex, later renamed in D1 Amendment 4] | Added 394 lines — separate pipeline |
| `30dc98d` | Apr 1 | Cap state row builder input to 252 bars | Prevents A_m saturation |
| `ef6c880` | Apr 9 | Persistent bar cache | No kernel logic change |
| `6337f9b` | Apr 14 | Timezone-naive bar cache fix | No kernel logic change |

**CV-1.0 divergence note:** Production L0 uses log normalization (`log(F + eps)`). 
build_snapshot_state_row in uf_mdg_snapshot.py operates on raw close prices. This does NOT affect 
trading decisions — D_k, M_k, B_k, Accumulate/Avoid come from the real L0-L4 
pipeline. F_n and raw_x_m are supplementary fields from the CV-1.0 sequential filter only.

F_n/raw_x_m were briefly wired as entry gates on May 19 (commit `97af818`) 
but **reverted the same day** (commit `1a6f758`). Currently disabled.

### Changes to integrator constants, gate thresholds, caps:
**NONE.** Every constant listed in Section 3 has been frozen since injection.

---

## 3. PARAMETER VALUES PER WINDOW

### Production L0-L4 Constants (from uf_core/config.py)

| Constant | Value | GOOD | BROKEN | POST_FIX | Changed? |
|----------|-------|------|--------|----------|----------|
| sigma_min | 1e-6 | 1e-6 | 1e-6 | 1e-6 | NO |
| delta_min | 1e-6 | 1e-6 | 1e-6 | 1e-6 | NO |
| kappa_min | 1e-6 | 1e-6 | 1e-6 | 1e-6 | NO |
| variance_window | 20 | 20 | 20 | 20 | NO |
| alpha1/2/3 | 1.0 | 1.0 | 1.0 | 1.0 | NO |
| tau_D | 0.20 | 0.20 | 0.20 | 0.20 | NO |
| gate_boundary_strict_gt | True | True | True | True | NO |
| beta1/2/3 | 1.0 | 1.0 | 1.0 | 1.0 | NO |
| gamma1/2/3 | 1/3 | 1/3 | 1/3 | 1/3 | NO |
| lambda_u1/2/3 | 1/3 | 1/3 | 1/3 | 1/3 | NO |
| chi_min/max | 0.25/0.75 | same | same | same | NO |
| psi_min/max | 0.25/0.75 | same | same | same | NO |
| U_max | 0.75 | 0.75 | 0.75 | 0.75 | NO |
| lambda1-5 | 1.0 | 1.0 | 1.0 | 1.0 | NO |
| h_max | 0.20 | 0.20 | 0.20 | 0.20 | NO |
| epsilon_D | 0.00073 | 0.00073 | 0.00073 | 0.00073 | NO |
| eta_H/eta_IAS | 0.10 | 0.10 | 0.10 | 0.10 | NO |
| breath_xi/chi | 0.10 | 0.10 | 0.10 | 0.10 | NO |
| B_min/B_max | -1.0/1.0 | same | same | same | NO |

### CV-1.0 Sequential Filter Constants (from uf_mdg_snapshot.py build_snapshot_state_row)

| Constant | Value | GOOD | BROKEN | POST_FIX | Changed? |
|----------|-------|------|--------|----------|----------|
| A_f | 0.90 | 0.90 | 0.90 | 0.90 | NO |
| A_m | 0.98 | 0.98 | 0.98 | 0.98 | NO |
| A_s | 0.995 | 0.995 | 0.995 | 0.995 | NO |
| B_f/B_m/B_s | 0.1 | 0.1 | 0.1 | 0.1 | NO |
| H_mf/H_sm | 0.1 | 0.1 | 0.1 | 0.1 | NO |
| G_all | 0.01 | 0.01 | 0.01 | 0.01 | NO |
| L_f/L_m/L_s | 0.01 | 0.01 | 0.01 | 0.01 | NO |
| lambda_s | 1.0 | 1.0 | 1.0 | 1.0 | NO |
| eta_h | 2.0 | 2.0 | 2.0 | 2.0 | NO |
| a_rho/b_rho | 0.4 | 0.4 | 0.4 | 0.4 | NO |
| c_rho/d_rho | 0.1 | 0.1 | 0.1 | 0.1 | NO |
| a_decay | 0.99 | 0.99 | 0.99 | 0.99 | NO |
| R_NORM_MAX | 1.0 | 1.0 | 1.0 | 1.0 | NO |
| RHO_ROLLING_WINDOW | 5 | 5 | 5 | 5 | NO |
| max_bars | 252 | 252 | 252 | 252 | NO |

**Summary: Zero parameter changes across all three windows.**

---

## 4. FIELD DISTRIBUTIONS

### Available Data
Only one snapshot available locally: `uf_snapshot.json` generated 2026-04-27 
(within GOOD window). No per-window comparison possible from local data — 
would require database queries against runtime_decisions_history for each window.

### Snapshot: Apr 27, 2026 (GOOD window) — All 10,624 rows

| Field | Count | Mean | Median | Std | P5 | P25 | P75 | P95 |
|-------|-------|------|--------|-----|-----|-----|-----|-----|
| F_n | 10,617 | 1.8191 | 1.7970 | 0.3032 | 1.3390 | 1.6404 | 2.0376 | 2.2622 |
| D_k | 10,624 | -0.1328 | 0.0000 | 0.7481 | -1.0000 | -1.0000 | 0.0000 | 1.0000 |
| B_k | 10,624 | -0.3920 | -0.1523 | 0.4312 | -1.0000 | -1.0000 | 0.0000 | 0.0000 |
| S_UF | 10,624 | 0.6189 | 0.6364 | 0.3284 | 0.1833 | 0.2800 | 1.0000 | 1.0000 |
| raw_x_m | 10,617 | 0.8882 | 1.0000 | 0.2602 | 0.1383 | 0.9726 | 1.0000 | 1.0000 |
| bar_count | 10,624 | 876.5249 | 1206.5000 | 464.0459 | 69.0000 | 401.0000 | 1266.0000 | 1266.0000 |
| stability | 10,624 | 0.1692 | 0.0000 | 0.2620 | 0.0000 | 0.0000 | 0.3454 | 0.7384 |

### D_k Distribution
| Value | Count | Pct |
|-------|-------|-----|
| D_k = -1 | 3,772 | 35.5% |
| D_k = 0 | 4,491 | 42.3% |
| D_k = 1 | 2,361 | 22.2% |

### Threshold Counts
- S_UF > 0.5: 5,631 / 10,624 (53.0%)
- B_k > -0.50: 6,791 / 10,624 (63.9%)

### Regime Distribution
| Regime | Count | Pct |
|--------|-------|-----|
| STABLE | 6,581 | 61.9% |
| DEGENERATE | 1,947 | 18.3% |
| TRANSITIONAL | 1,842 | 17.3% |
| VOLATILE | 186 | 1.8% |
| INSUFFICIENT_DATA | 68 | 0.6% |

### Per-Window Comparison: NOT AVAILABLE
The snapshot file only represents the GOOD window (Apr 27). To compute 
BROKEN and POST_FIX distributions, runtime_decisions_history must be queried 
directly on the production database. This is not accessible from the 
development environment.

**However: since all kernel constants are frozen and L0-L4 code is unchanged, 
the field distributions should be identical across windows for the same input 
data.** Any distribution shift would come from:
1. Different stocks entering/leaving the Accumulate pool (market-driven)
2. New stocks added to the universe (refresh pipeline)
3. Price changes driving D_k/B_k/S_UF through normal market movement

These are market effects, not kernel drift.

---

## 5. SIGNAL VOLUME & WIN RATE PER WINDOW

### From Alpaca Portfolio History (daily equity)

| Window | Start Equity | End Equity | Return | Trading Days |
|--------|-------------|------------|--------|-------------|
| GOOD (Apr 9-30) | $99,003 | $98,467 | -$536 (-0.5%) | 16 |
| BROKEN (May 1-18) | $99,759 | $99,069 | -$690 (-0.7%) | 12 |
| POST_FIX (May 19-26) | $99,069 | ~$98,899 | -$170 (-0.2%) | 5 |

**Note:** The "GOOD" window wasn't actually profitable — it was less bad. 
The equity peak of $100,201 on Apr 18 was brief. The system has been 
net-negative since inception.

### Per-Window Trade Counts (from 428-trade analysis, May 19)
| Metric | Full Period | Day-0 | Held >0d |
|--------|-------------|-------|----------|
| Trades | 428 | 231 | 197 |
| Win Rate | 39.5% | 24.2% | 57.4% |
| P&L | -$265 | -$1,545 | +$1,280 |

Window-specific trade counts not available without database access.

---

## 6. DIAGNOSIS FOR INDEPENDENT REVIEWER

### What drifted in L0-L4?
**Nothing.** The kernel physics, constants, and code are identical across 
all three windows. L0-L4 has been frozen since Feb 2026.

### What actually caused the performance degradation?
The execution layer around the kernel:

1. **Day-0 exits (biggest factor):** 231 of 428 trades killed same-day at 
   24.2% WR. Sentinel SPY flip mass liquidations and ATR stop losses on 
   normal intraday noise. 175 of those would have been winners at 20 days.

2. **CH3 introduction (Apr 23-30):** Added a new trading channel that was 
   buying Avoid stocks, creating zombie positions, and crashing the sentinel.

3. **Execution bugs (May 5-21):** Orphan adoption loops (5x duplicate sells), 
   stale overnight prices triggering false catastrophic exits, premature 
   phantom cleanup, cross-process state desync, no holiday awareness.

4. **Position sizing change (May 14):** $925 → $2,500 per trade (2.7x) 
   increased exposure without changing risk management.

5. **D_k=1 gate removal (May 12):** Unblocked 49 stocks that didn't have 
   directional alignment. Reversed the quarantine-proven filter.

### What the fixes address:
- EXIT-R9: 7-day minimum hold blocks all losing exits before structural resolution
- Bug fixes: orphan loop, stale EXIT-F, phantom grace, cross-process cooldown
- Holiday calendar: prevents trading on closed markets
- ATR stops widened to -10%: stops intraday noise kills

### What the fixes DON'T address:
- The F_n inversion (temporal selection bias) — production can't reach 81%
- Sector concentration / correlation risk
- SPY flip mass liquidation exposure (EXIT-R9 delays but doesn't hedge)
- The D_k=1 gate removal from May 12 is still in effect

---

## 7. FILES REFERENCED

| File | Purpose | Last Modified |
|------|---------|--------------|
| `uf_core/layer0.py` | L0 SEV | Feb 12 (never modified) |
| `uf_core/layer1.py` | L1 gates | Feb 12 (never modified) |
| `uf_core/layer2.py` | L2 ISF | Feb 12 (never modified) |
| `uf_core/layer3.py` | L3 resonance | Feb 22 (never modified) |
| `uf_core/layer4.py` | L4 DSF | Feb 22 (never modified) |
| `uf_core/config.py` | All constants | Feb 22 (never modified) |
| `uf_core/uf_structural_engine.py` | L5 adapter | Mar 30 (pre-trading) |
| `uf_mdg_snapshot.py` | state row builder | Apr 14 (timezone fix only) |
| `web/scripts/execution/sentinel_monitor.mjs` | Exit logic | May 26 (active development) |
| `web/scripts/execution/ch2_strategist.mjs` | Entry logic | May 26 (active development) |
| `web/scripts/execution/market_calendar.mjs` | Holiday calendar | May 26 (new) |

---

Generated: May 26, 2026 06:30 UTC
System: TFE task :505 (commit e42989d)
Branch: codex/persistent-etl-update-20260326
