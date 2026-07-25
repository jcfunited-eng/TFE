# TFE-CMD-L5-PHYSICS-NATIVE-STACK-WC-20260707-v1

**Purpose:** Replace the D5.x compromise gate (physics-gate + universe-allowlist) with the physics-native L5 stack derived from the walkforward cohort trajectory analysis, and add the pool-calendar exit that harvests the release phase.

**Priority:** BLOCKING for D6 / D7. Halt must remain in place until this ships. Do not open the kill switch until Step 8 verification passes.

**Branch:** `codex/persistent-etl-update-20260326`
**Origin SHA:** `8dc5141` (D5.8, current production)

**Backing analysis:** `tools/cohort_trajectory_20260625.parquet` (24,699 rows / 835 walkforward holds). Filters and numeric constants derived from measurement, not fit to backtest.

---

## 0. Physics rationale (short)

The 835-trade walkforward exposed two independent facts:

1. The 7-tuple is a coupled derivative structure over the URF trajectory. `M_k` crosses zero exactly at `D_k: 1→0` transitions across 143 events, p<1e-15. Not vocabulary — measured.
2. The pool identity (calm/normal/volatile from `species_profiles`) is the L5 filter that distinguishes energy-bearing tickers. Normal species produces no cycle edge (45% WR on fresh ignition). Calm and volatile produce the cycle release the spec predicts.

The D5.x scalar gates (`R_rev_k=0 AND 0<M_k<0.12`, universe allowlist) are point-in-time reads of coupled fields — the exact destruction pattern named in `KERNEL_PHILOSOPHY.md`. They cost EV independently across 2021, 2022, 2023 and produced the -1.31%/yr walkforward.

The physics-native L5 read is:

**Entry candidate is trade-worthy iff:**
- Ticker is not an ETF (per Polygon reference)
- `bar_count >= 252` (kernel integrator past warmup, not zombie)
- `species ∈ {'calm', 'volatile'}` (energy-bearing pools)
- `P_k >= 1` at entry (fresh `D_k` transition — discrete `τ_in > 0`, the ignition event)
- `S_UF >= 0.667` (strong structural coupling at entry, spec §3.2 ground-state analog)

**Exit fires when:**
- Position age reaches pool cycle time (calm=15d, volatile=20d) — the median peak of the release phase, matched to pool cycle
- Or -10% catastrophic floor (EXIT-F, unchanged)

Wave 1 (spec §4 crystallization) remains a bypass path, unchanged.

## 0.1 Measured result on walkforward (must be reproduced by test)

| Metric | Value |
|---|---|
| N trades | 121 (of 835 walkforward candidates) |
| Peak WR | 91.7% |
| Realized WR | 61.2% |
| Mean realized/trade | +1.25% |
| Annualized book=3 | +17.10%/yr |
| Annualized book=1 | +23.09%/yr |

By year: 2021 WR 68% mean +2.74%, 2022 WR 61% mean +1.98%, 2023 WR 60% mean +0.23%, 2024 N=5.

Baseline walkforward as-shipped for comparison: N=835, WR 54.6%, +1.31%/yr.

---

## 1. Step-by-step execution

### STEP 1 — Branch check (paste output)

```
cd /workspaces/TFE-worktree && git branch --show-current && git log -1 --oneline
```

Must return `codex/persistent-etl-update-20260326` and the tip at `8dc5141` or a fast-forward. Stop if not.

### STEP 2 — Halt state check

Confirm kill switch is currently ON. Grep the running task def env for `TFE_ENTRIES_HALTED`. Paste actual output. If `0`, execute `TFE-CMD-HALT-BEFORE-PASS-WC-20260706-v1` first and return here.

### STEP 3 — Create ETF universe module

**NEW FILE:** `web/scripts/execution/etf_universe.mjs`

Loads the ETF ticker set from `massive_universe_etf.json` (already committed in repo root). Exports a `Set<string>` and a helper.

