"""Which CH2 exit rule subtracts? — the measurement declared in
docs/CH2_EXIT_RULE_COST_DECLARATION_20260919.md.

Same entries and floors as the entry-gate measurement. Holds blind to a fixed
horizon as the baseline, then adds exactly one exit rule at a time, then the
whole law. For every rule it reports the fired set — what the rule realised
against what those same positions would have made held to the horizon — and an
exit-timing null. It ships nothing.

Usage:
  PYTHONHASHSEED=0 python tools/ch2_exit_rule_cost.py \
      artifacts/ch4_uf/ch2_lanes_20260919.csv.gz ch4_live_store.parquet
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ch2_winner_exit_measure import (  # noqa: E402
    GATE_ACC_MIN, GATE_BREAK_MAX, GATE_BARS_MIN, DEAD_DAMAGE_PCT, DEAD_SESSIONS,
    WALL_DAYS, BRAKE_PCT, RATCHET_ENGAGE, RATCHET_GIVEBACK,
    basin_frame, verify_vectorised,
)
from ch2_holding_length_measure import LIQ_FLOOR_USD, LIQ_WINDOW, PRICE_FLOOR  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "ch4_uf" / "ch2_exit_rule_cost_20260919.json"

HORIZONS = [30, 60]
RULES = ["brake", "dead_clock", "ratchet", "wall", "full_law"]
SEEDS = 200
SPLIT = np.datetime64("2024-03-15", "D")


def simulate(close, dates, j, horizon, rules):
    """Return (ret, exit_offset, reason) for one position under a rule set."""
    entry = close[j]
    damage_line = entry * (1 - DEAD_DAMAGE_PCT)
    brake_line = entry * (1 - BRAKE_PCT)
    peak = entry
    below = 0
    last = min(j + horizon, len(close) - 1)
    for k in range(j, last + 1):
        px = close[k]
        off = k - j
        if off >= horizon:
            return px / entry - 1.0, off, "horizon"
        if "brake" in rules and px <= brake_line:
            return px / entry - 1.0, off, "brake"
        peak = max(peak, px)
        if "ratchet" in rules and peak >= entry * (1 + RATCHET_ENGAGE):
            floor = entry + (peak - entry) * (1 - RATCHET_GIVEBACK)
            if px <= floor:
                return px / entry - 1.0, off, "ratchet"
        if "dead_clock" in rules:
            below = below + 1 if px <= damage_line else 0
            if below > DEAD_SESSIONS:
                nk = min(k + 1, len(close) - 1)
                return close[nk] / entry - 1.0, nk - j, "dead_clock"
        if "wall" in rules and (dates[k] - dates[j]).astype("timedelta64[D]").astype(int) >= WALL_DAYS:
            nk = min(k + 1, len(close) - 1)
            return close[nk] / entry - 1.0, nk - j, "wall"
    return close[last] / entry - 1.0, last - j, "end_of_data"


def stats(rets, mask=None):
    r = rets if mask is None else rets[mask]
    if not len(r):
        return {"positions": 0}
    return {"positions": int(len(r)), "mean_pct": float(r.mean() * 100),
            "median_pct": float(np.median(r) * 100),
            "win_rate_pct": float((r > 0).mean() * 100),
            "total_pct": float(r.sum() * 100)}


def main() -> int:
    lanes = pd.read_csv(sys.argv[1], parse_dates=["d"])
    lanes = lanes.dropna(subset=["s_uf", "r_uf", "d_k", "m_k", "r_rev_k", "u_star_k", "c_k", "p_k", "b_k"])
    lanes = lanes.sort_values(["ticker", "d"]).reset_index(drop=True)
    port = verify_vectorised(lanes)
    print(f"[cost] port check {port}", flush=True)
    if port["decision_mismatches"]:
        return 1
    b = basin_frame(lanes)
    lanes["entry_ok"] = (b.is_acc.values & (b.acc.values >= GATE_ACC_MIN)
                         & (b.brk.values < GATE_BREAK_MAX)
                         & (lanes.bar_count.fillna(0).values > GATE_BARS_MIN))

    bars = pd.read_parquet(sys.argv[2], columns=["Date", "Symbol", "Close", "Volume"]).dropna()
    bars = bars.sort_values(["Symbol", "Date"])
    lo = lanes.d.min().to_datetime64().astype("datetime64[D]")
    hi = lanes.d.max().to_datetime64().astype("datetime64[D]")
    groups = {}
    for sym, g in bars.groupby("Symbol", sort=False):
        close = g.Close.values.astype(float)
        d = g.Date.values.astype("datetime64[D]")
        liq = pd.Series(close * g.Volume.values.astype(float)).rolling(
            LIQ_WINDOW, min_periods=LIQ_WINDOW).median().values
        ok = np.nan_to_num((liq >= LIQ_FLOOR_USD), nan=0).astype(bool) & (close >= PRICE_FLOOR)
        groups[sym] = (d, close, ok & (d >= lo) & (d <= hi))

    positions = []  # (ticker, fill index, entry date)
    for ticker, gl in lanes.groupby("ticker", sort=False):
        grp = groups.get(ticker)
        if grp is None:
            continue
        d, close, ok = grp
        sig = gl.d.values.astype("datetime64[D]")[gl.entry_ok.values]
        if not len(sig):
            continue
        j = np.searchsorted(d, sig, side="right")
        j = j[j < len(d)]
        j = j[ok[j]]
        for x in j:
            positions.append((ticker, int(x), d[int(x)]))
    print(f"[cost] positions={len(positions)}", flush=True)

    out = {"declaration": "docs/CH2_EXIT_RULE_COST_DECLARATION_20260919.md",
           "generated_at_utc": pd.Timestamp.utcnow().isoformat(),
           "positions": len(positions), "port_check": port,
           "horizons": {}, "costs_modeled": False, "prices": "closes only"}

    for horizon in HORIZONS:
        usable = [(t, j, dt) for t, j, dt in positions if j + horizon < len(groups[t][1])]
        entry_dates = np.array([dt for _, _, dt in usable])
        base = np.array([groups[t][1][j + horizon] / groups[t][1][j] - 1.0 for t, j, _ in usable])
        h = {"baseline_hold_blind": stats(base),
             "baseline_first_half": stats(base, entry_dates < SPLIT),
             "baseline_second_half": stats(base, entry_dates >= SPLIT),
             "rules": {}}
        print(f"[cost] horizon={horizon} n={len(usable)} blind mean={base.mean()*100:+.2f}%", flush=True)

        for rule in RULES:
            rules = {"brake", "dead_clock", "ratchet", "wall"} if rule == "full_law" else {rule}
            rets = np.empty(len(usable)); offs = np.empty(len(usable), int)
            fired = np.zeros(len(usable), bool)
            for i, (t, j, _) in enumerate(usable):
                d, close, _ = groups[t]
                r, off, reason = simulate(close, d, j, horizon, rules)
                rets[i] = r; offs[i] = off; fired[i] = reason not in ("horizon", "end_of_data")
            delta = float((rets.mean() - base.mean()) * 100)
            fired_cost = float((rets[fired] - base[fired]).sum() * 100) if fired.any() else 0.0
            med_off = int(np.median(offs[fired])) if fired.any() else 0

            # exit-timing null: same count, drawn from positions the rule did NOT
            # fire on, exited at the rule's own median firing session
            null_means = []
            if fired.any() and (~fired).sum() > 0:
                pool = np.flatnonzero(~fired)
                for seed in range(SEEDS):
                    rng = np.random.default_rng(31000 + seed * 7 + horizon)
                    pick = rng.choice(pool, size=min(int(fired.sum()), len(pool)), replace=False)
                    alt = rets.copy()
                    for i in pick:
                        t, j, _ = usable[i]
                        d, close, _ = groups[t]
                        k = min(j + med_off, len(close) - 1)
                        alt[i] = close[k] / close[j] - 1.0
                    null_means.append(float(alt.mean() * 100))
            nm = np.array(null_means) if null_means else np.array([rets.mean() * 100])

            h["rules"][rule] = {
                "run": stats(rets), "first_half": stats(rets, entry_dates < SPLIT),
                "second_half": stats(rets, entry_dates >= SPLIT),
                "delta_vs_blind_pct_points": delta,
                "fired_positions": int(fired.sum()),
                "fired_median_session": med_off,
                "fired_realised_mean_pct": float(rets[fired].mean() * 100) if fired.any() else None,
                "fired_if_held_mean_pct": float(base[fired].mean() * 100) if fired.any() else None,
                "fired_total_cost_pct_points": fired_cost,
                "timing_null_mean_pct": float(nm.mean()),
                "timing_null_p05": float(np.percentile(nm, 5)),
                "timing_null_p95": float(np.percentile(nm, 95)),
                "worse_than_arbitrary_exit": bool(rets.mean() * 100 < np.percentile(nm, 5)),
            }
            r = h["rules"][rule]
            print(f"[cost]   {rule:11s} mean={r['run']['mean_pct']:+6.2f}% "
                  f"delta={delta:+6.2f} fired={r['fired_positions']:5d}@{med_off:3d} "
                  f"realised={r['fired_realised_mean_pct'] if r['fired_realised_mean_pct'] is None else round(r['fired_realised_mean_pct'],2)}% "
                  f"vs_held={r['fired_if_held_mean_pct'] if r['fired_if_held_mean_pct'] is None else round(r['fired_if_held_mean_pct'],2)}% "
                  f"null={r['timing_null_mean_pct']:+6.2f}% worse_than_random={r['worse_than_arbitrary_exit']}", flush=True)

        out["horizons"][str(horizon)] = h

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, default=str))
    print(f"[cost] written {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
