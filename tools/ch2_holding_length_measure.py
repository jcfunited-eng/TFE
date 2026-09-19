"""CH2 holding length — the measurement declared in
docs/CH2_HOLDING_LENGTH_MEASUREMENT_DECLARATION_20260919.md.

Same entries, same timing and the same verified entry math as the winner-exit
measurement; adds the declared liquidity and price floors, measures four
holding caps against the current law, and tests each against random-entry
positions of the same length. Reports what happened, win or fail.

Usage:
  PYTHONHASHSEED=0 python tools/ch2_holding_length_measure.py \
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
    WALL_DAYS, BRAKE_PCT, RATCHET_ENGAGE, RATCHET_GIVEBACK, SLICE_DOLLARS,
    basin_frame, summarise, verify_vectorised, walk,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "ch4_uf" / "ch2_holding_length_measurement_20260919.json"

# ── Declared constants (declaration §Population, §Candidates) ────────────
LIQ_WINDOW = 20
LIQ_FLOOR_USD = 5_000_000.0
PRICE_FLOOR = 5.00
CAPS = {"H10": 10, "H20": 20, "H30": 30, "H45": 45}
NULL_SEEDS = 20


def walk_random_entries(n_entries, cap, bar_dates, bar_closes, liq_ok, rng,
                        window=None):
    """Positions opened on random eligible sessions, same cap and control rules.

    `window` restricts the draw to the measurement window: without it the draw
    reaches back to the start of the bar store (2016) and answers a different
    question over a different period. `n_entries` must be the candidate's OWN
    position count for this ticker, because the comparison is a sum.
    """
    out = []
    ok = liq_ok.copy()
    if window is not None:
        lo, hi = window
        ok &= (bar_dates >= lo) & (bar_dates <= hi)
    eligible = np.flatnonzero(ok[:-1]) if len(ok) > 1 else np.array([], int)
    if len(eligible) == 0 or n_entries <= 0:
        return out
    for j in rng.choice(eligible, size=min(n_entries, len(eligible)), replace=False):
        j = int(j)
        entry_price = bar_closes[j]
        if not np.isfinite(entry_price) or entry_price <= 0:
            continue
        entry_date = bar_dates[j]
        damage_line = entry_price * (1 - DEAD_DAMAGE_PCT)
        brake_line = entry_price * (1 - BRAKE_PCT)
        peak = entry_price
        below_run = 0
        exit_price = exit_date = reason = None
        k = j
        while k < len(bar_dates):
            px = bar_closes[k]
            held = k - j
            if held >= cap:
                exit_price, exit_date, reason = px, bar_dates[k], "cap"
                break
            if px <= brake_line:
                exit_price, exit_date, reason = px, bar_dates[k], "brake"
                break
            peak = max(peak, px)
            if peak >= entry_price * (1 + RATCHET_ENGAGE):
                floor = entry_price + (peak - entry_price) * (1 - RATCHET_GIVEBACK)
                if px <= floor:
                    exit_price, exit_date, reason = px, bar_dates[k], "ratchet"
                    break
            below_run = below_run + 1 if px <= damage_line else 0
            if below_run > DEAD_SESSIONS:
                nk = min(k + 1, len(bar_dates) - 1)
                exit_price, exit_date, reason = bar_closes[nk], bar_dates[nk], "dead_clock"
                break
            if (bar_dates[k] - entry_date).astype("timedelta64[D]").astype(int) >= WALL_DAYS:
                nk = min(k + 1, len(bar_dates) - 1)
                exit_price, exit_date, reason = bar_closes[nk], bar_dates[nk], "wall"
                break
            k += 1
        if exit_price is None:
            k = len(bar_dates) - 1
            exit_price, exit_date, reason = bar_closes[k], bar_dates[k], "window_end"
        out.append({"entry_date": str(np.datetime_as_string(entry_date, unit="D")),
                    "exit_date": str(np.datetime_as_string(exit_date, unit="D")),
                    "ret": float(exit_price / entry_price - 1.0), "held": int(k - j),
                    "reason": reason})
    return out


def main() -> int:
    lanes_path = Path(sys.argv[1]); bars_path = Path(sys.argv[2])
    lanes = pd.read_csv(lanes_path, parse_dates=["d"])
    lanes = lanes.dropna(subset=["s_uf", "r_uf", "d_k", "m_k", "r_rev_k", "u_star_k", "c_k", "p_k", "b_k"])
    lanes = lanes.sort_values(["ticker", "d"]).reset_index(drop=True)
    port = verify_vectorised(lanes)
    print(f"[holding] port check {port}", flush=True)
    if port["decision_mismatches"]:
        print("[holding] ABORT: basin disagreement"); return 1

    b = basin_frame(lanes)
    lanes["entry_ok"] = (b.is_acc.values & (b.acc.values >= GATE_ACC_MIN)
                         & (b.brk.values < GATE_BREAK_MAX)
                         & (lanes.bar_count.fillna(0).values > GATE_BARS_MIN))
    print(f"[holding] unfiltered entry signals: {int(lanes.entry_ok.sum())}", flush=True)

    bars = pd.read_parquet(bars_path, columns=["Date", "Symbol", "Close", "Volume"]).dropna()
    bars = bars.sort_values(["Symbol", "Date"])
    groups = {}
    for sym, g in bars.groupby("Symbol", sort=False):
        close = g.Close.values.astype(float)
        dollar = close * g.Volume.values.astype(float)
        liq = pd.Series(dollar).rolling(LIQ_WINDOW, min_periods=LIQ_WINDOW).median().values
        ok = (liq >= LIQ_FLOOR_USD) & (close >= PRICE_FLOOR)
        groups[sym] = (g.Date.values.astype("datetime64[D]"), close, np.nan_to_num(ok, nan=0).astype(bool))
    print(f"[holding] bar symbols={len(groups)}", flush=True)

    units = []
    kept = dropped = 0
    for ticker, gl in lanes.groupby("ticker", sort=False):
        grp = groups.get(ticker)
        if grp is None:
            continue
        bd, bc, ok = grp
        # a signal survives only if the bar it would fill on passes both floors
        sig = gl.entry_ok.values.copy()
        if sig.any():
            fill_idx = np.searchsorted(bd, gl.d.values.astype("datetime64[D]"), side="right")
            valid = fill_idx < len(bd)
            keep = np.zeros(len(sig), bool)
            keep[valid] = ok[fill_idx[valid]]
            dropped += int((sig & ~keep).sum()); kept += int((sig & keep).sum())
            sig = sig & keep
        units.append((ticker, gl.d.values.astype("datetime64[D]"), sig, bd, bc, ok))
    print(f"[holding] entry signals kept={kept} dropped_by_floors={dropped}", flush=True)

    lane_lo = lanes.d.min().to_datetime64().astype("datetime64[D]")
    lane_hi = lanes.d.max().to_datetime64().astype("datetime64[D]")

    def run(cap=None):
        pos = []
        counts = {}
        for ticker, d, sig, bd, bc, _ in units:
            got = walk(d, None, sig, None, bd, bc, forced_len=cap)
            if got:
                counts[ticker] = len(got)
            pos += got
        return pos, counts

    runs = {}
    run_counts = {}
    for label, cap in [("control", None)] + list(CAPS.items()):
        pos, counts = run(cap)
        run_counts[label] = counts
        runs[label] = summarise(pos, label)
        a = runs[label]["all"]
        print(f"[holding] {label}: n={a['positions']} total={a['total_return_pct']:.1f}% "
              f"${a['dollars']:.0f} mean={a['mean_pct']:+.2f}% win={a['win_rate_pct']:.1f}% "
              f"hold={a['mean_hold_sessions']:.1f} h1={runs[label]['first_half'].get('total_return_pct',0):.1f}% "
              f"h2={runs[label]['second_half'].get('total_return_pct',0):.1f}%", flush=True)

    ctrl_total = runs["control"]["all"]["total_return_pct"]
    nulls = {}
    for label, cap in CAPS.items():
        cand_total = runs[label]["all"]["total_return_pct"]
        if cand_total <= ctrl_total:
            nulls[label] = {"skipped": "did not beat the control", "candidate_total_pct": cand_total,
                            "control_total_pct": ctrl_total}
            continue
        totals = []
        for seed in range(NULL_SEEDS):
            rng = np.random.default_rng(5000 + seed)
            pos = []
            for ticker, d, sig, bd, bc, ok in units:
                n = run_counts[label].get(ticker, 0)
                if n:
                    pos += walk_random_entries(n, cap, bd, bc, ok, rng,
                                               window=(lane_lo, lane_hi))
            totals.append(float(np.array([p["ret"] for p in pos]).sum() * 100))
            null_positions = len(pos)
        p95 = float(np.percentile(totals, 95))
        nulls[label] = {"seeds": NULL_SEEDS, "mean_total_return_pct": float(np.mean(totals)),
                        "p05": float(np.percentile(totals, 5)), "p95": p95,
                        "candidate_total_pct": cand_total, "control_total_pct": ctrl_total,
                        "candidate_positions": runs[label]["all"]["positions"],
                        "null_positions_last_seed": null_positions,
                        "beats_null": bool(cand_total > p95)}
        print(f"[holding] null {label}: mean={nulls[label]['mean_total_return_pct']:.1f}% "
              f"p95={p95:.1f}% candidate={cand_total:.1f}% beats_null={nulls[label]['beats_null']}", flush=True)

    ships = [k for k in CAPS
             if runs[k]["all"]["total_return_pct"] > ctrl_total
             and runs[k]["first_half"].get("total_return_pct", -1e9) > runs["control"]["first_half"].get("total_return_pct", 0)
             and runs[k]["second_half"].get("total_return_pct", -1e9) > runs["control"]["second_half"].get("total_return_pct", 0)
             and nulls.get(k, {}).get("beats_null", False)]
    result = {"declaration": "docs/CH2_HOLDING_LENGTH_MEASUREMENT_DECLARATION_20260919.md",
              "generated_at_utc": pd.Timestamp.utcnow().isoformat(),
              "floors": {"liquidity_window": LIQ_WINDOW, "liquidity_usd": LIQ_FLOOR_USD,
                         "price": PRICE_FLOOR},
              "entry_signals_kept": kept, "entry_signals_dropped": dropped,
              "port_check": port, "runs": runs, "nulls": nulls,
              "passes_declared_bar": ships,
              "costs_modeled": False, "prices": "closes only"}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, default=str))
    print(f"[holding] passes declared bar: {ships or 'NONE'}", flush=True)
    print(f"[holding] written {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
