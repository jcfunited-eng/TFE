"""The canon kernel's reading on every day of every tradable name, and what
the price did after. Declared 2026-09-30 before running.

Joe: the field is the whole bar; the kernel never averages over the
history; "what were the tuples at before rises and what were they at falls
— ALL of them"; "run what-if scenarios at your pleasure."

READING: tools/canon_kernel_causal.readings on the raw bar (Open, High,
Low, Close, Volume) — the reading on day t is the kernel run on the bars
through t (verified identical to the prefix loop). Every field kept:
D_k, M_k, R_rev_k, U*_k, C_k, P_k, B_k, R_k, URF_k, g_k, Hyst_k, w_k,
psi_k, S_k, U_k, IAS_k, regime.
UNIVERSE: the live CH2 entry pool with >= 1,000 bars (artifacts/ch2_life/
ohlcv_pool.parquet). Days from 2021-01-01. Halves: < 2024 (seen) / >= 2024.
OUTCOMES from close[t]: close[t+5] and close[t+20]. RISE: 20-day >= +8%;
FALL: <= -8%.
TABLES (a count, not a rule): for every field, its values on days before
RISE vs before FALL vs flat (min/25/50/75/max); for discrete fields the
share of 20-day rises by value; for continuous fields by pool quintile;
D_k x sign(M_k). Both halves. Field variants (--field): "bar" (O,H,L,C,V),
"ohlc" (no volume), "cv" (Close, Volume). Each variant is a what-if, MINE.
OUTPUT: artifacts/ch4_uf/ch2_canon_census_<field>.json (+ .parquet sample).
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

COLS = {"bar": ["Open", "High", "Low", "Close", "Volume"], "ohlc": ["Open", "High", "Low", "Close"], "cv": ["Close", "Volume"]}
DISCRETE = ["D_k", "R_rev_k", "C_k", "P_k", "g_k", "Hyst_k", "IAS_k", "regime"]
CONTINUOUS = ["M_k", "U_star_k", "B_k", "R_k", "URF_k", "w_k", "psi_k", "S_k", "U_k"]
START = pd.Timestamp("2021-01-01")
CONFIRM = pd.Timestamp("2024-01-01")
MOVE = 0.08
_FIELD = "bar"
_TAU = 0.20


def _init(field, tau):
    global _FIELD, _TAU
    _FIELD, _TAU = field, tau


def tradeable_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Causal per-day filters (MINE, 2026-09-30). Each flag on day t uses bars through t only."""
    close, vol, high, low = df.Close.astype(float), df.Volume.astype(float), df.High.astype(float), df.Low.astype(float)
    ret = close.pct_change().abs()
    dv20 = (close * vol).rolling(20, min_periods=20).median()
    zero60 = (vol <= 0).astype(int).rolling(60, min_periods=1).sum()
    hist = pd.Series(np.arange(len(df)), index=df.index)
    doubled20 = close.rolling(20, min_periods=20).max() / close.rolling(20, min_periods=20).min() > 2.0
    big60 = (ret > 0.30).astype(int).rolling(60, min_periods=1).sum() > 0
    spike = (vol > 8 * vol.rolling(60, min_periods=20).median()) & (ret > 0.15)
    spike_block = spike.astype(int).rolling(60, min_periods=1).sum() > 0
    rng60 = (high.rolling(60, min_periods=60).max() - low.rolling(60, min_periods=60).min()) / close
    out = pd.DataFrame({
        "f_bars": hist >= 252,
        "f_price": close >= 5.0,
        "f_dollar_vol": dv20 >= 2_000_000,
        "f_zero_vol": zero60 <= 3,
        "f_pump": ~(doubled20.fillna(False) | big60 | spike_block),
        "f_zombie": rng60 >= 0.05,
    })
    out["tradeable"] = out.all(axis=1)
    return out


