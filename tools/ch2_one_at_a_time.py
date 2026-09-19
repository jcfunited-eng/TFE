"""Does "one position per stock at a time" cost the book? — the measurement
declared in docs/CH2_ONE_AT_A_TIME_DECLARATION_20260919.md.

Three runs on identical entries and identical fixed holds: every signal, the
live first-of-cluster rule, and the same count chosen at random within each
cluster. No adaptive exits, so only the choice of entries differs.

Usage:
  PYTHONHASHSEED=0 python tools/ch2_one_at_a_time.py \
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
OUT = ROOT / "artifacts" / "ch4_uf" / "ch2_one_at_a_time_20260919.json"

HORIZONS = [30, 60]
SEEDS = 200
SPLIT = np.datetime64("2024-03-15", "D")


def stats(rets, dates=None, mask=None):
    r = rets if mask is None else rets[mask]
    if not len(r):
        return {"positions": 0}
    return {"positions": int(len(r)), "mean_pct": float(r.mean() * 100),
            "median_pct": float(np.median(r) * 100),
            "win_rate_pct": float((r > 0).mean() * 100),
            "total_pct": float(r.sum() * 100)}


def first_of_cluster(js: np.ndarray, horizon: int) -> np.ndarray:
    """The live rule: take a signal, skip every signal until the hold is over."""
    out = []
    block_until = -1
    for j in js:
        if j <= block_until:
            continue
        out.append(j)
        block_until = j + horizon
    return np.array(out, dtype=int)


def random_of_cluster(js: np.ndarray, horizon: int, n_wanted: int, rng) -> np.ndarray:
    """n_wanted signals from the same list, no two overlapping, chosen at random."""
    pool = list(js)
    rng.shuffle(pool)
    chosen: list[int] = []
    for j in pool:
        if len(chosen) >= n_wanted:
            break
        if all(abs(j - c) > horizon for c in chosen):
            chosen.append(int(j))
    return np.array(sorted(chosen), dtype=int)


def main() -> int:
    lanes = pd.read_csv(sys.argv[1], parse_dates=["d"])
    lanes = lanes.dropna(subset=["s_uf", "r_uf", "d_k", "m_k", "r_rev_k", "u_star_k", "c_k", "p_k", "b_k"])
    lanes = lanes.sort_values(["ticker", "d"]).reset_index(drop=True)
    port = verify_vectorised(lanes)
    print(f"[oaat] port check {port}", flush=True)
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

    signals: dict[str, np.ndarray] = {}
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
        j = np.unique(j[ok[j]])
        if len(j):
            signals[ticker] = j
    print(f"[oaat] tickers={len(signals)} signals={sum(len(v) for v in signals.values())}", flush=True)

    def outcomes(idx_map, horizon):
        rets, dts = [], []
        for ticker, js in idx_map.items():
            d, close, _ = groups[ticker]
            js = js[js + horizon < len(close)]
            if not len(js):
                continue
            rets.append(close[js + horizon] / close[js] - 1.0)
            dts.append(d[js])
        if not rets:
            return np.array([]), np.array([], dtype="datetime64[D]")
        return np.concatenate(rets), np.concatenate(dts)

    out = {"declaration": "docs/CH2_ONE_AT_A_TIME_DECLARATION_20260919.md",
           "generated_at_utc": pd.Timestamp.utcnow().isoformat(),
           "port_check": port, "horizons": {}, "costs_modeled": False,
           "prices": "closes only"}

    for horizon in HORIZONS:
        all_ret, all_dt = outcomes(signals, horizon)
        first_map = {t: first_of_cluster(js, horizon) for t, js in signals.items()}
        first_ret, first_dt = outcomes(first_map, horizon)
        wanted = {t: len(v) for t, v in first_map.items()}

        means, means_h1, means_h2, counts = [], [], [], []
        for seed in range(SEEDS):
            rng = np.random.default_rng(77000 + seed * 11 + horizon)
            rmap = {t: random_of_cluster(js, horizon, wanted.get(t, 0), rng)
                    for t, js in signals.items() if wanted.get(t, 0)}
            r, dt = outcomes(rmap, horizon)
            if not len(r):
                continue
            means.append(float(r.mean() * 100)); counts.append(int(len(r)))
            if (dt < SPLIT).any():
                means_h1.append(float(r[dt < SPLIT].mean() * 100))
            if (dt >= SPLIT).any():
                means_h2.append(float(r[dt >= SPLIT].mean() * 100))
        nm = np.array(means)

        h = {
            "all_signals": {"all": stats(all_ret), "first_half": stats(all_ret, mask=all_dt < SPLIT),
                            "second_half": stats(all_ret, mask=all_dt >= SPLIT)},
            "first_of_cluster": {"all": stats(first_ret), "first_half": stats(first_ret, mask=first_dt < SPLIT),
                                 "second_half": stats(first_ret, mask=first_dt >= SPLIT)},
            "random_of_cluster": {"seeds": len(means), "mean_positions": float(np.mean(counts)),
                                  "mean_pct": float(nm.mean()), "p05": float(np.percentile(nm, 5)),
                                  "p95": float(np.percentile(nm, 95)),
                                  "h1_mean_pct": float(np.mean(means_h1)) if means_h1 else None,
                                  "h1_p05": float(np.percentile(means_h1, 5)) if means_h1 else None,
                                  "h2_mean_pct": float(np.mean(means_h2)) if means_h2 else None,
                                  "h2_p05": float(np.percentile(means_h2, 5)) if means_h2 else None},
        }
        h["first_is_worse_than_random_within_cluster"] = bool(
            first_ret.mean() * 100 < np.percentile(nm, 5))
        h["fewer_positions_explains_gap"] = bool(
            abs(first_ret.mean() * 100 - nm.mean()) < (np.percentile(nm, 95) - np.percentile(nm, 5)) / 2)
        out["horizons"][str(horizon)] = h
        print(f"[oaat] horizon={horizon}: all n={h['all_signals']['all']['positions']} "
              f"mean={h['all_signals']['all']['mean_pct']:+.2f}% | "
              f"first n={h['first_of_cluster']['all']['positions']} "
              f"mean={h['first_of_cluster']['all']['mean_pct']:+.2f}% | "
              f"random_within n={h['random_of_cluster']['mean_positions']:.0f} "
              f"mean={h['random_of_cluster']['mean_pct']:+.2f}% "
              f"p05={h['random_of_cluster']['p05']:+.2f}% p95={h['random_of_cluster']['p95']:+.2f}% | "
              f"first_worse={h['first_is_worse_than_random_within_cluster']}", flush=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, default=str))
    print(f"[oaat] written {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