```javascript
/**
 * ETF universe loader.
 *
 * Reads massive_universe_etf.json (Polygon reference, 4,838 ETFs) and
 * exposes ETF_TICKERS as a Set for O(1) exclusion checks.
 *
 * Rationale: TFE kernel is designed for individual energy-bearing equities.
 * ETFs are basket products with different structural dynamics (index-tracking
 * damps idiosyncratic tuple motion). Wave 1 audit showed 190 of 372 canonical
 * "verified" signals were ETFs whose 95.8% WR was passive-index tracking a
 * rising market, not perception. Excluding them is spec-consistent, not a
 * post-hoc filter.
 */
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ETF_JSON = path.resolve(__dirname, "../../../massive_universe_etf.json");

let _etfSet = null;

export function loadETFTickers() {
  if (_etfSet) return _etfSet;
  const raw = JSON.parse(fs.readFileSync(ETF_JSON, "utf-8"));
  _etfSet = new Set();
  for (const e of raw) {
    if (e && e.ticker) _etfSet.add(String(e.ticker).toUpperCase());
  }
  return _etfSet;
}

export function isETF(ticker) {
  const set = loadETFTickers();
  return set.has(String(ticker ?? "").toUpperCase());
}

export const ETF_TICKERS = loadETFTickers();
```

Test: `node -e "import('./web/scripts/execution/etf_universe.mjs').then(m => console.log('loaded', m.ETF_TICKERS.size, 'AAA is ETF:', m.isETF('AAA'), 'AAPL is ETF:', m.isETF('AAPL')))"`

Must print `4838`, `AAA is ETF: true`, `AAPL is ETF: false`.

### STEP 4 — Replace D5.x gate with physics-native L5 stack in `3wa_strategist.mjs`

**FILE:** `web/scripts/execution/3wa_strategist.mjs`

**Add import (top of file):**

```javascript
import { isETF } from "./etf_universe.mjs";
```

**Add constants (near line 40, after `M_K_CEILING`):**

```javascript
// L5 physics-native constants (TFE-CMD-L5-PHYSICS-NATIVE-STACK-WC-20260707-v1)
// Values derived from walkforward cohort trajectory analysis, not tunable.
// Canonical, set by Joseph Forrester.
const L5_MIN_BAR_COUNT      = 252;   // kernel integrator warmup
const L5_MIN_P_K            = 1;     // fresh D_k transition (discrete τ_in > 0)
const L5_MIN_S_UF           = 0.667; // strong structural coupling
const L5_ENERGY_BEARING_POOLS = new Set(["calm", "volatile"]);
```

**REMOVE the D5.x compromise gate** — delete the block starting at the `physicsPass` computation and ending after the universe-allowlist check (lines 205-231, approximately). This includes:

```javascript
// DELETE THIS BLOCK:
//   const physicsPass = (rRevK === 0) && (mK !== null && mK > 0) && (mK < M_K_CEILING);
//   if (!wave1 && !physicsPass) return null;
//
//   if (!wave1 && !VALIDATED_UNIVERSE.has(ticker)) return null;
```

**REPLACE with L5 physics-native filter (same location):**

