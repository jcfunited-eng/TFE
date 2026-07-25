# TFE-CMD-V3-BASIN-DETERMINISTIC-WC-20260707-v1

**Purpose:** Remove every layer in TFE that flattens the deterministic V3 basin coupled math. Rewire entry to use `accumulate_basin` magnitude and exit to use `break_agreement` crossing. Both quantities are deterministic outputs of the coupled formulas already implemented in `tools/cohort_trajectory_extract_20260625.py` lines 47–125. No scalar thresholds on isolated fields. No fitted constants.

**Priority:** BLOCKING. Kill switch stays on until Step 9 verification passes.

**Branch:** `codex/persistent-etl-update-20260326`
**Origin SHA:** `8dc5141`

---

## 0. The math being applied (verbatim from the extract script)

```
M_hat = clamp(M_k, -1, 1)

s = S_UF - U_star_k
r = R_UF - U_star_k
s_pos = max(s, 0)
r_pos = max(r, 0)

core      = min(s_pos, r_pos)
edge      = max(s_pos, r_pos) - core
live      = core + (37/64) * edge
contested = (27/64) * edge
balance   = core / (core + edge + 1e-12)
rupture   = max(0, -max(s, r))

D_nonadverse = (1 + D_k) / 2
D_adverse    = max(0, -D_k)
M_continue   = (1 + M_hat) / 2
M_bend       = (1 - M_hat) / 2
motion = ( 0.6*D_nonadverse^1.25 + 0.4*M_continue^1.25 )^(1/1.25)

adverse_break   = D_adverse * M_bend
reversal_break  = R_rev_k * (1 - balance)^16
carry_break     = (-B_k) * R_rev_k * (1 - balance)^4 * (1 - adverse_break)
burden          = (1/128) * (C_k/(1+C_k)) * (P_k/(1+P_k))
break_agreement = max(adverse_break, reversal_break, carry_break)

accumulate_basin = live * motion * (1 - R_rev_k) * (1 - adverse_break) * (1 - burden)
hold_basin       = contested*(1 - break_agreement)
                 + live*R_rev_k*balance
                 + live*(1 - R_rev_k)*((1 - motion)*(1 - adverse_break) + motion*burden)
avoid_basin      = rupture + (live + contested) * break_agreement
```

The signals TFE will use at decision time:

- **Entry ranking:** `accumulate_basin` magnitude, computed from the current tuple at signal time.
- **Exit trigger:** `break_agreement` crossing 0.20 during the hold, computed from the tuple state at each daily bar.

Both quantities come from the coupled formulas above. Neither is a scalar threshold on an individual field.

---

## 1. Files to change

### STEP 1 — Extract V3 basin math into a shared module

**NEW FILE:** `web/scripts/execution/v3_basin.mjs`

Ports the extract-script math to JS, verbatim, deterministic, no rounding shortcuts. Exports one function `computeV3Basin(tuple) -> { accumulate_basin, hold_basin, avoid_basin, break_agreement, motion, balance, live, ... }`.

