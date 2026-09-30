"""CH2 herd census — the individual read against its herd. Declared 2026-09-30
before running.

Joe (2026-09-30): "that works for the individual ticker — but about the
herd — look at similar groups of stocks." Joe (2026-07-30): "the herd = the
stock's peer cohort — same type and pedigree — NOT the whole market."

FIELD: the raw bar (O, H, L, C, V). KERNEL: the canon kernel, causal pass.

HERD (kernel-native, causal, no hand labels; the July pedigree on the full
bar): on each day every eligible name sits in a cell (sigma-class,
attention-class, price-class), each class the {lo, mid, hi} band of,
respectively, the kernel's own L0 dispersion sigma(t) of the bar, the
trailing-20-day median volume, and the close — bands at the 25/75
quantiles of that DAY's cross-section. 27 cells. Membership drifts.

RESOLUTION FROM THE HERD (HIS: per group by size and price; MINE: the
setting): a name's boundary threshold on day t is c x the median of D(t)
over its cell's members that day (c = 3.77). A boundary is a day unusual
for THAT KIND of stock, not for the market and not only for itself.

HERD WEATHER, per cell per day (counts, not averages of tuples):
  deviating  = share of members whose D(t) crossed their threshold
  rising     = share of members whose close rose on the day
each banded lo/mid/hi against the cell's own trailing 20 days (25/75).

INDIVIDUAL READING: R_k of the standing gate at the herd resolution;
ACTIVE = R_k at or above the 80th percentile of the seen half (fixed).

TABLES (a count): 20-session up share and mean return by (individual
ACTIVE or not) x (herd deviating band) x (herd rising band), both halves,
tradeable days only (tools/ch2_canon_census.py filters). Also the herd
weather alone. RISE/FALL definitions as before.
OUTPUT: artifacts/ch4_uf/ch2_herd_census.json
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
C = 3.77
START = pd.Timestamp("2021-01-01")
CONFIRM = pd.Timestamp("2024-01-01")
HOLD = 20
OUT = ROOT / "artifacts" / "ch4_uf" / "ch2_herd_census.json"
_TAU = {}   # symbol -> per-bar threshold array, set in the pool initializer


def l0_vectorized(g: pd.DataFrame, cols=("Open", "High", "Low", "Close", "Volume")):
    """The canon L0 on the bar, vectorized: ||dF||, sigma = sum of per-column population variances
    over the trailing W bars, kappa = ||F(t+1) - 2F(t) + F(t-1)||, D = ||dF|| + sigma + kappa."""
    F = g[list(cols)].astype(float)
    dF = F.diff().fillna(0.0)
    ndF = np.sqrt((dF ** 2).sum(axis=1)).values
    sigma = F.rolling(W, min_periods=1).var(ddof=0).sum(axis=1).values
    kap = np.zeros(len(F)); Fv = F.values
    kap[1:-1] = np.linalg.norm(Fv[2:] - 2 * Fv[1:-1] + Fv[:-2], axis=1)
    return ndF, sigma, kap, ndF + sigma + kap


def band3(x: pd.DataFrame) -> pd.DataFrame:
    """Row-wise {0,1,2} band at that row's 25/75 quantiles (cross-section on the day)."""
    q1 = x.quantile(0.25, axis=1); q3 = x.quantile(0.75, axis=1)
    return (x.gt(q1, axis=0).astype(int) + x.gt(q3, axis=0).astype(int)).where(x.notna())


def trailing_band3(x: pd.DataFrame) -> pd.DataFrame:
    """Column-wise band of today's value against the column's own trailing W days (shifted)."""
    prev = x.shift(1)
    q1 = prev.rolling(W, min_periods=10).quantile(0.25); q3 = prev.rolling(W, min_periods=10).quantile(0.75)
    return (x.gt(q1).astype(int) + x.gt(q3).astype(int)).where(x.notna() & q1.notna())