```javascript
  // ── L5 physics-native filter ───────────────────────────────────────
  // Wave 1 hits bypass — spec §4 crystallization is validated independently.
  // For non-Wave-1 candidates, apply the full L5 stack derived from
  // walkforward cohort trajectory analysis (TFE-CMD-L5-PHYSICS-NATIVE-STACK-WC-20260707-v1).
  //
  // The stack reads the coupled tuple state at entry through pool identity,
  // ignition discreteness, and structural coupling strength — none is a
  // scalar threshold on a field in isolation.
  if (!wave1) {
    // ETF exclusion — TFE kernel operates on individual equities, not baskets
    if (isETF(ticker)) return null;

    // Kernel warmup — integrator not converged below 252 bars
    if (barCount === null || barCount < L5_MIN_BAR_COUNT) return null;

    // Energy-bearing pool — spec §5.2 species classification
    if (!L5_ENERGY_BEARING_POOLS.has(species)) return null;

    // Fresh ignition — discrete τ_in > 0. P_k = |D_k - last_D_k|.
    // At entry D_k = 1 by construction, so P_k=1 ⇔ last_D_k = 0
    // (transition out of quiescence). P_k=0 = mid-cycle entry (no edge).
    const pK = toInt(snap.P_k ?? snap.p_k);
    if (pK === null || pK < L5_MIN_P_K) return null;

    // Strong structural coupling — spec §3.2 ground-state analog for
    // established stocks. S_UF ≥ 0.667 selects tickers whose upper-field
    // coupling weight is above the median of the trade-worthy universe.
    if (sUf === null || sUf < L5_MIN_S_UF) return null;
  }
```

**REMOVE from imports (top of file):**
```javascript
import { VALIDATED_UNIVERSE } from "./validated_universe.mjs";  // no longer used
```

**REMOVE** the `M_K_CEILING` constant if no other code references it (grep first — if orphan, delete).

**Add to the returned signal object:** `p_k: pK` so downstream logging captures the ignition flag. Also add `species: species` if not already there.

### STEP 5 — Pool-calendar exit in `sentinel_monitor.mjs`

**FILE:** `web/scripts/execution/sentinel_monitor.mjs`

**Find the EXIT-TIME block (around line 1020-1032).** Currently fires at `posAge >= 20` unconditionally.

**REPLACE with pool-calendar EXIT-TIME:**

```javascript
      // ── EXIT-TIME: Pool-calendar close ─────────────────────────────
      // (TFE-CMD-L5-PHYSICS-NATIVE-STACK-WC-20260707-v1)
      //
      // Pool cycle time matches median peak day of the release phase per pool:
      //   calm species     — peak at day ~15 (short cycle, tight coupling)
      //   volatile species — peak at day ~20 (longer buildup, larger discharge)
      //
      // Wave 1 keeps the 20-day boundary (its own validation used 20-bar horizon).
      //
      // Pool is read from the entry snapshot `signal_class` and `species`
      // fields written by 3wa_strategist. Fallback to 20 if pool unknown.
      let exitTimeTarget = 20;
      const entrySpecies = pos.rationale_json?.entry_species
                        ?? pos.rationale_json?.species
                        ?? null;
      if (entrySpecies === "calm") exitTimeTarget = 15;
      else if (entrySpecies === "volatile") exitTimeTarget = 20;
      // Wave 1 explicitly stays at 20 regardless of species tag
      if (pos.rationale_json?.signal_class === "3WA"
          || pos.rationale_json?.signal_class === "1+3") {
        exitTimeTarget = 20;
      }

      if (posAge >= exitTimeTarget) {
        const pnlStr = currentPnlPct !== null ? `${currentPnlPct.toFixed(1)}%` : "n/a";
        console.log(
          `[SENTINEL] CH2 EXIT-TIME ${pos.ticker} | age=${posAge}d target=${exitTimeTarget}d ` +
          `species=${entrySpecies ?? "unknown"} — pool-cycle exit (P&L=${pnlStr})`
        );
        await killPosition(pos, "ch2_exit_pool_cycle", ALPACA_BASE);
        continue;
      }
```

**Update `alpaca_bridge.mjs` (or whatever writes the ledger row at entry)** to include `entry_species` and `signal_class` fields in `rationale_json` so `sentinel_monitor` can read the pool at exit time. Grep for the ledger-insert to locate.

### STEP 6 — Deprecate `validated_universe.mjs`

Do NOT delete the file (other things may import it). Add a header comment:

