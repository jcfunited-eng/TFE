"""The capacitor law, tested as physics then as finance. Declared before running.

Joe's exhaustion paper: quiescence stores energy (E_p ∝ tau_in), a shock
ignites it, the release lasts tau_out = floor(tau_in / 3).

GATES: the canon kernel on the raw bar at HERD resolution (a boundary is a
bar > 3.77x the median bar of the stock's own cell that day). Two fields,
both reported: (A) O,H,L,C,V in the norm; (B) O,H,L,C in the norm, volume
as relevance. Tradeable days only (ch2_canon_census filters at entry).

For every boundary bar t_b ending a gate of length tau_in >= 2:
  shock size       |close[t_b] / close[t_b-1] - 1|          (the boundary bar's own move)
  shock direction  sign of that move
  entry            close[t_b + 1]  (the boundary is knowable at that close)
  tau_out          max(1, tau_in // 3)
  release          direction x (close[t_b + 1 + tau_out] / close[t_b + 1] - 1)

PHYSICS: shock size by tau_in band (2-5, 6-10, 11-20, 21-40, 41+): quartiles.
FINANCE: share of releases > 0 and their mean, by tau_in band; and PER YEAR
for the long-quiet bands (Joe's standard). Null: the same horizon from a
random day = the base up-rate over tau_out bars (direction-blind); reported
as the share > 0 of direction x move for ALL days with a random sign, i.e.
0.5, and the plain up-share for reference.
OUTPUT: artifacts/ch4_uf/ch2_capacitor_test.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
W = 20
BANDS = [(2, 5), (6, 10), (11, 20), (21, 40), (41, 10 ** 6)]
FIELDS = {"A_bar_in_norm": ("Open", "High", "Low", "Close", "Volume"), "B_volume_as_relevance": ("Open", "High", "Low", "Close")}
OUT = ROOT / "artifacts" / "ch4_uf" / "ch2_capacitor_test.json"
_TAU, _FIELD = {}, "A_bar_in_norm"


def _init(tau_map, field):
    global _TAU, _FIELD
    _TAU, _FIELD = tau_map, field


def one(task):
    from canon_kernel_causal import readings
    from ch2_canon_census import tradeable_flags
    symbol, df = task
    df = df.sort_values("Date").reset_index(drop=True)
    F = df[list(FIELDS[_FIELD])].values.astype(float)
    close = df.Close.values.astype(float); n = len(close)
    rel = None
    if _FIELD == "B_volume_as_relevance":
        v = df.Volume.astype(float); med = v.rolling(W, min_periods=1).median()
        rel = np.where(med > 0, v / med.replace(0, np.nan), 1.0); rel = np.where(np.isfinite(rel), rel, 1.0)
    r = readings(F, tau_D=_TAU[symbol], r=rel)
    trad = tradeable_flags(df).tradeable.values
    rows = []
    for t_b, T in zip(r.t.values, r.T_k.values):
        t_b = int(t_b); tau_in = int(T)
        if tau_in < 2 or t_b < 1 or t_b + 1 >= n:
            continue
        shock = close[t_b] / close[t_b - 1] - 1.0
        s = 1 if shock > 0 else (-1 if shock < 0 else 0)
        if s == 0 or not trad[t_b + 1]:
            continue
        tau_out = max(1, tau_in // 3)
        e = t_b + 1
        if e + tau_out >= n:
            continue
        release = s * (close[e + tau_out] / close[e] - 1.0)
        rows.append((symbol, str(df.Date.values[e])[:10], tau_in, tau_out, abs(shock), s, release))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--every", type=int, default=1)
    a = ap.parse_args()
    from ch2_herd_census import herd_state
    bars_all = pd.read_parquet(ROOT / "artifacts" / "ch2_life" / "ohlcv_pool.parquet")
    symbols = sorted(bars_all.Symbol.unique())[:: a.every]
    bars_all = bars_all[bars_all.Symbol.isin(symbols)].sort_values(["Symbol", "Date"]).reset_index(drop=True)
    res = {"declared": "law, gates, entry, horizon, tables in the docstring before results", "fields": {}}
    pd.set_option("display.width", 200)
    for field, cols in FIELDS.items():
        t0 = time.time()
        tau, cs, weather = herd_state(bars_all, cols=cols)
        tau_map = {s: tau[s].reindex(g.Date.values).values for s, g in bars_all.groupby("Symbol", sort=False)}
        tasks = [(s, g) for s, g in bars_all.groupby("Symbol", sort=False)]
        rows = []
        with Pool(a.workers, initializer=_init, initargs=(tau_map, field)) as pool:
            for r in pool.imap_unordered(one, tasks, chunksize=4):
                rows.extend(r)
        ev = pd.DataFrame(rows, columns=["symbol", "date", "tau_in", "tau_out", "shock", "dir", "release"])
        ev = ev[ev.date >= "2017-01-01"]
        ev["band"] = pd.cut(ev.tau_in, [1] + [b[1] for b in BANDS], labels=[f"{lo}-{hi if hi < 10**6 else '+'}" for lo, hi in BANDS])
        ev["year"] = ev.date.str[:4]
        print(f"\n===== {field}: {len(ev)} shocks ending gates of >= 2 bars, {time.time() - t0:.0f}s")
        g = ev.groupby("band", observed=True)
        phys = pd.DataFrame({"n": g.size(), "shock_q25%": g.shock.quantile(.25) * 100, "shock_median%": g.shock.median() * 100, "shock_q75%": g.shock.quantile(.75) * 100,
                             "tau_out_median": g.tau_out.median()})
        fin = pd.DataFrame({"n": g.size(), "release>0": g.release.apply(lambda s: float((s > 0).mean())), "mean_release%": g.release.mean() * 100,
                            "median_release%": g.release.median() * 100, "up_shocks_share": g["dir"].apply(lambda s: float((s > 0).mean()))})
        print("PHYSICS — shock size on the boundary bar, by length of the quiet before it:"); print(phys.round(3).to_string())
        print("FINANCE — continuation in the shock's direction over tau_in//3 bars:"); print(fin.round(4).to_string())
        # direction split and per-year for the long bands
        split = ev.groupby(["band", "dir"], observed=True).release.agg(n="size", cont=lambda s: float((s > 0).mean()), mean_pct=lambda s: float(s.mean() * 100))
        print("by shock direction (+1 up shock, -1 down shock):"); print(split.round(4).to_string())
        long = ev[ev.tau_in >= 21]
        py = long.groupby("year").release.agg(n="size", cont=lambda s: float((s > 0).mean()), mean_pct=lambda s: float(s.mean() * 100))
        print("PER YEAR, quiet >= 21 bars:"); print(py.round(4).to_string())
        res["fields"][field] = {"shocks": int(len(ev)),
                                "physics": {str(k): {c: round(float(v), 4) for c, v in row.items()} for k, row in phys.iterrows()},
                                "finance": {str(k): {c: round(float(v), 4) for c, v in row.items()} for k, row in fin.iterrows()},
                                "by_direction": {" | ".join(map(str, k)): {c: round(float(v), 4) for c, v in row.items()} for k, row in split.iterrows()},
                                "per_year_quiet_ge_21": {str(k): {c: round(float(v), 4) for c, v in row.items()} for k, row in py.iterrows()}}
    json.dump(res, open(OUT, "w"), indent=1)
    print("filed:", OUT)


if __name__ == "__main__":
    main()
