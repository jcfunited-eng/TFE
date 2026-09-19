"""Universe or picking? — the measurement declared in
docs/CH2_BOOK_NULL_UNIVERSE_DECLARATION_20260919.md.

One book, four references: the gate's live book, a random book restricted to
the gate's own signal universe, a random book over every liquid name, and SPY
bought and held. Same capital, same sizing, same exit law, same days.

Usage:
  PYTHONHASHSEED=0 python tools/ch2_book_null_universe.py \
      artifacts/ch4_uf/ch2_lanes_20260919.csv.gz ch4_live_store.parquet
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ch2_winner_exit_measure import (  # noqa: E402
    GATE_ACC_MIN, GATE_BREAK_MAX, GATE_BARS_MIN, basin_frame, verify_vectorised,
)
from ch2_holding_length_measure import LIQ_FLOOR_USD, LIQ_WINDOW, PRICE_FLOOR  # noqa: E402
from ch2_book_simulation import CAPITAL, COSTS_BPS, SPLIT, simulate_book  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "ch4_uf" / "ch2_book_null_universe_20260919.json"
SEEDS = 50


def main() -> int:
    lanes = pd.read_csv(sys.argv[1], parse_dates=["d"])
    lanes = lanes.dropna(subset=["s_uf", "r_uf", "d_k", "m_k", "r_rev_k", "u_star_k", "c_k", "p_k", "b_k"])
    lanes = lanes.sort_values(["ticker", "d"]).reset_index(drop=True)
    port = verify_vectorised(lanes)
    print(f"[uni] port check {port}", flush=True)
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

    day_signals: dict[np.datetime64, list] = defaultdict(list)
    sig = lanes[lanes.entry_ok]
    gate_universe = set()
    for ticker, gl in sig.groupby("ticker", sort=False):
        grp = bars.get(ticker)
        if grp is None:
            continue
        d, close, ok = grp
        j = np.searchsorted(d, gl.d.values.astype("datetime64[D]"), side="right")
        for jj, acc in zip(j, gl.acc.values):
            if jj < len(d) and ok[jj] and lo <= d[jj] <= hi:
                day_signals[d[jj]].append((ticker, float(acc)))
                gate_universe.add(ticker)
    for day in day_signals:
        day_signals[day].sort(key=lambda x: -x[1])
    calendar = np.array(sorted(day_signals.keys()))
    print(f"[uni] days={len(calendar)} signals={sum(len(v) for v in day_signals.values())} "
          f"gate universe={len(gate_universe)}", flush=True)

    broad_pool: dict[np.datetime64, list] = {}
    own_pool: dict[np.datetime64, list] = {}
    for day in calendar:
        broad, own = [], []
        for t, (d, c, ok) in bars.items():
            k = int(np.searchsorted(d, day, side="left"))
            if k < len(d) and d[k] == day and ok[k]:
                broad.append(t)
                if t in gate_universe:
                    own.append(t)
        broad_pool[day] = broad; own_pool[day] = own
    print(f"[uni] pools: broad median {int(np.median([len(v) for v in broad_pool.values()]))}/day, "
          f"own median {int(np.median([len(v) for v in own_pool.values()]))}/day", flush=True)

    def spy_hold(start, end):
        d, close, _ = bars.get("SPY", (None, None, None))
        if d is None:
            return {"note": "SPY not in the store"}
        m = (d >= start) & (d <= end)
        c = close[m]
        if len(c) < 2:
            return {"note": "insufficient SPY bars"}
        shares = int(CAPITAL // c[0])
        eq = shares * c + (CAPITAL - shares * c[0])
        peak = np.maximum.accumulate(eq)
        return {"return_pct": float((eq[-1] / CAPITAL - 1) * 100),
                "max_drawdown_pct": float(((eq - peak) / peak).min() * 100),
                "positions_taken": 1}

    windows = {"full": (lo, hi), "first_half": (lo, SPLIT), "second_half": (SPLIT, hi)}
    out = {"declaration": "docs/CH2_BOOK_NULL_UNIVERSE_DECLARATION_20260919.md",
           "generated_at_utc": pd.Timestamp.utcnow().isoformat(), "port_check": port,
           "gate_universe_tickers": len(gate_universe), "windows": {}}

    for wname, (ws, we) in windows.items():
        w = {"spy_hold": spy_hold(ws, we)}
        print(f"[uni] {wname}: SPY {w['spy_hold'].get('return_pct')}", flush=True)
        for cost in COSTS_BPS:
            c = {"gate": simulate_book(day_signals, bars, calendar, 1, cost, ws, we)}
            for nm, pool in (("null_own_universe", own_pool), ("null_broad_universe", broad_pool)):
                rets, dds = [], []
                for seed in range(SEEDS):
                    rng = np.random.default_rng(8800 + seed)
                    r = simulate_book(day_signals, bars, calendar, 1, cost, ws, we,
                                      rng=rng, random_pool=pool)
                    rets.append(r["return_pct"]); dds.append(r["max_drawdown_pct"])
                a = np.array(rets)
                c[nm] = {"seeds": SEEDS, "mean_return_pct": float(a.mean()),
                         "p05": float(np.percentile(a, 5)), "p95": float(np.percentile(a, 95)),
                         "mean_max_drawdown_pct": float(np.mean(dds))}
            c["gate_beats_own_universe_null"] = bool(c["gate"]["return_pct"] > c["null_own_universe"]["p95"])
            c["own_universe_worse_than_broad"] = bool(
                c["null_own_universe"]["mean_return_pct"] < c["null_broad_universe"]["p05"])
            w[f"cost_{int(cost)}bp"] = c
            print(f"[uni] {wname:12s} {cost:4.1f}bp gate={c['gate']['return_pct']:+6.1f}% "
                  f"own_null={c['null_own_universe']['mean_return_pct']:+6.1f}% "
                  f"(p95 {c['null_own_universe']['p95']:+.1f}) "
                  f"broad_null={c['null_broad_universe']['mean_return_pct']:+6.1f}% "
                  f"| gate>own_p95={c['gate_beats_own_universe_null']} "
                  f"own<broad_p05={c['own_universe_worse_than_broad']}", flush=True)
        out["windows"][wname] = w

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, default=str))
    print(f"[uni] written {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