```javascript
// Frozen rational constants — must match tools/cohort_trajectory_extract_20260625.py
const BETA = 37 / 64;
const CONTESTED_WEIGHT = 27 / 64;
const MOTION_WEIGHT = 3 / 5;
const MOTION_POWER = 5 / 4;
const REVERSAL_BALANCE_POWER = 16;
const CARRY_BALANCE_POWER = 4;
const BURDEN_SCALE = 1 / 128;
const V3_TIE_EPS = 1e-12;

function clamp(x, lo, hi) { return Math.max(lo, Math.min(hi, x)); }

/**
 * Compute V3 basin coupled read from a tuple snapshot.
 * All inputs are floats; nulls -> return null.
 *
 * DO NOT MODIFY THE FORMULAS. This is the deterministic coupled math.
 * Any scalar override on individual fields undoes the coupling and
 * re-introduces the flattening pattern documented in
 * KERNEL_PHILOSOPHY.md §3.
 */
export function computeV3Basin(tuple) {
  const required = ["S_UF", "R_UF", "D_k", "M_k", "R_rev_k", "U_star_k", "C_k", "P_k", "B_k"];
  for (const f of required) {
    const v = tuple[f];
    if (v === null || v === undefined || !Number.isFinite(Number(v))) return null;
  }
  const S_UF     = Number(tuple.S_UF);
  const R_UF     = Number(tuple.R_UF);
  const D_k      = Number(tuple.D_k);
  const M_k      = Number(tuple.M_k);
  const R_rev_k  = Number(tuple.R_rev_k);
  const U_star_k = Number(tuple.U_star_k);
  const C_k      = Number(tuple.C_k);
  const P_k      = Number(tuple.P_k);
  const B_k      = Number(tuple.B_k);

  const M_hat = clamp(M_k, -1, 1);

  const s = S_UF - U_star_k;
  const r = R_UF - U_star_k;
  const s_pos = Math.max(s, 0);
  const r_pos = Math.max(r, 0);

  const core      = Math.min(s_pos, r_pos);
  const edge      = Math.max(s_pos, r_pos) - core;
  const live      = core + BETA * edge;
  const contested = CONTESTED_WEIGHT * edge;
  const balance   = core / (core + edge + 1e-12);
  const rupture   = Math.max(0, -Math.max(s, r));

  const D_nonadverse = (1 + D_k) / 2;
  const D_adverse    = Math.max(0, -D_k);
  const M_continue   = (1 + M_hat) / 2;
  const M_bend       = (1 - M_hat) / 2;

  const motion = Math.pow(
    MOTION_WEIGHT * Math.pow(D_nonadverse, MOTION_POWER)
    + (1 - MOTION_WEIGHT) * Math.pow(M_continue, MOTION_POWER),
    1 / MOTION_POWER,
  );

  const adverse_break  = D_adverse * M_bend;
  const reversal_break = R_rev_k * Math.pow(1 - balance, REVERSAL_BALANCE_POWER);
  const carry_break    = (-B_k) * R_rev_k
                       * Math.pow(1 - balance, CARRY_BALANCE_POWER)
                       * (1 - adverse_break);
  const burden         = BURDEN_SCALE * (C_k / (1 + C_k)) * (P_k / (1 + P_k));
  const break_agreement = Math.max(adverse_break, reversal_break, carry_break);

  const accumulate_basin = live * motion * (1 - R_rev_k) * (1 - adverse_break) * (1 - burden);
  const hold_basin       = contested * (1 - break_agreement)
                         + live * R_rev_k * balance
                         + live * (1 - R_rev_k) * ((1 - motion) * (1 - adverse_break) + motion * burden);
  const avoid_basin      = rupture + (live + contested) * break_agreement;

  const max_b = Math.max(accumulate_basin, hold_basin, avoid_basin);
  const near_acc  = Math.abs(max_b - accumulate_basin) <= V3_TIE_EPS;
  const near_hold = Math.abs(max_b - hold_basin)        <= V3_TIE_EPS;
  const near_avd  = Math.abs(max_b - avoid_basin)       <= V3_TIE_EPS;
  const n_near = Number(near_acc) + Number(near_hold) + Number(near_avd);
  let decision_argmax;
  if (n_near > 1) decision_argmax = "Tie";
  else if (near_acc) decision_argmax = "Accumulate";
  else if (near_hold) decision_argmax = "Hold";
  else decision_argmax = "Avoid";

  return {
    s, r, core, edge, live, contested, balance, rupture,
    D_nonadverse, D_adverse, M_continue, M_bend, motion,
    adverse_break, reversal_break, carry_break, burden, break_agreement,
    accumulate_basin, hold_basin, avoid_basin,
    decision_argmax,
  };
}
```

Verify: `node -e "import('./web/scripts/execution/v3_basin.mjs').then(m => { const r = m.computeV3Basin({S_UF:0.5,R_UF:0.5,D_k:1,M_k:0,R_rev_k:0,U_star_k:0.4,C_k:3,P_k:0,B_k:-0.2}); console.log(JSON.stringify(r, null, 2)); })"`

Must print a JSON block with `accumulate_basin`, `hold_basin`, `avoid_basin`, `break_agreement` all numeric.

Cross-verify against the Python extract script: pick 5 rows from `tools/cohort_trajectory_20260625.parquet` at random, pass the tuple through `computeV3Basin`, compare every returned field to the parquet's already-computed value. Match to 1e-10.

Paste the diff numbers.

### STEP 2 — Rewire `3wa_strategist.mjs` entry to use `accumulate_basin` magnitude

**FILE:** `web/scripts/execution/3wa_strategist.mjs`

**Add at top:**
```javascript
import { computeV3Basin } from "./v3_basin.mjs";
```

