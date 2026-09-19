"""Does the CH2 entry gate beat chance? — the measurement declared in
docs/CH2_ENTRY_GATE_VS_CHANCE_DECLARATION_20260919.md.

No adaptive exits: a position is opened at the close after the signal and held
a fixed number of sessions. The gate's picks are compared with random entries
in the same stocks, same window, same counts, same holds, judged on mean
return per position across 200 seeds.

Usage:
  PYTHONHASHSEED=0 python tools/ch2_entry_gate_vs_chance.py \
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
    GATE_ACC_MIN, GATE_BREAK_MAX, GATE_BARS_MIN, basin_frame, verify_vectorised,
)
from ch2_holding_length_measure import LIQ_FLOOR_USD, LIQ_WINDOW, PRICE_FLOOR  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "ch4_uf" / "ch2_entry_gate_vs_chance_20260919.json"

HOLDS = [5, 10, 20, 30, 60]
SEEDS = 200
SPLIT = np.datetime64("2024-03-15", "D")


def block(rets: np.ndarray) -> dict:
    if not len(rets):
        return {"positions": 0}
    return {"positions": int(len(rets)), "mean_pct": float(rets.mean() * 100),
            "median_pct": float(np.median(rets) * 100),
            "win_rate_pct": float((rets > 0).mean() * 100),
            "total_pct": float(rets.sum() * 100)}


def main() -> int:
    lanes = pd.read_csv(sys.argv[1], parse_dates=["d"])
    lanes = lanes.dropna(subset=["s_uf", "r_uf", "d_k", "m_k", "r_rev_k", "u_star_k", "c_k", "p_k", "b_k"])
    lanes = lanes.sort_values(["ticker", "d"]).reset_index(drop=True)
    port = verify_vectorised(lanes)
    print(f"[gate] port check {port}", flush=True)
    if port["decision_mismatches"]:
        print("[gate] ABORT: basin disagreement"); return 1

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

    # gate fill indices per ticker
    gate_idx: dict[str, np.ndarray] = {}
    total_signals = kept = 0
    for ticker, gl in lanes.groupby("ticker", sort=False):
        grp = groups.get(ticker)
        if grp is None:
            continue
        d, close, ok = grp
        sig_dates = gl.d.values.astype("datetime64[D]")[gl.entry_ok.values]
        total_signals += len(sig_dates)
        if not len(sig_dates):
            continue
        j = np.searchsorted(d, sig_dates, side="right")
        j = j[(j < len(d))]
        j = j[ok[j]]
        if len(j):
            gate_idx[ticker] = j
            kept += len(j)
    print(f"[gate] signals={total_signals} kept after floors={kept} tickers={len(gate_idx)}", flush=True)

    def rets_for(idx_map, hold):
        out, dates = [], []
        for ticker, js in idx_map.items():
            d, close, _ = groups[ticker]
            end = js + hold
            m = end < len(close)
            j2, e2 = js[m], end[m]
            if not len(j2):
                continue
            out.append(close[e2] / close[j2] - 1.0)
            dates.append(d[j2])
        if not out:
            return np.array([]), np.array([], dtype="datetime64[D]")
        return np.concatenate(out), np.concatenate(dates)

    results = {}
    for hold in HOLDS:
        g_ret, g_date = rets_for(gate_idx, hold)
        gate_all = block(g_ret)
        gate_h1 = block(g_ret[g_date < SPLIT]); gate_h2 = block(g_ret[g_date >= SPLIT])

        means, means_h1, means_h2 = [], [], []
        for seed in range(SEEDS):
            rng = np.random.default_rng(90000 + seed * 13 + hold)
            rnd_map = {}
            for ticker, js in gate_idx.items():
                d, close, ok = groups[ticker]
                eligible = np.flatnonzero(ok)
                eligible = eligible[eligible + hold < len(close)]
                if not len(eligible):
                    continue
                rnd_map[ticker] = rng.choice(eligible, size=len(js),
                                             replace=len(eligible) < len(js))
            r_ret, r_date = rets_for(rnd_map, hold)
            if len(r_ret):
                means.append(float(r_ret.mean() * 100))
                if (r_date < SPLIT).any():
                    means_h1.append(float(r_ret[r_date < SPLIT].mean() * 100))
                if (r_date >= SPLIT).any():
                    means_h2.append(float(r_ret[r_date >= SPLIT].mean() * 100))
        nm = np.array(means)
        null = {"seeds": len(means), "mean_pct": float(nm.mean()),
                "p05": float(np.percentile(nm, 5)), "p95": float(np.percentile(nm, 95)),
                "h1_mean_pct": float(np.mean(means_h1)) if means_h1 else None,
                "h1_p95": float(np.percentile(means_h1, 95)) if means_h1 else None,
                "h2_mean_pct": float(np.mean(means_h2)) if means_h2 else None,
                "h2_p95": float(np.percentile(means_h2, 95)) if means_h2 else None}
        beats = bool(gate_all["mean_pct"] > null["p95"])
        beats_h1 = bool(null["h1_p95"] is not None and gate_h1.get("mean_pct", -1e9) > null["h1_p95"])
        beats_h2 = bool(null["h2_p95"] is not None and gate_h2.get("mean_pct", -1e9) > null["h2_p95"])
        results[f"hold_{hold}"] = {"gate": gate_all, "gate_first_half": gate_h1,
                                   "gate_second_half": gate_h2, "null": null,
                                   "beats_null": beats, "beats_null_first_half": beats_h1,
                                   "beats_null_second_half": beats_h2}
        print(f"[gate] hold={hold:3d} n={gate_all['positions']:5d} gate_mean={gate_all['mean_pct']:+6.2f}% "
              f"null_mean={null['mean_pct']:+6.2f}% null_p95={null['p95']:+6.2f}% "
              f"beats={beats} h1={beats_h1} h2={beats_h2}", flush=True)

    n_beat = sum(1 for v in results.values() if v["beats_null"])
    n_both = sum(1 for v in results.values() if v["beats_null_first_half"] and v["beats_null_second_half"])
    verdict = ("the gate beat chance on this test" if n_beat > len(HOLDS) / 2 and n_both > len(HOLDS) / 2
               else "the gate did NOT beat chance on this test")
    out = {"declaration": "docs/CH2_ENTRY_GATE_VS_CHANCE_DECLARATION_20260919.md",
           "generated_at_utc": pd.Timestamp.utcnow().isoformat(),
           "signals": total_signals, "positions_after_floors": kept,
           "port_check": port, "holds": results,
           "holds_beating_null": n_beat, "holds_beating_null_in_both_halves": n_both,
           "verdict": verdict, "costs_modeled": False, "prices": "closes only"}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, default=str))
    print(f"[gate] VERDICT: {verdict} ({n_beat}/{len(HOLDS)} holds, {n_both} in both halves)", flush=True)
    print(f"[gate] written {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
