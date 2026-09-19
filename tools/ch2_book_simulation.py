"""CH2 book simulation — the measurement declared in
docs/CH2_BOOK_SIMULATION_DECLARATION_20260919.md.

A capacity-bounded book: $100,000, $2,500 slices, whole shares, cash-limited,
the live exit law, run day by day. One difference between the two runs: how
many positions a single stock may hold at once. A random-entry book of the
same shape is the null.

Usage:
  PYTHONHASHSEED=0 python tools/ch2_book_simulation.py \
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
    GATE_ACC_MIN, GATE_BREAK_MAX, GATE_BARS_MIN, DEAD_DAMAGE_PCT, DEAD_SESSIONS,
    WALL_DAYS, BRAKE_PCT, RATCHET_ENGAGE, RATCHET_GIVEBACK,
    basin_frame, verify_vectorised,
)
from ch2_holding_length_measure import LIQ_FLOOR_USD, LIQ_WINDOW, PRICE_FLOOR  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "ch4_uf" / "ch2_book_simulation_20260919.json"

CAPITAL = 100_000.0
SLICE = 2_500.0
MAX_PER_STOCK = {"one_per_stock": 1, "repeats_3": 3}
COSTS_BPS = [0.0, 10.0]
NULL_SEEDS = 50
SPLIT = np.datetime64("2024-03-15", "D")


def simulate_book(day_signals, bars, calendar, max_per_stock, cost_bps,
                  start, end, rng=None, random_pool=None):
    """Run the book across `calendar`. Returns a result dict."""
    cash = CAPITAL
    open_pos = []           # dicts
    per_stock = defaultdict(int)
    closed = []
    equity_curve = []
    cost = cost_bps / 10_000.0

    for day in calendar:
        if day < start or day > end:
            continue
        # 1. exits first, on today's close
        still = []
        for p in open_pos:
            d, close, _ = bars[p["ticker"]]
            k = np.searchsorted(d, day, side="left")
            if k >= len(d) or d[k] != day:
                still.append(p); continue
            px = close[k]
            p["peak"] = max(p["peak"], px)
            reason = None
            if px <= p["brake_line"]:
                reason, fill = "brake", px
            elif p["peak"] >= p["entry"] * (1 + RATCHET_ENGAGE) and \
                    px <= p["entry"] + (p["peak"] - p["entry"]) * (1 - RATCHET_GIVEBACK):
                reason, fill = "ratchet", px
            else:
                p["below"] = p["below"] + 1 if px <= p["damage_line"] else 0
                if p["below"] > DEAD_SESSIONS:
                    reason, fill = "dead_clock", px
                elif (day - p["entry_date"]).astype("timedelta64[D]").astype(int) >= WALL_DAYS:
                    reason, fill = "wall", px
            if reason:
                proceeds = p["shares"] * fill * (1 - cost)
                cash += proceeds
                per_stock[p["ticker"]] -= 1
                closed.append({"ticker": p["ticker"], "entry_date": str(p["entry_date"]),
                               "exit_date": str(day), "reason": reason,
                               "pnl": proceeds - p["cost_basis"],
                               "ret": (fill / p["entry"]) - 1.0})
            else:
                still.append(p)
        open_pos = still

        # 2. entries
        todays = day_signals.get(day, [])
        if random_pool is not None:
            pool = random_pool.get(day, [])
            n = len(todays)
            todays = [(t, 0.0) for t in rng.choice(pool, size=min(n, len(pool)), replace=False)] if (n and len(pool)) else []
        for ticker, _basin in todays:
            if per_stock[ticker] >= max_per_stock:
                continue
            d, close, ok = bars[ticker]
            k = np.searchsorted(d, day, side="left")
            if k >= len(d) or d[k] != day or not ok[k]:
                continue
            px = close[k]
            shares = int(SLICE // px)
            if shares <= 0:
                continue
            spend = shares * px * (1 + cost)
            if spend > cash:
                continue
            cash -= spend
            per_stock[ticker] += 1
            open_pos.append({"ticker": ticker, "entry": px, "entry_date": day, "shares": shares,
                             "cost_basis": spend, "peak": px, "below": 0,
                             "damage_line": px * (1 - DEAD_DAMAGE_PCT),
                             "brake_line": px * (1 - BRAKE_PCT)})

        # 3. mark
        mv = 0.0
        for p in open_pos:
            d, close, _ = bars[p["ticker"]]
            k = np.searchsorted(d, day, side="right") - 1
            if 0 <= k < len(close):
                mv += p["shares"] * close[k]
        equity_curve.append(cash + mv)

    eq = np.array(equity_curve) if equity_curve else np.array([CAPITAL])
    peak = np.maximum.accumulate(eq)
    dd = float(((eq - peak) / peak).min() * 100)
    rets = np.array([c["ret"] for c in closed]) if closed else np.array([])
    reasons = defaultdict(int)
    for c in closed:
        reasons[c["reason"]] += 1
    return {"final_equity": float(eq[-1]), "return_pct": float((eq[-1] / CAPITAL - 1) * 100),
            "max_drawdown_pct": dd, "positions_taken": len(closed) + len(open_pos),
            "positions_closed": len(closed), "still_open": len(open_pos),
            "win_rate_pct": float((rets > 0).mean() * 100) if len(rets) else None,
            "mean_trade_pct": float(rets.mean() * 100) if len(rets) else None,
            "exit_reasons": dict(reasons)}


def main() -> int:
    lanes = pd.read_csv(sys.argv[1], parse_dates=["d"])
    lanes = lanes.dropna(subset=["s_uf", "r_uf", "d_k", "m_k", "r_rev_k", "u_star_k", "c_k", "p_k", "b_k"])
    lanes = lanes.sort_values(["ticker", "d"]).reset_index(drop=True)
    port = verify_vectorised(lanes)
    print(f"[book] port check {port}", flush=True)
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

    # signals keyed by the session they would fill on
    day_signals: dict[np.datetime64, list] = defaultdict(list)
    sig = lanes[lanes.entry_ok]
    for ticker, gl in sig.groupby("ticker", sort=False):
        grp = bars.get(ticker)
        if grp is None:
            continue
        d, close, ok = grp
        j = np.searchsorted(d, gl.d.values.astype("datetime64[D]"), side="right")
        for jj, acc in zip(j, gl.acc.values):
            if jj < len(d) and ok[jj] and lo <= d[jj] <= hi:
                day_signals[d[jj]].append((ticker, float(acc)))
    for day in day_signals:
        day_signals[day].sort(key=lambda x: -x[1])
    calendar = np.array(sorted(day_signals.keys()))
    print(f"[book] signal days={len(calendar)} signals={sum(len(v) for v in day_signals.values())}", flush=True)

    # eligible pool per day for the null
    pool: dict[np.datetime64, list] = {}
    for day in calendar:
        names = [t for t, (d, c, ok) in bars.items()
                 if (k := int(np.searchsorted(d, day, side="left"))) < len(d) and d[k] == day and ok[k]]
        pool[day] = names
    print(f"[book] null pool built (median {int(np.median([len(v) for v in pool.values()]))} names/day)", flush=True)

    windows = {"full": (lo, hi), "first_half": (lo, SPLIT), "second_half": (SPLIT, hi)}
    out = {"declaration": "docs/CH2_BOOK_SIMULATION_DECLARATION_20260919.md",
           "generated_at_utc": pd.Timestamp.utcnow().isoformat(), "port_check": port,
           "capital": CAPITAL, "slice": SLICE, "windows": {}}

    for wname, (ws, we) in windows.items():
        w = {}
        for cost in COSTS_BPS:
            c = {}
            for run, cap in MAX_PER_STOCK.items():
                r = simulate_book(day_signals, bars, calendar, cap, cost, ws, we)
                c[run] = r
                print(f"[book] {wname:12s} cost={cost:4.1f}bp {run:14s} "
                      f"equity=${r['final_equity']:,.0f} ret={r['return_pct']:+.1f}% "
                      f"dd={r['max_drawdown_pct']:.1f}% trades={r['positions_taken']} "
                      f"win={r['win_rate_pct'] if r['win_rate_pct'] is None else round(r['win_rate_pct'],1)}%", flush=True)
            # null: random-entry book at the live cap
            nulls = []
            for seed in range(NULL_SEEDS):
                rng = np.random.default_rng(4242 + seed)
                nulls.append(simulate_book(day_signals, bars, calendar, 1, cost, ws, we,
                                           rng=rng, random_pool=pool)["return_pct"])
            nm = np.array(nulls)
            c["random_entry_null"] = {"seeds": NULL_SEEDS, "mean_return_pct": float(nm.mean()),
                                      "p05": float(np.percentile(nm, 5)), "p95": float(np.percentile(nm, 95))}
            print(f"[book] {wname:12s} cost={cost:4.1f}bp null mean={nm.mean():+.1f}% "
                  f"p95={np.percentile(nm, 95):+.1f}%", flush=True)
            w[f"cost_{int(cost)}bp"] = c
        out["windows"][wname] = w

    def passes():
        for wname in windows:
            for cost in COSTS_BPS:
                c = out["windows"][wname][f"cost_{int(cost)}bp"]
                if c["repeats_3"]["return_pct"] <= c["one_per_stock"]["return_pct"]:
                    return False
                if c["repeats_3"]["return_pct"] <= c["random_entry_null"]["p95"]:
                    return False
                if c["one_per_stock"]["return_pct"] <= c["random_entry_null"]["p95"]:
                    return False
        return True

    out["repeats_3_passes_declared_bar"] = passes()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, default=str))
    print(f"[book] repeats_3 passes declared bar: {out['repeats_3_passes_declared_bar']}", flush=True)
    print(f"[book] written {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