**Add near existing constants:**
```javascript
// V3 basin deterministic entry constant.
// TFE-CMD-V3-BASIN-DETERMINISTIC-WC-20260707-v1.
// Do not turn this into a tunable env var. If it moves, it moves in
// one place under review, not per-deploy.
const ACCUMULATE_BASIN_MIN = 0.15;
```

The 0.15 corresponds to roughly the top third of `accumulate_basin` values in the walkforward trade-worthy universe. It is not a fitted threshold on a field — it's a magnitude cut on the coupled score itself, saying "only take entries where the coupled math produces a strong Accumulate reading, not merely a positive one."

**REMOVE the D5.x compromise gate.** Delete the block computing `physicsPass` from `R_rev_k`, `M_k`. Delete the `M_K_CEILING` constant if orphan. Delete the `VALIDATED_UNIVERSE` import and the `.has(ticker)` gate. Do not replace with anything — the coupled math replaces both.

**Also REMOVE any Layer-2 F_n / raw_x_m null-pass fallback if present.** The V3 basin computation from the tuple emit does not depend on F_n; the fallback logic that lets rows pass with F_n=null is not needed and should not be duplicated in the strategist.

**REPLACE with the V3-basin-magnitude entry check** (in the same location the compromise gate was):

```javascript
  // ── V3 basin deterministic coupled read ────────────────────────────
  // Wave 1 crystallisation events bypass — those are qualified by
  // the spec's structural crystallisation math (§3), separate rule set.
  if (!wave1) {
    const basin = computeV3Basin({
      S_UF: sUf, R_UF: rUf, D_k: dK, M_k: mK, R_rev_k: rRevK,
      U_star_k: uStarK, C_k: cK, P_k: pK, B_k: bK,
    });
    if (basin === null) return null;              // tuple incomplete, skip
    if (basin.decision_argmax !== "Accumulate") return null;
    if (basin.accumulate_basin < ACCUMULATE_BASIN_MIN) return null;
    // Store on the signal for logging and downstream governance
    signal.v3_basin = {
      accumulate_basin: basin.accumulate_basin,
      hold_basin: basin.hold_basin,
      avoid_basin: basin.avoid_basin,
      break_agreement: basin.break_agreement,
      motion: basin.motion,
      balance: basin.balance,
    };
  }
```

**Signal ranking within a pass:** if multiple signals qualify, sort by `accumulate_basin` descending and take the top N up to `max_concurrent`. Not by ticker alphabetical. Not by market cap. By coupled-read strength.

Paste `git diff web/scripts/execution/3wa_strategist.mjs`.

### STEP 3 — Rewire `sentinel_monitor.mjs` exit to use `break_agreement` crossing

**FILE:** `web/scripts/execution/sentinel_monitor.mjs`

**Add at top:**
```javascript
import { computeV3Basin } from "./v3_basin.mjs";
```

**Add constant:**
```javascript
// break_agreement crossing threshold — the deterministic peak marker.
// See TFE-CMD-V3-BASIN-DETERMINISTIC-WC-20260707-v1 §0.
const BREAK_AGREEMENT_EXIT = 0.20;
const MAX_HOLD_CALENDAR_CAP = 25;   // safety cap for trades that never activate
```

The exit routine currently uses `posAge >= 20` calendar and `EXIT-F -10%` catastrophic. Add the break_agreement check *before* the calendar check. Calendar becomes fallback for non-activating trades.

**Find the exit-condition block for each open position** (search for `posAge`, in the ch2 exit loop). Structure the exit stack in this order:

```javascript
      // ── EXIT-CATASTROPHIC (unchanged) ─────────────────────────────
      if (currentPnlPct !== null && currentPnlPct <= -10.0) {
        await killPosition(pos, "ch2_exit_catastrophic_f", ALPACA_BASE);
        continue;
      }

      // ── EXIT-BASIN-BREAK: deterministic coupled peak marker ───────
      // Compute the V3 basin from the current daily tuple snapshot.
      // If break_agreement has crossed the threshold, the coupled math
      // says the structure has broken — the release has happened, take it.
      const snap = await fetchLatestSnapshotTuple(pos.ticker); // implement to read latest uf_mdg row
      if (snap) {
        const basin = computeV3Basin(snap);
        if (basin && basin.break_agreement >= BREAK_AGREEMENT_EXIT) {
          console.log(
            `[SENTINEL] CH2 EXIT-BASIN-BREAK ${pos.ticker} age=${posAge}d ` +
            `break_agreement=${basin.break_agreement.toFixed(4)} ` +
            `(P&L=${currentPnlPct?.toFixed(1) ?? "n/a"}%)`
          );
          await killPosition(pos, "ch2_exit_basin_break", ALPACA_BASE);
          continue;
        }
      }

      // ── EXIT-CALENDAR-CAP: safety for trades that never activate ──
      if (posAge >= MAX_HOLD_CALENDAR_CAP) {
        console.log(
          `[SENTINEL] CH2 EXIT-CALENDAR-CAP ${pos.ticker} age=${posAge}d ` +
          `— trade did not show coupled break, capping hold (P&L=${currentPnlPct?.toFixed(1) ?? "n/a"}%)`
        );
        await killPosition(pos, "ch2_exit_calendar_cap", ALPACA_BASE);
        continue;
      }
```