def one(task):
    from canon_kernel_causal import readings
    symbol, df = task
    df = df.sort_values("Date").reset_index(drop=True)
    F = df[COLS[_FIELD]].values.astype(float)
    close = df.Close.values.astype(float)
    n = len(close)
    r = readings(F, tau_D=_TAU)
    t = r.t.values
    r["date"] = df.Date.values[t]
    r["close"] = close[t]
    flags = tradeable_flags(df).iloc[t].reset_index(drop=True)
    for c in flags.columns:
        r[c] = flags[c].values
    for h in (5, 20):
        fwd = np.full(len(t), np.nan)
        ok = t + h < n
        fwd[ok] = close[t[ok] + h] / close[t[ok]] - 1.0
        r[f"r{h}"] = fwd
    r = r[r.date >= START].drop(columns=["t", "T_k", "V_k", "delta_g"])
    r.insert(0, "symbol", symbol)
    for c in CONTINUOUS + ["r5", "r20", "close"]:
        r[c] = r[c].astype("float32")
    return r


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--field", choices=list(COLS), default="bar")
    ap.add_argument("--tau", default="0.20", help='0.20 (canon fixed) or "own" (per-ticker, trailing, MINE)')
    ap.add_argument("--filters", action="store_true", help="keep only tradeable stock-days (zombie / pump-and-dump / too few bars / non-tradeable filters, MINE)")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--every", type=int, default=1)
    a = ap.parse_args()
    tau = "own" if a.tau == "own" else float(a.tau)
    out = ROOT / "artifacts" / "ch4_uf" / f"ch2_canon_census_{a.field}_tau{a.tau.replace('.', 'p')}{'_filtered' if a.filters else ''}"
    bars = pd.read_parquet(ROOT / "artifacts" / "ch2_life" / "ohlcv_pool.parquet")
    symbols = sorted(bars.Symbol.unique())[:: a.every]
    tasks = [(s, g) for s, g in bars[bars.Symbol.isin(symbols)].groupby("Symbol")]
    del bars
    print(f"[canon] field={a.field} tau={a.tau} symbols {len(tasks)} workers {a.workers}", flush=True)
    t0 = time.time(); parts = []
    with Pool(a.workers, initializer=_init, initargs=(a.field, tau)) as pool:
        for i, r in enumerate(pool.imap_unordered(one, tasks, chunksize=4), 1):
            parts.append(r)
            if i % 250 == 0:
                print(f"[canon] {i}/{len(tasks)} {time.time() - t0:.0f}s", flush=True)
    ev = pd.concat(parts, ignore_index=True); del parts
    ev["half"] = np.where(ev.date < CONFIRM, "seen", "confirm")
    fl = {c: round(float(ev[c].mean()), 4) for c in ["f_bars", "f_price", "f_dollar_vol", "f_zero_vol", "f_pump", "f_zombie", "tradeable"]}
    print("[canon] share of stock-days passing each filter:", fl, flush=True)
    if a.filters:
        ev = ev[ev.tradeable].reset_index(drop=True)
        print(f"[canon] tradeable stock-days kept: {len(ev)}", flush=True)
    ev["after"] = np.where(ev.r20 >= MOVE, "RISE", np.where(ev.r20 <= -MOVE, "FALL", np.where(ev.r20.isna(), "?", "flat")))
    ev.sample(min(len(ev), 1_500_000), random_state=0).to_parquet(out.with_suffix(".parquet"), index=False)
    res = {"declared": "reading, universe, outcomes, tables in the docstring before results", "field": a.field, "tau": a.tau, "filters": a.filters, "filter_pass_shares": fl,
           "symbols": len(tasks), "days": int(len(ev)), "tables": {}}
    pd.set_option("display.width", 220); pd.set_option("display.max_rows", 200)

    def tab(name, key_series):
        res["tables"][name] = {}
        for half in ("seen", "confirm"):
            h = ev[ev.half == half]
            g = h.groupby(key_series.loc[h.index], observed=True)
            t = pd.DataFrame({"n": g.size(), "up20": g.r20.apply(lambda s: float((s.dropna() > 0).mean())), "mean_r20%": g.r20.mean() * 100,
                              "up5": g.r5.apply(lambda s: float((s.dropna() > 0).mean())), "mean_r5%": g.r5.mean() * 100,
                              "rise_share": g.after.apply(lambda s: float((s == "RISE").mean())), "fall_share": g.after.apply(lambda s: float((s == "FALL").mean()))})
            res["tables"][name][half] = {str(k): {c: round(float(v), 4) for c, v in row.items()} for k, row in t.iterrows()}
            print(f"\n== {name} [{half}]"); print(t.round(4).to_string())

    tab("all", pd.Series("all", index=ev.index))
    for f in DISCRETE:
        tab(f, ev[f])
    for f in CONTINUOUS:
        q = ev[f].astype(float).quantile([0.2, 0.4, 0.6, 0.8]).values
        edges = np.unique(np.concatenate([[-np.inf], q, [np.inf]]))
        tab(f + "_quintile", pd.cut(ev[f].astype(float), edges).astype(str))
    tab("D_k x sign(M_k)", ev.D_k.astype(int).astype(str) + " | M" + np.sign(ev.M_k).astype(int).astype(str))
    # every field: its values before RISE / FALL / flat
    res["before"] = {}
    print("\n== every field, values on days BEFORE a RISE vs FALL vs flat (min / 25% / 50% / 75% / max), both halves pooled")
    for f in CONTINUOUS:
        line = f"{f:>9}"; res["before"][f] = {}
        for lab in ("RISE", "FALL", "flat"):
            v = ev.loc[ev.after == lab, f].astype(float).quantile([0, .25, .5, .75, 1]).values
            res["before"][f][lab] = [float(x) for x in v]
            line += f" | {lab:4} " + " ".join(f"{x:>7.4f}" for x in v)
        print(line)
    for f in DISCRETE:
        ct = pd.crosstab(ev[f], ev.after, normalize="columns")
        res["before"][f] = {str(k): {c: round(float(v), 4) for c, v in row.items()} for k, row in ct.iterrows()}
        print(f"\n{f} (share of days in each column):"); print(ct.round(4).to_string())
    json.dump(res, open(out.with_suffix(".json"), "w"), indent=1)
    print("filed:", out.with_suffix(".json"))


if __name__ == "__main__":
    main()