```javascript
/**
 * DEPRECATED as of TFE-CMD-L5-PHYSICS-NATIVE-STACK-WC-20260707-v1.
 * The universe allowlist was the D5.8 compromise. L5 physics-native
 * stack replaces it with pool identity + coupling strength. Do not
 * re-add allowlist filtering unless canonical direction changes.
 */
```

### STEP 7 — Test harness (`tools/verify_l5_physics_native_20260707.py`)

Write a Python script that reproduces the measured result on the walkforward parquet. Same filter, same exit rule, must return the same numbers within tolerance.

```python
#!/usr/bin/env python3
"""
tools/verify_l5_physics_native_20260707.py

Test harness for TFE-CMD-L5-PHYSICS-NATIVE-STACK-WC-20260707-v1.

Applies the L5 physics-native filter + pool-calendar exit to the
walkforward cohort trajectory parquet and verifies the measured
result reproduces within tolerance.

Must PASS before Step 8 (removing kill switch) is authorized.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PARQUET = ROOT / "tools" / "cohort_trajectory_20260625.parquet"
SPECIES = ROOT / "tools" / "wave_species_profiles_20260625.csv"
ETF     = ROOT / "massive_universe_etf.json"

# Constants must match 3wa_strategist.mjs / sentinel_monitor.mjs exactly
MIN_BAR_COUNT   = 252
MIN_P_K         = 1
MIN_S_UF        = 0.667
POOLS_OK        = {"calm", "volatile"}
EXIT_DAY_CALM   = 15
EXIT_DAY_VOL    = 20
FLOOR           = -0.10

# Reproduction target
TARGET_N              = 121   # ±5
TARGET_REALIZED_WR    = 0.612 # ±0.03
TARGET_PEAK_WR        = 0.917 # ±0.03
TARGET_ANN_BOOK3      = 0.1710 # ±0.03

def qualify(sub, etf_set, species_map):
    ticker = sub.ticker.iloc[0]
    if ticker in etf_set: return False
    if sub.bar_count.iloc[0] < MIN_BAR_COUNT: return False
    sp = species_map.get(ticker, "unknown")
    if sp not in POOLS_OK: return False
    if sub.P_k.iloc[0] < MIN_P_K: return False
    if sub.S_UF.iloc[0] < MIN_S_UF: return False
    return True, sp

def apply_exit(sub, species):
    cum = sub.cumulative_pnl_pct.values
    target = EXIT_DAY_CALM if species == "calm" else EXIT_DAY_VOL
    for i in range(len(cum)):
        if cum[i] <= FLOOR:
            return i, cum[i]
        if i >= target:
            return i, cum[i]
    return len(cum) - 1, cum[-1]

def sim_portfolio(res, col, book):
    r = res.sort_values("entry_date").reset_index(drop=True)
    slots, key, taken = {}, 0, []
    for _, row in r.iterrows():
        for k in list(slots):
            if slots[k] <= row.entry_date: del slots[k]
        if len(slots) < book:
            slots[key] = row.exit_date
            key += 1
            taken.append(row[col])
    total = sum(taken) / book
    years = (r.exit_date.max() - r.entry_date.min()).days / 365.25
    return {
        "N": len(taken),
        "WR": np.mean([p > 0 for p in taken]),
        "mean": np.mean(taken),
        "ann": (1 + total) ** (1 / max(years, 0.01)) - 1,
    }

def main():
    print(f"[VERIFY] Loading data...")
    df = pd.read_parquet(PARQUET).sort_values(["trade_idx", "day_offset"]).reset_index(drop=True)

    etf_set = set()
    for e in json.loads(ETF.read_text()):
        if e.get("ticker"): etf_set.add(e["ticker"])
    print(f"[VERIFY]   {len(etf_set)} ETFs loaded")

    sp = pd.read_csv(SPECIES)
    species_map = dict(zip(sp.ticker, sp.classification.astype(str)))
    print(f"[VERIFY]   {len(species_map)} species classifications")

    results = []
    for tid, sub in df.groupby("trade_idx", sort=False):
        sub = sub.sort_values("day_offset").reset_index(drop=True)
        if len(sub) < 3: continue
        q = qualify(sub, etf_set, species_map)
        if q is False: continue
        _, species = q
        exit_day, exit_pnl = apply_exit(sub, species)
        results.append({
            "trade_idx": tid,
            "ticker": sub.ticker.iloc[0],
            "species": species,
            "entry_date": pd.to_datetime(sub.day.iloc[0]),
            "exit_date": pd.to_datetime(sub.day.iloc[-1]),
            "exit_pnl": exit_pnl,
            "peak_pnl": sub.cumulative_pnl_pct.max(),
        })
    res = pd.DataFrame(results)

    n = len(res)
    realized_wr = float((res.exit_pnl > 0).mean())
    peak_wr = float((res.peak_pnl > 0).mean())
    mean_per_trade = float(res.exit_pnl.mean())
    ann_book3 = sim_portfolio(res, "exit_pnl", 3)["ann"]

    print(f"\n[VERIFY] MEASURED:")
    print(f"  N                  = {n}     (target {TARGET_N} ± 5)")
    print(f"  Realized WR        = {realized_wr:.3f}  (target {TARGET_REALIZED_WR:.3f} ± 0.03)")
    print(f"  Peak WR            = {peak_wr:.3f}  (target {TARGET_PEAK_WR:.3f} ± 0.03)")
    print(f"  Mean/trade         = {mean_per_trade*100:+.2f}%")
    print(f"  Annualized book=3  = {ann_book3*100:+.2f}%/yr  (target {TARGET_ANN_BOOK3*100:+.2f}% ± 3)")

    fails = []
    if abs(n - TARGET_N) > 5: fails.append(f"N drift {n} vs {TARGET_N}")
    if abs(realized_wr - TARGET_REALIZED_WR) > 0.03: fails.append(f"WR drift {realized_wr:.3f}")
    if abs(peak_wr - TARGET_PEAK_WR) > 0.03: fails.append(f"peak WR drift {peak_wr:.3f}")
    if abs(ann_book3 - TARGET_ANN_BOOK3) > 0.03: fails.append(f"ann drift {ann_book3:.3f}")

    if fails:
        print(f"\n[VERIFY] FAIL — {'; '.join(fails)}")
        sys.exit(1)
    print(f"\n[VERIFY] PASS")

if __name__ == "__main__":
    main()
```

