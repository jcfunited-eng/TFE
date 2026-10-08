"""Declared 2026-10-08 before running (MINE). Does the kernel's reading differ
before rises and before falls once price actually reaches it?
FIELD: move-unit field (tools/ch2_field_units.move_unit_field), own resolution
tau_D (c=3.77, trailing 252 median), canon kernel untouched.
SAMPLE: 150 pool names, seed 7, >= 1000 bars. TRADEABLE at the reading day
(causal): close >= $5 and 20-day median dollar volume >= $2M.
TRADE: reading on day t (known at close t) -> buy close t, sell close t+10.
REPORT: base rate; by D_k (-1/0/+1); by sign of M_k; by URF_k tercile; by
B_k at floor vs above. Win rate, mean 10-day return, n — both halves
(<= 2023, >= 2024). PASS (declared): some reading separates rises from falls by
>= 3 points of win rate vs base in BOTH halves with n >= 300 each.
OUTPUT artifacts/ch4_uf/ch2_unit_field_census.json"""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, "tools"); sys.path.insert(0, ".")
from canon_kernel_causal import readings
from ch2_field_units import move_unit_field
pool = pd.read_parquet("artifacts/ch2_life/ohlcv_pool.parquet")
cnt = pool.groupby("Symbol").size(); names = sorted(cnt[cnt >= 1000].index)
rng = np.random.default_rng(7); names = list(rng.choice(names, 150, replace=False))
rows = []
for i, s in enumerate(names):
    d = pool[pool.Symbol == s].sort_values("Date").reset_index(drop=True)
    F = move_unit_field(d); ok = np.isfinite(F).all(axis=1)
    d = d[ok].reset_index(drop=True); F = F[ok]
    if len(F) < 300: continue
    r = readings(F, tau_D="own")
    c = d.Close.values; dv = (d.Close * d.Volume).rolling(20).median().values
    for _, x in r.iterrows():
        t = int(x.t)
        if t + 10 >= len(c) or c[t] < 5 or not (dv[t] >= 2e6): continue
        rows.append((s, str(d.Date[t])[:10], x.D_k, x.M_k, x.URF_k, x.B_k, c[t + 10] / c[t] - 1))
    if i % 25 == 0: print(i, len(rows), flush=True)
df = pd.DataFrame(rows, columns=["sym", "date", "D_k", "M_k", "URF_k", "B_k", "r10"])
df["half"] = np.where(df.date <= "2023-12-31", "H1", "H2")
df["M_sign"] = np.sign(df.M_k); df["B_floor"] = df.B_k <= -0.999
df["URF_t"] = df.groupby("half").URF_k.transform(lambda v: pd.qcut(v.rank(method="first"), 3, labels=["lo", "mid", "hi"]))
out = {"declared": __doc__, "n": len(df)}
def tab(g): return {"n": int(len(g)), "wr": round(float((g.r10 > 0).mean()) * 100, 1), "mean": round(float(g.r10.mean()) * 100, 2)}
for h, g in df.groupby("half"):
    out[h] = {"base": tab(g)}
    for col in ("D_k", "M_sign", "URF_t", "B_floor"):
        out[h][col] = {str(k): tab(v) for k, v in g.groupby(col, observed=True)}
print(json.dumps({k: v for k, v in out.items() if k != "declared"}, indent=1))
json.dump(out, open("artifacts/ch4_uf/ch2_unit_field_census.json", "w"), indent=1)
