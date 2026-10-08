"""Flares and their active regions — declared 2026-10-08 before running (Joe: "this is
a physics problem first — solar flare prediction"; July: the herd is the stock's OWN
peer cohort, not the market; "predicting the flares").
REGION: the stock's own pedigree cell each day (artifacts/ch4_uf/herd_state_live.parquet:
cell, eband = region energy band, gband = region greed band, 0/1/2, each banded against
the cell's own trailing history; day-t state uses day-t closes, knowable at close t).
STORED ENERGY: the stock's own kernel structure (valid feed: path_unit_field L=100, own
resolution, check_feed, tradeable filter) — D_k at the structure's end.
FLARE: the next structure moves > 10 % (rise) or < -10 % (fall); quiet |move| < 2 %.
Issue = close t_b+1; region state read on that day.
REPORT per half (<= 2023 / >= 2024), per region state (eband x gband):
  flare rate = flares / all structures; polarity = rises / flares;
  and the same split by the stock's own D_k (>0 / <=0).
Descriptive; nothing tuned. OUTPUT artifacts/ch4_uf/ch2_flare_region.json"""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, "tools"); sys.path.insert(0, ".")
from canon_kernel_causal import readings
from ch2_field_units import path_unit_field, check_feed, FeedError
from ch2_canon_census import tradeable_flags
herd = pd.read_parquet("artifacts/ch4_uf/herd_state_live.parquet")
herd["key"] = herd.sym.astype(str) + "|" + herd.date.astype(str)
hmap = dict(zip(herd.key, zip(herd.eband, herd.gband)))
import os
POOL = os.environ.get("FLARE_POOL", "artifacts/ch2_life/ohlcv_pool.parquet"); SUF = os.environ.get("FLARE_SUFFIX", "")
pool = pd.read_parquet(POOL)
cnt = pool.groupby("Symbol").size(); names = sorted(cnt[cnt >= 1000].index)
rows = []
for s in names:
    d = pool[pool.Symbol == s].sort_values("Date").reset_index(drop=True)
    F = path_unit_field(d, 100); ok = np.isfinite(F).all(axis=1); d = d[ok].reset_index(drop=True); F = F[ok]
    if len(F) < 400: continue
    try:
        rr = None
        if os.environ.get("FLARE_RELEVANCE") == "psi_r":
            # the original file's relevance (standalone_truth_kernel.psi_r, W_r=10):
            # 1.0 if the latest value is above its 10-bar mean, else 0.5 — on the close channel
            cc = pd.Series(F[:, 3]); rr = np.where(cc > cc.rolling(10, min_periods=1).mean(), 1.0, 0.5)
        r = readings(F, tau_D="own", r=rr); check_feed(F, r)
    except FeedError: continue
    tf = tradeable_flags(d).tradeable.values; c = d.Close.values
    dk = d.Date.dt.strftime("%Y%m%d").values; tb = r.t.values.astype(int)
    for k in range(len(r) - 1):
        a, b = tb[k] + 1, tb[k + 1] + 1
        if b >= len(c) or not tf[tb[k]]: continue
        st = hmap.get(f"{s}|{dk[a]}")
        if st is None: continue
        mv = c[b] / c[a] - 1
        rows.append((dk[a], s, st[0], st[1], float(r.iloc[k].D_k), mv, int(b - a)))
df = pd.DataFrame(rows, columns=["date", "sym", "eband", "gband", "D_k", "mv", "bars"])
df["half"] = np.where(df.date <= "20231231", "H1", "H2")
df["flare"] = df.mv.abs() > 0.10; df["rise"] = df.mv > 0.10
res = {"declared": __doc__, "structures": len(df)}
def cell(g):
    f = g[g.flare]
    return {"n": int(len(g)), "flare_rate": round(float(g.flare.mean()) * 100, 1), "flares": int(len(f)),
            "polarity_up": round(float(f.rise.mean()) * 100, 1) if len(f) else None}
for h, g in df.groupby("half"):
    res[h] = {"all": cell(g),
              "region": {f"E{e}G{gg}": cell(x) for (e, gg), x in g.groupby(["eband", "gband"])},
              "region_x_own_Dk": {f"E{e}G{gg}|D{'+' if dpos else '0-'}": cell(x) for (e, gg, dpos), x in g.assign(dpos=g.D_k > 0).groupby(["eband", "gband", "dpos"])}}
print(json.dumps({k: v for k, v in res.items() if k != "declared"}, indent=1))
json.dump(res, open(f"artifacts/ch4_uf/ch2_flare_region{SUF}.json", "w"), indent=1)
df.to_parquet(f"artifacts/ch4_uf/ch2_flare_region_rows{SUF}.parquet")