Run: `python3 tools/verify_l5_physics_native_20260707.py`

Must print `PASS`. If it prints `FAIL`, do not proceed — report the drift back to Joe.

### STEP 8 — Dry-run then deploy

1. `git diff --stat` → paste
2. `npm run build` (or the JS build step for `web/scripts`) → paste any errors
3. Deploy new image to ECS (task def bump). DO NOT flip kill switch.
4. Wait 24h for the strategist to run its next scheduled pass with `TFE_ENTRIES_HALTED=1`. Read logs — the strategist must log the L5 filter decisions and pool tags. Paste log excerpt showing at least one accept and one reject with each reason.
5. Only after logs show the filter working correctly: flip `TFE_ENTRIES_HALTED=0` in a NEW task def revision.
6. Watch first live pass. Escalate if signal count is 0 (something wrong) or > 30 (filter not tight enough — bug).

### STEP 9 — Completion report

Paste to Joe:
- git commit SHA of the merged changes
- task def revision numbers (pre and post)
- Full `verify_l5_physics_native_20260707.py` output
- Excerpt of first live pass log showing filter decisions
- First entry ticker + species + P_k + S_UF (verifies the fields land correctly)

---

## 2. Hard constraints

- **No parameter search.** The five constants (MIN_BAR_COUNT=252, MIN_P_K=1, MIN_S_UF=0.667, EXIT_DAY_CALM=15, EXIT_DAY_VOL=20) are canonical. Do not env-parameterize them. Do not add "tunable" alternatives. If Joe changes them later, they change in one place.
- **No additional filters.** If the L5 stack produces fewer signals than expected, do not add filters to "improve" it. Report signal count and stop.
- **No exit "improvements."** The pool-calendar exit is what harvests the release phase. Do not add trailing stops, structural exits, or other rules on top. -10% floor and pool calendar only.
- **Wave 1 path stays as-is.** No changes to the `wave1` computation or its bypass through the physics-native filter.
- **Kill switch stays ON until Step 7 verification passes** and Step 8 dry-run confirms filter is firing correctly. This is the only guarantee against re-contamination.