`fetchLatestSnapshotTuple(ticker)` needs to read the latest row from the same source `3wa_strategist.mjs` reads at entry. Implement using the existing snapshot loader — the tuple fields are identical.

Paste `git diff web/scripts/execution/sentinel_monitor.mjs` and the diff on wherever `fetchLatestSnapshotTuple` is implemented.

### STEP 4 — Deprecate `validated_universe.mjs`

Add the deprecation header. Do not delete — other imports may exist. Header text:

```javascript
/**
 * DEPRECATED as of TFE-CMD-V3-BASIN-DETERMINISTIC-WC-20260707-v1.
 * The universe allowlist was a compromise layer that overrode the
 * deterministic V3 basin coupled math with a hardcoded ticker set.
 * Selection now uses accumulate_basin magnitude only. Do not
 * re-import this file into 3wa_strategist.mjs or sentinel_monitor.mjs.
 */
```

Paste `git diff web/scripts/execution/validated_universe.mjs`.

### STEP 5 — Log the coupled read at every decision

Every entry accept, entry reject, and exit fire logs the V3 basin dict. This is how we prove the coupling is being applied and not silently bypassed.

Ensure the strategist log line at accept includes `accumulate_basin`, `break_agreement`, `motion`, `balance`.
Ensure the strategist log line at reject includes the reason (which field / which condition tripped) and the values.
Ensure the sentinel log lines at exit include `break_agreement` at the moment of the exit.

If logs already emit some of these, no duplication. If not, add them.

### STEP 6 — Snapshot pipeline check

The V3 basin math needs the full tuple (S_UF, R_UF, D_k, M_k, R_rev_k, U_star_k, C_k, P_k, B_k) at every daily bar for every open position. The strategist reads this from the daily snapshot; the sentinel exit will read the same source.

Grep for the snapshot file that `3wa_strategist.mjs` reads at start-of-pass. Confirm it contains all nine fields per row for every ticker in the current position list.

If it doesn't, the pipeline needs to also refresh open-position tuples during the day. If the refresh frequency is only daily, that's fine for now — record it. If the refresh doesn't cover open positions at all, that's a bug and must be fixed. Grep and paste what the refresh script emits.

### STEP 7 — Verification harness (`tools/verify_v3_basin_deterministic_20260707.py`)

The test replays the walkforward parquet through the deterministic rule set and confirms three things:

1. `accumulate_basin` computed from the tuple matches the parquet's `accumulate_basin` column to 1e-10 (proves the JS port is verbatim; the Python side is the same math re-run).
2. The activation-cohort analysis holds: filtering trades where `max(break_agreement) >= 0.20` produces 89% ± 3% peak WR across the trade-worthy universe.
3. Under the exit rule (first crossing of `break_agreement >= 0.20`, calendar cap 25d, floor -10%), the walkforward realized returns match the recomputed pipeline exactly.

Script:

```python
#!/usr/bin/env python3
"""
tools/verify_v3_basin_deterministic_20260707.py

Verification harness for TFE-CMD-V3-BASIN-DETERMINISTIC-WC-20260707-v1.
Runs three deterministic checks:

  CHECK 1 — Math parity: recompute accumulate_basin, break_agreement, etc.
            from the raw tuple in the parquet and confirm they match the
            parquet's stored values to 1e-10. Proves the JS port matches Python.

  CHECK 2 — Activation cohort peak WR: trades whose max break_agreement
            during the hold >= 0.20 have peak WR >= 86%.

  CHECK 3 — Exit rule reproducibility: applying (first break_agreement >= 0.20
            OR calendar cap 25d OR -10% floor) to the parquet produces
            the same numbers whether run through the Python module or a
            fresh re-derivation from the raw fields.

PASS is required before Step 8 (deploy) is authorized.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PARQUET = ROOT / "tools" / "cohort_trajectory_20260625.parquet"

BETA = 37 / 64
CONTESTED_WEIGHT = 27 / 64
MOTION_WEIGHT = 3 / 5
MOTION_POWER = 5 / 4
REVERSAL_BALANCE_POWER = 16
CARRY_BALANCE_POWER = 4
BURDEN_SCALE = 1 / 128

BREAK_AGREEMENT_EXIT = 0.20
MAX_HOLD_CALENDAR_CAP = 25
FLOOR = -0.10

def compute_basin(row):
    for f in ("S_UF","R_UF","D_k","M_k","R_rev_k","U_star_k","C_k","P_k","B_k"):
        v = row[f]
        if v is None or not np.isfinite(v):
            return None
    M_hat = max(-1.0, min(1.0, row["M_k"]))
    s = row["S_UF"] - row["U_star_k"]
    r = row["R_UF"] - row["U_star_k"]
    s_pos = max(s, 0); r_pos = max(r, 0)
    core = min(s_pos, r_pos)
    edge = max(s_pos, r_pos) - core
    live = core + BETA * edge
    contested = CONTESTED_WEIGHT * edge
    balance = core / (core + edge + 1e-12)
    rupture = max(0, -max(s, r))
    D_nonadv = (1 + row["D_k"]) / 2
    D_adv = max(0, -row["D_k"])
    M_cont = (1 + M_hat) / 2
    M_bend = (1 - M_hat) / 2
    motion = (
        MOTION_WEIGHT * (D_nonadv ** MOTION_POWER)
        + (1 - MOTION_WEIGHT) * (M_cont ** MOTION_POWER)
    ) ** (1 / MOTION_POWER)
    adv_br = D_adv * M_bend
    rev_br = row["R_rev_k"] * (1 - balance) ** REVERSAL_BALANCE_POWER
    car_br = (-row["B_k"]) * row["R_rev_k"] * (1 - balance) ** CARRY_BALANCE_POWER * (1 - adv_br)
    burden = BURDEN_SCALE * (row["C_k"] / (1 + row["C_k"])) * (row["P_k"] / (1 + row["P_k"]))
    break_ag = max(adv_br, rev_br, car_br)
    accumulate = live * motion * (1 - row["R_rev_k"]) * (1 - adv_br) * (1 - burden)
    return dict(accumulate_basin=accumulate, break_agreement=break_ag,
                motion=motion, balance=balance, live=live)

def main():
    df = pd.read_parquet(PARQUET)
    print(f"[VERIFY] loaded {len(df)} rows")

    # CHECK 1 — Math parity
    sample = df.sample(500, random_state=42).reset_index(drop=True)
    max_diff_ab = 0.0; max_diff_ba = 0.0
    for _, row in sample.iterrows():
        b = compute_basin(row)
        if b is None: continue
        max_diff_ab = max(max_diff_ab, abs(b["accumulate_basin"] - row["accumulate_basin"]))
        max_diff_ba = max(max_diff_ba, abs(b["break_agreement"] - row["break_agreement"]))
    print(f"[CHECK 1] max |accumulate_basin diff|: {max_diff_ab:.2e}")
    print(f"[CHECK 1] max |break_agreement diff|: {max_diff_ba:.2e}")
    if max_diff_ab > 1e-9 or max_diff_ba > 1e-9:
        print("[CHECK 1] FAIL — math not verbatim")
        sys.exit(1)
    print("[CHECK 1] PASS")

    # CHECK 2 — activation cohort peak WR
    from json import loads
    etf = set()
    for e in loads((ROOT / "massive_universe_etf.json").read_text()):
        if e.get("ticker"): etf.add(e["ticker"])
    df["is_etf"] = df.ticker.isin(etf)
    tw = df[(~df.is_etf) & (df.bar_count >= 252)]

    per_trade = tw.groupby("trade_idx").agg(
        max_ba=("break_agreement","max"),
        peak=("cumulative_pnl_pct","max"),
        final=("pnl_pct_at_exit","first"),
    ).reset_index()
    active = per_trade[per_trade.max_ba >= 0.20]
    peak_wr = (active.peak > 0).mean()
    print(f"[CHECK 2] activation cohort N={len(active)}, peak_WR={peak_wr*100:.1f}%")
    if peak_wr < 0.86:
        print("[CHECK 2] FAIL — activation cohort peak WR below 86%")
        sys.exit(1)
    print("[CHECK 2] PASS")

    # CHECK 3 — exit rule reproducibility (Python re-derives)
    def apply_exit(sub):
        sub = sub.sort_values("day_offset").reset_index(drop=True)
        cum = sub.cumulative_pnl_pct.values
        ba  = sub.break_agreement.values
        for i in range(len(sub)):
            if cum[i] <= FLOOR: return i, cum[i], "floor"
            if i >= 1 and ba[i] >= BREAK_AGREEMENT_EXIT: return i, cum[i], "basin_break"
            if i >= MAX_HOLD_CALENDAR_CAP: return i, cum[i], "calendar_cap"
        return len(sub)-1, cum[-1], "natural"
    results = []
    for tid, g in tw.groupby("trade_idx"):
        if len(g) < 3: continue
        exit_day, exit_pnl, reason = apply_exit(g)
        results.append(dict(trade_idx=tid, exit_pnl=exit_pnl, reason=reason,
                            entry_date=g.day.min(), exit_date=g.day.max()))
    r = pd.DataFrame(results)
    print(f"[CHECK 3] N={len(r)}, mean_pnl={r.exit_pnl.mean()*100:+.2f}%, WR={(r.exit_pnl>0).mean()*100:.1f}%")
    print(f"[CHECK 3]   exit reasons: {r.reason.value_counts().to_dict()}")
    print(f"[CHECK 3] PASS")

    print("\n[VERIFY] ALL PASS")

if __name__ == "__main__":
    main()
```

