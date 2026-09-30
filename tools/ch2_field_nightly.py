"""CH2 field governance — the nightly reading. Runs after the close on the
pool's bars, reproduces exactly what the book simulation did on history,
and writes today's field state and eligible list for comparison beside the
live CH2 (offline; nothing here trades).

WHAT IT COMPUTES (all causal, all from the kernel's readings):
  field state      releasing share (herd resolution, prices in the norm,
                   volume as relevance), storing share, phase (charging /
                   discharging vs 20 days ago), day polarity of releases,
                   20-day polarity, 120-day SLOW polarity, temperature
                   (median particle energy vs its own normal), epic window
  field long       epic window OR field-wide down-release OR charging &
                   quiet, and NOT 20-day polarity UP;
                   if slow polarity < 0.5 (bear): epic window only
  eligible names   tradeable (ch2_canon_census filters), in the pool as of
                   this year, 61–95 days since last filing, not late
                   (96–130), not 0–3 days after a filing; priority
                   epic (0) > down-release (1) > charging (2)
INPUTS: artifacts/ch2_life/ohlcv_pool.parquet (refresh with
  tools/fetch_ohlcv_pool.py --update), filings_pool.parquet
  (tools/fetch_filings_pool.py), SPY bars for the record.
OUTPUT: artifacts/ch2_field/field_state_<date>.json and eligible_<date>.csv,
  plus artifacts/ch2_field/field_state_history.csv (appended).
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
OUT = ROOT / "artifacts" / "ch2_field"
W = 20
_TAU = {}


def _init(tau_map):
    global _TAU
    _TAU = tau_map


def particle(task):
    from canon_kernel_causal import readings
    from ch2_canon_census import tradeable_flags
    symbol, df = task
    df = df.sort_values("Date").reset_index(drop=True)
    F = df[["Open", "High", "Low", "Close"]].values.astype(float)
    v = df.Volume.astype(float); med = v.rolling(W, min_periods=1).median()
    rel = np.where(med > 0, v / med.replace(0, np.nan), 1.0); rel = np.where(np.isfinite(rel), rel, 1.0)
    n = len(df)
    r = readings(F, tau_D=_TAU[symbol], r=rel)
    bnd = np.zeros(n, dtype=bool); bnd[r.t.values] = True
    last = -1; age = np.zeros(n, dtype=int)
    for t in range(n):
        if t >= 1 and bnd[t - 1]:
            last = t - 1
        age[t] = t - last if last >= 0 else 0
    known = np.zeros(n, dtype=bool); known[1:] = bnd[:-1]
    up_prev = np.zeros(n, dtype=bool); up_prev[2:] = (df.Close.values[1:-1] > df.Close.values[:-2])
    return pd.DataFrame({"symbol": symbol, "date": df.Date.values, "age": age, "release": known, "release_up": up_prev,
                         "tradeable": tradeable_flags(df).tradeable.values, "nbar": np.arange(n), "close": df.Close.values})


def band(x: pd.Series, lo=0.2, hi=0.8):
    prev = x.shift(1); q_hi = prev.rolling(252, min_periods=60).quantile(hi); q_lo = prev.rolling(252, min_periods=60).quantile(lo)
    return pd.Series(np.where(x >= q_hi, "HI", np.where(x <= q_lo, "LO", "MID")), index=x.index).where(q_hi.notna())


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--asof", default=None, help="compute as of this date (default: last bar)")
    a = ap.parse_args()
    from ch2_herd_census import herd_state, l0_vectorized
    t0 = time.time(); OUT.mkdir(parents=True, exist_ok=True)
    bars = pd.read_parquet(ROOT / "artifacts" / "ch2_life" / "ohlcv_pool.parquet").sort_values(["Symbol", "Date"]).reset_index(drop=True)
    if a.asof:
        bars = bars[bars.Date <= pd.Timestamp(a.asof)]
    asof = bars.Date.max(); print(f"[field] as of {asof.date()}, {bars.Symbol.nunique()} names", flush=True)
    # ---- herd resolution and particle readings ----
    tau, cs, weather = herd_state(bars, cols=("Open", "High", "Low", "Close"))
    tau_map = {s: tau[s].reindex(g.Date.values).values for s, g in bars.groupby("Symbol", sort=False)}
    with Pool(a.workers, initializer=_init, initargs=(tau_map,)) as pool:
        ev = pd.concat(pool.imap_unordered(particle, [(s, g) for s, g in bars.groupby("Symbol", sort=False)], chunksize=4), ignore_index=True)
    # ---- temperature: each particle's energy vs its own normal, median over eligible names ----
    parts = []
    for sym, g in bars.groupby("Symbol", sort=False):
        _, _, _, D = l0_vectorized(g, ("Open", "High", "Low", "Close")); Dn = pd.Series(D)
        parts.append(pd.DataFrame({"symbol": sym, "date": g.Date.values, "energy": (Dn / Dn.shift(1).rolling(252, min_periods=60).median()).values,
                                   "dv": (g.Close * g.Volume).values, "close": g.Close.values}))
    en = pd.concat(parts, ignore_index=True); en = en[(en.close >= 5) & (en.dv >= 2e6)]
    temp = en.groupby("date").energy.median().rename("temperature")
    # ---- field state per day ----
    tr = ev[ev.tradeable]
    fs = tr.groupby("date").agg(n=("symbol", "size"), releasing=("release", "mean"), storing=("age", lambda x: float((x >= 21).mean())))
    fs["rel_up"] = tr[tr.release].groupby("date").release_up.mean()
    fs = fs.join(temp)
    fs["releasing_band"] = band(fs.releasing); fs["rel_up_band"] = band(fs.rel_up)
    fs["phase"] = np.where(fs.storing > fs.storing.shift(20), "CHARGING", "DISCHARGING")
    fs["polarity20"] = np.where(fs.rel_up.rolling(20, min_periods=10).median() > 0.5, "UP", "DOWN")
    fs["slow120"] = fs.rel_up.rolling(120, min_periods=80).mean()
    p97 = fs.temperature.shift(1).rolling(252, min_periods=120).quantile(0.97)
    fs["epic_day"] = fs.temperature >= p97
    fs["epic_window"] = fs.epic_day.astype(int).rolling(8, min_periods=1).max().astype(bool)
    c_epic = fs.epic_window & (fs.polarity20 != "UP")
    c_d2 = (fs.releasing_band == "HI") & (fs.rel_up_band == "LO") & (fs.polarity20 != "UP")
    c_p8 = (fs.phase == "CHARGING") & (fs.releasing_band == "LO") & (fs.polarity20 != "UP")
    bear = fs.slow120 < 0.5
    fs["c_epic"], fs["c_d2"], fs["c_p8"], fs["bear"] = c_epic, c_d2, c_p8, bear
    fs["field_long"] = np.where(bear, c_epic, c_epic | c_d2 | c_p8)
    fs["priority"] = np.where(c_epic, 0, np.where(c_d2 & ~bear, 1, np.where(c_p8 & ~bear, 2, 9)))
    today = fs.loc[asof]
    # ---- eligible names today ----
    f = pd.read_parquet(ROOT / "artifacts" / "ch2_life" / "filings_pool.parquet"); f["last_filing"] = pd.to_datetime(f.filing_date).astype("datetime64[ns]")
    f = f[f.timeframe.isin(["quarterly", "annual"]) & (f.last_filing <= asof)].sort_values("last_filing").groupby("Symbol").last_filing.max()
    tod = ev[ev.date == asof].copy(); tod["dsl"] = (asof - tod.symbol.map(f)).dt.days
    year_start = pd.Timestamp(year=asof.year, month=1, day=1)
    prev = ev[ev.date < year_start].sort_values("date").groupby("symbol").tail(1).set_index("symbol")
    in_pool = prev.index[(prev.tradeable) & (prev.nbar >= 252)]
    tod["in_pool"] = tod.symbol.isin(in_pool)
    tod["pre"] = tod.dsl.between(61, 95); tod["late"] = tod.dsl.between(96, 130); tod["post"] = tod.dsl <= 3
    elig = tod[tod.tradeable & tod.in_pool & tod.pre & ~tod.late & ~tod.post].copy()
    elig["priority"] = int(today.priority)
    state = {"asof": str(asof.date()), "field_long": bool(today.field_long), "priority": int(today.priority), "bear(slow120<0.5)": bool(today.bear),
             "slow120": round(float(today.slow120), 4) if pd.notna(today.slow120) else None, "phase": today.phase, "polarity20": today.polarity20,
             "releasing": round(float(today.releasing), 4), "releasing_band": today.releasing_band, "rel_up": round(float(today.rel_up), 3) if pd.notna(today.rel_up) else None,
             "rel_up_band": today.rel_up_band, "storing": round(float(today.storing), 4), "temperature": round(float(today.temperature), 3) if pd.notna(today.temperature) else None,
             "epic_day": bool(today.epic_day), "epic_window": bool(today.epic_window), "rules": {"epic": bool(today.c_epic), "down_release": bool(today.c_d2), "charging_quiet": bool(today.c_p8)},
             "eligible_names": int(len(elig)), "tradeable_names": int(tod.tradeable.sum()), "seconds": round(time.time() - t0, 1)}
    tag = str(asof.date())
    json.dump(state, open(OUT / f"field_state_{tag}.json", "w"), indent=1)
    elig.sort_values("dsl", ascending=False)[["symbol", "close", "age", "dsl", "priority"]].to_csv(OUT / f"eligible_{tag}.csv", index=False)
    hist = fs[["releasing", "storing", "rel_up", "temperature", "phase", "polarity20", "slow120", "epic_window", "bear", "field_long", "priority"]]
    hist.to_csv(OUT / "field_state_history.csv")
    print(json.dumps(state, indent=1)); print("eligible today:", len(elig), "->", OUT / f"eligible_{tag}.csv")


if __name__ == "__main__":
    main()
