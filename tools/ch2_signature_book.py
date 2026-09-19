"""The living-drive signature at book level — declared in the result section of
docs/CH2_LIVING_DRIVE_SIGNATURE_DECLARATION_20260919.md.

The same capacity-bounded book that killed the flattened gate: $100,000,
$2,500 slices, whole shares, cash-limited, day by day. Entries are the
signature instead of the gate. Two exit settings (the live law, and a flat
30-session hold), both cost settings, both halves, against a random-entry book
drawn from the same eligible pool and against SPY held.

Priority when cash is short: fewest signature names first is meaningless, so
entries are taken in the order the day lists them after a deterministic shuffle
seeded per day — no ranking, because the gate's own ranking was shown to carry
no information.

Usage:
  PYTHONHASHSEED=0 python tools/ch2_signature_book.py \
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
from ch2_winner_exit_measure import verify_vectorised  # noqa: E402
from ch2_holding_length_measure import LIQ_FLOOR_USD, LIQ_WINDOW, PRICE_FLOOR  # noqa: E402
from ch2_book_simulation import CAPITAL, COSTS_BPS, SPLIT, simulate_book  # noqa: E402
from ch2_living_drive_signature import (  # noqa: E402
    W, LAG, RUPTURE_MAX, IGNITION_MIN, ZOMBIE_BARS, PUMP_RISE,
)


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "ch4_uf" / "ch2_signature_book_20260919.json"
SEEDS = 50


def main() -> int:
    lanes = pd.read_csv(sys.argv[1], parse_dates=["d"])
    lanes = lanes.dropna(subset=["s_uf", "r_uf", "d_k", "m_k", "r_rev_k", "u_star_k", "c_k", "p_k", "b_k"])
    lanes = lanes.sort_values(["ticker", "d"]).reset_index(drop=True)
    port = verify_vectorised(lanes)
    print(f"[sigbook] port check {port}", flush=True)
    if port["decision_mismatches"]:
        return 1

    g = lanes.groupby("ticker", sort=False)
    suf_med = g.s_uf.transform(lambda x: x.rolling(W, min_periods=W).median())
    ruf_med = g.r_uf.transform(lambda x: x.rolling(W, min_periods=W).median())
    b_prev = g.b_k.shift(LAG)
    rupture = (-np.maximum(lanes.s_uf - lanes.u_star_k, lanes.r_uf - lanes.u_star_k)).clip(lower=0)
    lanes["rupture"] = rupture
    rupture_days = g.rupture.transform(lambda x: (x > 0).rolling(W, min_periods=W).sum())
    lanes["_ign"] = (lanes.d_k == 1).astype(int)
    ign_days = g._ign.transform(lambda x: x.rolling(W, min_periods=W).sum())
    lanes["signature"] = ((lanes.s_uf >= suf_med) & (lanes.r_uf >= ruf_med)
                          & (lanes.b_k >= b_prev) & (rupture <= 0) & (rupture_days <= RUPTURE_MAX)
                          & (lanes.d_k == 1) & (ign_days >= IGNITION_MIN)).fillna(False)
    lanes["not_zombie"] = lanes.bar_count.fillna(0) >= ZOMBIE_BARS
    print(f"[sigbook] signature rate {lanes.signature.mean()*100:.2f}%", flush=True)

    bars_df = pd.read_parquet(sys.argv[2], columns=["Date", "Symbol", "Close", "Volume"]).dropna()
    bars_df = bars_df.sort_values(["Symbol", "Date"])
    lo = lanes.d.min().to_datetime64().astype("datetime64[D]")
    hi = lanes.d.max().to_datetime64().astype("datetime64[D]")
    bars = {}
    for sym, gg in bars_df.groupby("Symbol", sort=False):
        close = gg.Close.values.astype(float)
        d = gg.Date.values.astype("datetime64[D]")
        liq = pd.Series(close * gg.Volume.values.astype(float)).rolling(
            LIQ_WINDOW, min_periods=LIQ_WINDOW).median().values
        ok = np.nan_to_num((liq >= LIQ_FLOOR_USD), nan=0).astype(bool) & (close >= PRICE_FLOOR)
        pump = pd.Series(close).pct_change(W).values
        bars[sym] = (d, close, ok & ~np.nan_to_num(pump > PUMP_RISE, nan=False))

    day_signals: dict[np.datetime64, list] = defaultdict(list)
    eligible_pool: dict[np.datetime64, list] = defaultdict(list)
    for ticker, gl in lanes.groupby("ticker", sort=False):
        grp = bars.get(ticker)
        if grp is None:
            continue
        d, close, ok = grp
        keep = gl.not_zombie.values
        dates = gl.d.values.astype("datetime64[D]")
        sigs = gl.signature.values
        j = np.searchsorted(d, dates, side="right")
        for k in np.flatnonzero(keep):
            jj = j[k]
            if jj < len(d) and ok[jj] and lo <= d[jj] <= hi:
                eligible_pool[d[jj]].append(ticker)
                if sigs[k]:
                    day_signals[d[jj]].append((ticker, 0.0))
    for day, lst in day_signals.items():
        rng = np.random.default_rng(abs(hash(str(day))) % (2**32))
        idx = rng.permutation(len(lst))
        day_signals[day] = [lst[i] for i in idx]
    calendar = np.array(sorted(day_signals.keys()))
    print(f"[sigbook] signal days={len(calendar)} signals={sum(len(v) for v in day_signals.values())} "
          f"median eligible/day={int(np.median([len(v) for v in eligible_pool.values()]))}", flush=True)

    def spy_hold(start, end):
        d, close, _ = bars.get("SPY", (None, None, None))
        if d is None:
            return {"note": "SPY missing"}
        m = (d >= start) & (d <= end); c = close[m]
        if len(c) < 2:
            return {"note": "insufficient"}
        sh = int(CAPITAL // c[0]); eq = sh * c + (CAPITAL - sh * c[0])
        peak = np.maximum.accumulate(eq)
        return {"return_pct": float((eq[-1] / CAPITAL - 1) * 100),
                "max_drawdown_pct": float(((eq - peak) / peak).min() * 100)}

    windows = {"full": (lo, hi), "first_half": (lo, SPLIT), "second_half": (SPLIT, hi)}
    out = {"source": "docs/CH2_LIVING_DRIVE_SIGNATURE_DECLARATION_20260919.md",
           "generated_at_utc": pd.Timestamp.utcnow().isoformat(), "port_check": port,
           "signature_rate_pct": float(lanes.signature.mean() * 100), "windows": {}}

    for wname, (ws, we) in windows.items():
        w = {"spy_hold": spy_hold(ws, we)}
        print(f"[sigbook] {wname}: SPY {w['spy_hold'].get('return_pct')}", flush=True)
        for cost in COSTS_BPS:
            c = {}
            # One run only: the live exit law. simulate_book carries no horizon
            # cap, so a "flat hold" variant would have been the same numbers
            # under a second name — removed rather than reported twice.
            r = simulate_book(day_signals, bars, calendar, 1, cost, ws, we)
            c["live_exits"] = r
            print(f"[sigbook] {wname:12s} {cost:4.1f}bp live_exits "
                  f"ret={r['return_pct']:+6.1f}% dd={r['max_drawdown_pct']:.1f}% "
                  f"trades={r['positions_taken']} win={r['win_rate_pct'] if r['win_rate_pct'] is None else round(r['win_rate_pct'],1)}%", flush=True)
            rets = []
            for seed in range(SEEDS):
                rng = np.random.default_rng(1500 + seed)
                rets.append(simulate_book(day_signals, bars, calendar, 1, cost, ws, we,
                                          rng=rng, random_pool=eligible_pool)["return_pct"])
            a = np.array(rets)
            c["random_entry_null"] = {"seeds": SEEDS, "mean_return_pct": float(a.mean()),
                                      "p05": float(np.percentile(a, 5)), "p95": float(np.percentile(a, 95))}
            c["beats_null"] = bool(c["live_exits"]["return_pct"] > c["random_entry_null"]["p95"])
            print(f"[sigbook] {wname:12s} {cost:4.1f}bp null mean={a.mean():+.1f}% "
                  f"p95={np.percentile(a, 95):+.1f}% beats={c['beats_null']}", flush=True)
            w[f"cost_{int(cost)}bp"] = c
        out["windows"][wname] = w

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, default=str))
    print(f"[sigbook] written {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
