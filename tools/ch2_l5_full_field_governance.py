"""CH2 L5 — governance over the FULL field reading. Declared 2026-09-30 before running.

Joe: "the Kernel is data agnostic" · "L5 is the governance" · "the analysis
needs to be FULL field — and not single signals."

THE FIELD: SPY's daily bar, read by the same kernel as any stock
(tools/canon_kernel_causal.py; prices in the norm, volume as relevance;
own resolution 3.77x its trailing median bar; causal). Its standing
reading each day is the WHOLE tuple:
  D_k, M_k, R_rev_k, U*_k, C_k, P_k, B_k, R_k, URF_k, g_k, Hyst_k,
  w_k, psi_k, S_k, U_k, IAS_k, regime, age of the standing gate,
  and the L0 signed displacement of the standing gate so far (canon SEV
  carries dF signed; L1 drops the sign; L5 may read it).
GOVERNANCE (the spec's own L5 approximation, CP-0): each day's full tuple
is compared with every earlier day's full tuple (each coordinate scaled
by its trailing-252 spread; earlier = at least 21 sessions earlier, so
the outcome is known); the 30 nearest days vote with what the POOL did
in the 20 sessions after them (the pool's mean up-share over tradeable
stock-days). EXPOSURE: long when the vote >= 0.55, flat otherwise.
Nothing else. No single field is read alone.
SELECTION (particle, same law): inside long days, each tradeable name's
own full tuple is compared with its own earlier days; enter only if its
30 nearest days' 20-session outcome was up >= 0.55 (arm S1); arm S0 takes
every tradeable name.
HOLD 20 sessions, one position per name. PER YEAR: positions, win rate,
mean 20-day return, exposure (share of days long). NULL: every tradeable
day. PASS BAR (declared): WR >= null + 3 points in 5 of 6 years AND mean
better in 5 of 6. Costs / survivorship not handled.
OUTPUT: artifacts/ch4_uf/ch2_l5_full_field_governance.json
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
HOLD = 20
K = 30
VOTE = 0.55
START = "2021-01-01"
COORDS = ["D_k", "M_k", "R_rev_k", "U_star_k", "C_k", "P_k", "B_k", "R_k", "URF_k", "g_k", "Hyst_k", "w_k", "psi_k", "S_k", "U_k", "IAS_k", "reg", "age", "disp"]
OUT = ROOT / "artifacts" / "ch4_uf" / "ch2_l5_full_field_governance.json"
_TAU = {}


def full_reading(df: pd.DataFrame, tau) -> pd.DataFrame:
    """The whole standing tuple on every day, causal (prices in the norm, volume as relevance)."""
    from canon_kernel_causal import readings, FIELDS
    F = df[["Open", "High", "Low", "Close"]].values.astype(float)
    v = df.Volume.astype(float); med = v.rolling(W, min_periods=1).median()
    rel = np.where(med > 0, v / med.replace(0, np.nan), 1.0); rel = np.where(np.isfinite(rel), rel, 1.0)
    close = df.Close.values.astype(float); n = len(close)
    r = readings(F, tau_D=tau, r=rel)
    r["reg"] = r.regime.map({"STABLE": 0, "TRANSITIONAL": 1, "VOLATILE": 2, "DEGENERATE": 3})
    cols = [c for c in COORDS if c not in ("age", "disp")]
    st = pd.DataFrame(np.nan, index=np.arange(n), columns=cols)
    st.iloc[r.t.values] = r[cols].values
    st = st.ffill()
    bnd = np.zeros(n, dtype=bool); bnd[r.t.values] = True
    last = -1; age = np.zeros(n); disp = np.zeros(n)
    for t in range(n):
        if t >= 1 and bnd[t - 1]:
            last = t - 1
        age[t] = t - last if last >= 0 else 0
        disp[t] = close[t] / close[last] - 1.0 if last >= 0 else 0.0   # signed displacement of the standing gate so far
    st["age"] = age; st["disp"] = disp
    st["close"] = close
    st["date"] = df.Date.astype(str).str[:10].values
    fwd = np.full(n, np.nan); fwd[: n - HOLD] = close[HOLD:] / close[: n - HOLD] - 1.0
    st["r20"] = fwd
    return st


def neighbour_vote(X: np.ndarray, y: np.ndarray, valid: np.ndarray, start_idx: int) -> np.ndarray:
    """For each day t >= start_idx: the mean of y over the K nearest earlier days (index <= t - HOLD - 1,
    y known), coordinates scaled by the trailing-252 std at t. Causal."""
    n = len(X); out = np.full(n, np.nan)
    for t in range(start_idx, n):
        lo = max(0, t - 252); sd = X[lo: t].std(axis=0); sd[sd == 0] = 1.0
        past = np.arange(0, t - HOLD)
        past = past[valid[past]]
        if len(past) < K:
            continue
        d = np.sqrt((((X[past] - X[t]) / sd) ** 2).sum(axis=1))
        nn = past[np.argsort(d)[:K]]
        out[t] = float(np.mean(y[nn]))
    return out


def _init(tau_map):
    global _TAU
    _TAU = tau_map


def particle(task):
    from ch2_canon_census import tradeable_flags
    symbol, df = task
    df = df.sort_values("Date").reset_index(drop=True)
    st = full_reading(df, _TAU[symbol])
    X = st[COORDS].fillna(0.0).values.astype(float)
    y = (st.r20.values > 0).astype(float); valid = ~np.isnan(st.r20.values)
    start_idx = int(np.searchsorted(st.date.values, START))
    st["own_vote"] = neighbour_vote(X, y, valid, max(start_idx, 300))
    st["tradeable"] = tradeable_flags(df).tradeable.values
    st["symbol"] = symbol
    return st.loc[st.date >= START, ["symbol", "date", "r20", "tradeable", "own_vote"]]


def positions(g: pd.DataFrame, cond: np.ndarray):
    idx = np.where(cond)[0]; taken, last_exit = [], -1
    for i in idx:
        if i <= last_exit: continue
        taken.append(i); last_exit = i + HOLD
    return g.iloc[taken]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--every", type=int, default=1)
    a = ap.parse_args()
    from ch2_herd_census import herd_state
    t0 = time.time()
    # ---- the field: SPY's full reading and the pool's outcome after each day ----
    spy = pd.read_csv(ROOT / "artifacts" / "ch2_life" / "SPY_ohlcv_daily.csv"); spy["Date"] = spy.Date.astype(str)
    fs = full_reading(spy, "own")
    pool = pd.read_parquet(ROOT / "artifacts" / "ch4_uf" / "ch2_canon_census_bar_tau0p20_filtered.parquet", columns=["date", "r20"])
    pool["date"] = pool.date.astype(str).str[:10]
    pool_up = pool.groupby("date").r20.apply(lambda s: float((s.dropna() > 0).mean()))
    fs["pool_up"] = fs.date.map(pool_up)
    X = fs[COORDS].fillna(0.0).values.astype(float); y = fs.pool_up.values; valid = ~np.isnan(y)
    start_idx = int(np.searchsorted(fs.date.values, "2020-06-01"))
    fs["vote"] = neighbour_vote(X, np.nan_to_num(y, nan=0.5), valid, start_idx)
    fs["long"] = fs.vote >= VOTE
    print(f"[gov] field readings {len(fs)}; days with a vote {fs.vote.notna().sum()}; long days {int(fs.long.sum())} ({time.time() - t0:.0f}s)", flush=True)
    # ---- the particles ----
    bars = pd.read_parquet(ROOT / "artifacts" / "ch2_life" / "ohlcv_pool.parquet")
    symbols = sorted(bars.Symbol.unique())[:: a.every]
    bars = bars[bars.Symbol.isin(symbols)].sort_values(["Symbol", "Date"]).reset_index(drop=True)
    tau, cs, weather = herd_state(bars, cols=("Open", "High", "Low", "Close"))
    tau_map = {s: tau[s].reindex(g.Date.values).values for s, g in bars.groupby("Symbol", sort=False)}
    tasks = [(s, g) for s, g in bars.groupby("Symbol", sort=False)]
    del bars
    parts = []
    with Pool(a.workers, initializer=_init, initargs=(tau_map,)) as pool_:
        for i, r in enumerate(pool_.imap_unordered(particle, tasks, chunksize=2), 1):
            parts.append(r)
            if i % 500 == 0: print(f"[gov] particles {i}/{len(tasks)} {time.time() - t0:.0f}s", flush=True)
    ev = pd.concat(parts, ignore_index=True); del parts
    ev = ev.merge(fs[["date", "vote", "long"]], on="date", how="left")
    ev = ev[ev.r20.notna() & ev.vote.notna()].sort_values(["symbol", "date"]).reset_index(drop=True)
    ev["year"] = ev.date.str[:4]
    trad = ev.tradeable.values; long_ = ev.long.values; own = (ev.own_vote >= VOTE).values
    arms = {"N0 every tradeable day": trad,
            "F1 field long (full-tuple vote >= 0.55)": trad & long_,
            "F1+S1 field long & particle own-tuple vote >= 0.55": trad & long_ & own,
            "S1 alone: particle own-tuple vote >= 0.55": trad & own,
            "F0 field flat (vote < 0.55) — the other side": trad & ~long_}
    res = {"declared": "field, governance, selection, hold, per-year report and pass bar in the docstring before results",
           "field_long_days_per_year": fs[fs.date >= START].groupby(fs.date.str[:4]).long.mean().round(3).to_dict(), "arms": {}}
    pd.set_option("display.width", 220)
    tables = {}
    for name, cond in arms.items():
        ev["_c"] = cond
        pos = pd.concat([positions(g, g._c.values) for _, g in ev.groupby("symbol", sort=False)], ignore_index=True)
        t = pos.groupby("year").r20.agg(positions="size", win_rate=lambda s: float((s > 0).mean()), mean_r20_pct=lambda s: float(s.mean() * 100))
        tables[name] = t
        res["arms"][name] = {y: {c: round(float(v), 4) for c, v in row.items()} for y, row in t.iterrows()}
        res["arms"][name]["total"] = {"positions": int(len(pos)), "win_rate": round(float((pos.r20 > 0).mean()), 4), "mean_r20_pct": round(float(pos.r20.mean() * 100), 3)}
        print(f"\n== {name}: positions {len(pos)}, WR {float((pos.r20 > 0).mean()):.4f}, mean {float(pos.r20.mean() * 100):.3f}%"); print(t.round(4).to_string())
    base = tables["N0 every tradeable day"]
    for name, t in tables.items():
        if name.startswith("N0"): continue
        j = t.join(base, rsuffix="_base")
        wr_ok = int(((j.win_rate - j.win_rate_base) >= 0.03).sum()); mean_ok = int((j.mean_r20_pct > j.mean_r20_pct_base).sum())
        res["arms"][name]["PASS"] = bool(wr_ok >= 5 and mean_ok >= 5); res["arms"][name]["years_wr_ge_plus3"] = wr_ok; res["arms"][name]["years_mean_better"] = mean_ok
        print(f"[gov] {name}: years WR >= null+3: {wr_ok}/6, years mean > null: {mean_ok}/6, PASS={res['arms'][name]['PASS']}")
    print("[gov] share of days the field governance is long, per year:", res["field_long_days_per_year"])
    fs.to_csv(ROOT / "artifacts" / "ch2_life" / "SPY_full_reading_governance.csv", index=False)
    json.dump(res, open(OUT, "w"), indent=1)
    print("filed:", OUT)


if __name__ == "__main__":
    main()