## 3. Physics laws being encoded (do not undo)

Any future session that removes these will re-trigger the destruction cycle. They are here for the record so the next session can check.

1. **ETF exclusion.** TFE kernel operates on individual-equity idiosyncratic dynamics. Basket products damp the state motion the kernel is designed to perceive. Removing this filter is destruction pattern #3 (financial-frame collapse) — reasoning "ETFs also went up, why exclude" misses that the mechanism is different.
2. **bar_count >= 252.** The integrator (A_f=0.90, A_m=0.98, A_s=0.995) requires ~250 bars to reach steady state. Reading tuple fields before then produces initialization-transient values that pattern-match to "ground state" without meaning it. This is what corrupted the June 24 Wave 1 measurement (365 of 372 signals at bar_count=2).
3. **Species pool filter.** Normal species produces no cycle edge on adversarial data (measured, 45% WR on 141 fresh-ignition entries). Calm and volatile species do. The three-way split is spec §5 Wave 2 — this is spec-native, not fit.
4. **P_k>=1 requirement.** P_k = |D_k - last_D_k|. At entry (D_k=1), P_k=1 means last_D_k=0 = fresh transition out of quiescence = spec §7 ALTE Ignition event. P_k=0 = mid-cycle entry with no ignition edge (measured 45.4% WR, no cycle).
5. **S_UF>=0.667.** Spec §3.2 defines the structural ground state including a_f≈0.09 (weak amplitude, high potential). For established stocks the analog is the S_UF (upper structural coupling) threshold — measured p50 of trade-worthy P_k=1 entries.
6. **Pool-calendar exit.** Median peak day of release: calm ~15, volatile ~20. The current 20-day-flat exit under-harvests calm (gives back 5 days of reversion) and matches volatile. Pool-specific timing is what converts peak WR 91.7% to realized WR 61.2%.

If any of these six change, re-run `verify_l5_physics_native_20260707.py` first. If it still passes, the change is safe. If not, revert.

## 4. Rollback

If Step 8 live pass shows unexpected behavior (0 signals, >30 signals, or logging errors):

1. `TFE_ENTRIES_HALTED=1` immediately
2. Revert task def to pre-deploy revision
3. Do NOT revert the git commit — leave the code so the next session can diagnose
4. Paste the failure mode to Joe

---

## 5. Doc trail

- Backing analysis: session log 2026-07-07 web Claude
- Canonical Wave 1 finding: `docs/TFE-CANONICAL-WAVE1-FINDING-20260625.md` (superseded for the "verified 91% WR" claim by this dispatch's clean-cohort measurement; Wave 1 as spec-defined remains valid as a bypass path)
- Kernel philosophy: `KERNEL_PHILOSOPHY.md` §3 destruction patterns
- Project state: `PROJECT_STATE.md` (needs update after Step 9)

## 6. Notes for next session

The horse/herd/diamond (Step 3b in `PROJECT_STATE.md`) is not in this dispatch. Its perception was measured weak on the walkforward's thin herd universe (5,354 rows, single-species peer pool). Proper Step 3b needs the full 5-year universe kernel state (311MB local artifact). That's the next physics build after this dispatch stabilizes. Do not attempt Step 3b before it — the temptation to add horse-based exit assessment on top of pool calendar is the same "one more filter" reflex that produced D5.x.