def herd_state(bars: pd.DataFrame, c: float = C, cols=("Open", "High", "Low", "Close", "Volume")):
    """Herd cells, the herd resolution (tau per name per day) and the herd weather, all causal.
    Returns (tau: DataFrame dates x symbols, cs: Date/Symbol/cell, weather: Date/cell/dev_band/ris_band)."""
    t0 = time.time()
    symbols = sorted(bars.Symbol.unique())
    # ---- L0 for every name, then the cross-section matrices (dates x symbols) ----
    parts = []
    for sym, g in bars.groupby("Symbol", sort=False):
        ndF, sigma, kap, D = l0_vectorized(g, cols)
        parts.append(pd.DataFrame({"Symbol": sym, "Date": g.Date.values, "sigma": sigma, "D": D,
                                   "vol20": g.Volume.rolling(W, min_periods=W).median().values, "close": g.Close.values}))
    l0 = pd.concat(parts, ignore_index=True); del parts
    piv = {c: l0.pivot(index="Date", columns="Symbol", values=c) for c in ("sigma", "D", "vol20", "close")}
    print(f"[herd] L0 + pivots: {len(symbols)} names x {len(piv['D'])} days, {time.time() - t0:.0f}s", flush=True)
    # ---- herd cells: (sigma-class, attention-class, price-class) from the day's cross-section ----
    elig = piv["close"].notna() & piv["vol20"].notna() & (piv["close"] >= 5.0)
    cell = (band3(piv["sigma"].where(elig)) * 9 + band3(piv["vol20"].where(elig)) * 3 + band3(piv["close"].where(elig)))
    # ---- resolution from the herd: tau = C x the cell's median D that day ----
    Dm = piv["D"].where(elig)
    tau = pd.DataFrame(np.nan, index=Dm.index, columns=Dm.columns)
    stacked = pd.DataFrame({"D": Dm.stack(), "cell": cell.stack()})
    med = stacked.groupby([stacked.index.get_level_values(0), "cell"]).D.median()
    med.index.names = ["Date", "cell"]
    cs = cell.stack().rename("cell").reset_index(); cs.columns = ["Date", "Symbol", "cell"]
    cs = cs.merge(med.rename("medD").reset_index(), on=["Date", "cell"], how="left")
    tau = cs.pivot(index="Date", columns="Symbol", values="medD") * c
    tau = tau.reindex(index=Dm.index, columns=Dm.columns)
    # ---- herd weather: deviating share and rising share per cell per day, banded vs the cell's trailing 20 days ----
    crossed = (piv["D"] >= tau).where(elig)
    rose = (piv["close"].diff() > 0).where(elig)
    wx = pd.DataFrame({"cell": cell.stack(), "crossed": crossed.stack().astype(float), "rose": rose.stack().astype(float)})
    wx.index.names = ["Date", "Symbol"]
    wcell = wx.groupby(["Date", "cell"]).agg(deviating=("crossed", "mean"), rising=("rose", "mean"), members=("crossed", "size"))
    dev_p = wcell.deviating.unstack("cell"); ris_p = wcell.rising.unstack("cell")
    dev_b = trailing_band3(dev_p).stack().rename("dev_band"); ris_b = trailing_band3(ris_p).stack().rename("ris_band")
    weather = pd.concat([dev_b, ris_b], axis=1).reset_index(); weather.columns = ["Date", "cell", "dev_band", "ris_band"]
    print(f"[herd] cells, herd resolution, weather done, {time.time() - t0:.0f}s; cells occupied per day median {cell.notna().sum(axis=1).median():.0f} names", flush=True)
    return tau, cs, weather


def _init(tau_map):
    global _TAU
    _TAU = tau_map