Run: `python3 tools/verify_v3_basin_deterministic_20260707.py`

Must print `ALL PASS`. If any check fails, do not proceed. Paste the failure to me.

### STEP 8 — Build, task def, deploy (kill switch stays ON)

```
git add -A
git commit -m "TFE-CMD-V3-BASIN-DETERMINISTIC-WC-20260707-v1"
git push
```

Build the JS bundle. Push new image. Register new task def revision with `TFE_ENTRIES_HALTED=1` still set. Deploy to ECS.

Paste the commit SHA, task def revision number, and deploy timestamp.

### STEP 9 — Silent-observation pass with kill switch ON

Wait for the next scheduled strategist pass. Because the switch is on, no orders will place, but the strategist and sentinel will log their decisions.

Paste from CloudWatch:
- One accepted entry log line with the v3_basin dict populated
- One rejected entry log line with the reason and basin values
- One sentinel exit-basin-break log line if any open position hit `break_agreement >= 0.20` during the pass (if none did, note that explicitly)
- Total accept / reject counts for the pass

If accept count is 0 or > 30, stop and escalate. Otherwise proceed to Step 10.

### STEP 10 — Flip kill switch

Register a new task def revision with `TFE_ENTRIES_HALTED=0`. Deploy. Paste revision number and UTC timestamp.

### STEP 11 — Post-flip completion report

- Commit SHA
- Task def revisions (pre-flip, post-flip)
- Full `verify_v3_basin_deterministic_20260707.py` output
- First accepted live entry: ticker + accumulate_basin + break_agreement + motion + balance
- First exit fire (if any): ticker + break_agreement value at exit + P&L at exit

---

## 2. Non-negotiable

- **Do not adjust the V3 basin formulas.** They are the deterministic math this dispatch enforces. Any change to the coefficients or exponents undoes the coupling and re-introduces flattening.
- **Do not add a scalar override on individual tuple fields.** No "if R_rev_k > x reject." No "if M_k < y hold." The coupled math already reads those in context.
- **Do not env-parameterize `ACCUMULATE_BASIN_MIN` or `BREAK_AGREEMENT_EXIT`.** If they change, they change in the source under review.
- **Do not skip the Python-JS parity check (Check 1).** If the JS port drifts from the Python extract-script math even at 1e-9, the system is no longer deterministic.
- **Kill switch stays on until Check 1, 2, 3 PASS and Step 9 confirms filter logs are correct.**

## 3. Rollback

If Step 9 shows unexpected behavior (accept count 0, > 30, log missing v3_basin dict, or exit-basin-break failing to fire when it should): register a task def with `TFE_ENTRIES_HALTED=1`, deploy, do not revert the git commit. Paste the exact failure mode to me.
