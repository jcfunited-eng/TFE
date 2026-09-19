"""Is the gate's own strength ranking inverted? — declared in the result
section of docs/CH2_BOOK_NULL_UNIVERSE_DECLARATION_20260919.md.

Forward returns of every gate signal, bucketed by accumulate_basin decile,
at the declared holds. Nothing is fitted and nothing is swept: the deciles are
the gate's own number, the holds are the ones already in use.

Usage:
  PYTHONHASHSEED=0 python tools/ch2_basin_rank_test.py \
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
OUT = ROOT / "artifacts" / "ch4_uf" / "ch2_basin_rank_20260919.json"
HOLDS = [30, 60]
SPLIT = np.datetime64("2024-03-15", "D")


def main() -> int:
    lanes = pd.read_csv(sys.argv[1], parse_dates=["d"])
    lanes = lanes.dropna(subset=["s_uf", "r_uf", "d_k", "m_k", "r_rev_k", "u_star_k", "c_k", "p_k", "b_k"])
    lanes = lanes.sort_values(["ticker", "d"]).reset_index(drop=True)
    port = verify_vectorised(lanes)
    print(f"[rank] port check {port}", flush=True)
    if port["decision_mismatches"]:
        return 1
    bf = basin_frame(lanes)
    lanes["acc"] = bf.acc.values
    lanes["entry_ok"] = (bf.is_acc.values & (bf.acc.values >= GATE_ACC_MIN)
                         & (bf.brk.values < GATE_BREAK_MAX)
                         & (lanes.bar_count.fillna(0).values > GATE_BARS_MIN))

    bars_df = pd.read_parquet(sys.argv[2], columns=["Date", "Symbol", "Close", "Volume"]).dropna()
    bars_df = bars_df.sort_values(["Symbol", "Date"])
    lo = lanes.d.min().to_datetime64().astype("datetime64[D]")
    hi = lanes.d.max().to_datetime64().astype("datetime64[D]")
    bars = {}
    for sym, g in bars_df.groupby("Symbol", sort=False):
        close = g.Close.values.astype(float)
        d = g.Date.values.astype("datetime64[D]")
        liq = pd.Series(close * g.Volume.values.astype(float)).rolling(
            LIQ_WINDOW, min_periods=LIQ_WINDOW).median().values
        ok = np.nan_to_num((liq >= LIQ_FLOOR_USD), nan=0).astype(bool) & (close >= PRICE_FLOOR)
        bars[sym] = (d, close, ok)

    rows = []
    sig = lanes[lanes.entry_ok]
    for ticker, gl in sig.groupby("ticker", sort=False):
        grp = bars.get(ticker)
        if grp is None:
            continue
        d, close, ok = grp
        j = np.searchsorted(d, gl.d.values.astype("datetime64[D]"), side="right")
        for jj, acc in zip(j, gl.acc.values):
            if jj < len(d) and ok[jj] and lo <= d[jj] <= hi:
                rows.append((ticker, int(jj), float(acc), d[jj]))
    print(f"[rank] signals={len(rows)}", flush=True)

    out = {"generated_at_utc": pd.Timestamp.utcnow().isoformat(), "port_check": port,
           "signals": len(rows), "holds": {}}
    accs = np.array([r[2] for r in rows])
    dates = np.array([r[3] for r in rows])
    edges = np.percentile(accs, np.arange(0, 101, 10))

    for hold in HOLDS:
        rets = np.full(len(rows), np.nan)
        for i, (t, jj, _, _) in enumerate(rows):
            _, close, _ = bars[t]
            if jj + hold < len(close):
                rets[i] = close[jj + hold] / close[jj] - 1.0
        m = np.isfinite(rets)
        dec = np.clip(np.digitize(accs[m], edges[1:-1]), 0, 9)
        r, dt = rets[m], dates[m]
        buckets = []
        for k in range(10):
            sel = dec == k
            if not sel.any():
                buckets.append({"decile": k + 1, "positions": 0}); continue
            h1 = sel & (dt < SPLIT); h2 = sel & (dt >= SPLIT)
            buckets.append({"decile": k + 1, "positions": int(sel.sum()),
                            "basin_range": [float(edges[k]), float(edges[k + 1])],
                            "mean_pct": float(r[sel].mean() * 100),
                            "median_pct": float(np.median(r[sel]) * 100),
                            "win_rate_pct": float((r[sel] > 0).mean() * 100),
                            "first_half_mean_pct": float(r[h1].mean() * 100) if h1.any() else None,
                            "second_half_mean_pct": float(r[h2].mean() * 100) if h2.any() else None})
        top, bottom = buckets[9], buckets[0]
        spread = top["mean_pct"] - bottom["mean_pct"]
        # rank correlation between the gate's own score and the outcome
        order = np.argsort(accs[m]); ranks = np.empty(len(order)); ranks[order] = np.arange(len(order))
        order_r = np.argsort(r); ranks_r = np.empty(len(order_r)); ranks_r[order_r] = np.arange(len(order_r))
        rho = float(np.corrcoef(ranks, ranks_r)[0, 1])
        out["holds"][str(hold)] = {"deciles": buckets, "top_minus_bottom_pct_points": spread,
                                   "rank_correlation": rho}
        print(f"[rank] hold={hold}: D1={bottom['mean_pct']:+.2f}% D10={top['mean_pct']:+.2f}% "
              f"spread={spread:+.2f} rank_corr={rho:+.4f}", flush=True)
        for bkt in buckets:
            if bkt["positions"]:
                print(f"[rank]   D{bkt['decile']:<2d} n={bkt['positions']:5d} mean={bkt['mean_pct']:+6.2f}% "
                      f"win={bkt['win_rate_pct']:.1f}% h1={bkt['first_half_mean_pct'] if bkt['first_half_mean_pct'] is None else round(bkt['first_half_mean_pct'],2)} "
                      f"h2={bkt['second_half_mean_pct'] if bkt['second_half_mean_pct'] is None else round(bkt['second_half_mean_pct'],2)}", flush=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, default=str))
    print(f"[rank] written {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