def one(task):
    from canon_kernel_causal import readings
    from ch2_canon_census import tradeable_flags
    symbol, df = task
    df = df.sort_values("Date").reset_index(drop=True)
    F = df[["Open", "High", "Low", "Close", "Volume"]].values.astype(float)
    close = df.Close.values.astype(float); n = len(close)
    tau = _TAU[symbol]
    r = readings(F, tau_D=tau)
    s = pd.Series(np.nan, index=np.arange(n)); s.iloc[r.t.values] = r.R_k.values
    out = pd.DataFrame({"symbol": symbol, "date": df.Date.values, "close": close, "R_k": s.ffill().values.astype("float32"),
                        "boundary": np.isin(np.arange(n), r.t.values)})
    out["tradeable"] = tradeable_flags(df).tradeable.values
    fwd = np.full(n, np.nan); fwd[: n - HOLD] = close[HOLD:] / close[: n - HOLD] - 1.0
    out["r20"] = fwd.astype("float32")
    return out[out.date >= START]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--every", type=int, default=1)
    a = ap.parse_args()
    t0 = time.time()
    bars = pd.read_parquet(ROOT / "artifacts" / "ch2_life" / "ohlcv_pool.parquet")
    symbols = sorted(bars.Symbol.unique())[:: a.every]
    bars = bars[bars.Symbol.isin(symbols)].sort_values(["Symbol", "Date"]).reset_index(drop=True)
    tau, cs, weather = herd_state(bars)
    # ---- per-name readings at the herd resolution ----
    tau_map = {s: tau[s].reindex(g.Date.values).values for s, g in bars.groupby("Symbol", sort=False)}
    tasks = [(s, g) for s, g in bars.groupby("Symbol", sort=False)]
    del bars
    parts = []
    with Pool(a.workers, initializer=_init, initargs=(tau_map,)) as pool:
        for i, r in enumerate(pool.imap_unordered(one, tasks, chunksize=4), 1):
            parts.append(r)
            if i % 500 == 0:
                print(f"[herd] readings {i}/{len(tasks)} {time.time() - t0:.0f}s", flush=True)
    ev = pd.concat(parts, ignore_index=True); del parts
    ev = ev.merge(cs[["Date", "Symbol", "cell"]].rename(columns={"Date": "date", "Symbol": "symbol"}), on=["date", "symbol"], how="left")
    ev = ev.merge(weather.rename(columns={"Date": "date"}), on=["date", "cell"], how="left")
    ev = ev[ev.tradeable & ev.cell.notna() & ev.dev_band.notna()].reset_index(drop=True)
    ev["half"] = np.where(ev.date < CONFIRM, "seen", "confirm")
    thr = float(np.nanpercentile(ev.loc[ev.half == "seen", "R_k"], 80))
    ev["active"] = (ev.R_k >= thr).astype(int)
    print(f"[herd] tradeable stock-days with a herd and weather: {len(ev)}; ACTIVE threshold R_k >= {thr:.4f}; boundaries per name-year: {ev.boundary.mean() * 252:.1f}", flush=True)
    res = {"declared": "herd, resolution, weather, reading, tables in the docstring before results", "symbols": len(symbols),
           "days": int(len(ev)), "active_threshold": thr, "boundaries_per_name_year": float(ev.boundary.mean() * 252), "tables": {}}
    pd.set_option("display.width", 220); pd.set_option("display.max_rows", 200)

    def tab(name, keys):
        res["tables"][name] = {}
        for half in ("seen", "confirm"):
            h = ev[ev.half == half]
            g = h.groupby(keys, observed=True)
            t = pd.DataFrame({"n": g.size(), "up20": g.r20.apply(lambda s: float((s.dropna() > 0).mean())), "mean_r20%": g.r20.mean() * 100,
                              "rise_share": g.r20.apply(lambda s: float((s.dropna() >= 0.08).mean())), "fall_share": g.r20.apply(lambda s: float((s.dropna() <= -0.08).mean()))})
            res["tables"][name][half] = {(" | ".join(map(str, k)) if isinstance(k, tuple) else str(k)): {c: round(float(v), 4) for c, v in row.items()} for k, row in t.iterrows()}
            print(f"\n== {name} [{half}]"); print(t.round(4).to_string())

    tab("all", ["tradeable"])
    tab("individual ACTIVE", ["active"])
    tab("herd deviating band", ["dev_band"])
    tab("herd rising band", ["ris_band"])
    tab("herd deviating x rising", ["dev_band", "ris_band"])
    tab("individual ACTIVE x herd deviating", ["active", "dev_band"])
    tab("individual ACTIVE x herd rising", ["active", "ris_band"])
    tab("individual ACTIVE x herd deviating x rising", ["active", "dev_band", "ris_band"])
    tab("boundary today x herd deviating", ["boundary", "dev_band"])
    json.dump(res, open(OUT, "w"), indent=1)
    print("filed:", OUT)


if __name__ == "__main__":
    main()
