"""Declared 2026-10-08 before running. Joe's look: "what were the tuples at before
rises and what were they at before falls." Same feed as structure ledger run 2b
(path_unit_field L=100, own resolution, check_feed, tradeable filter on the gate's
end bar). For every closed structure k, the NEXT structure's tradeable move
(close t_b+1 -> close t_b'+1). LARGE RISE: > +10 %. LARGE FALL: < -10 %. QUIET: |move| < 2 %.
Report, per half (<= 2023 / >= 2024): count and the kernel's full L4 output at
structure k (mean of D_k, M_k, R_rev_k, U_star_k, C_k, P_k, B_k, URF_k, w_k, psi_k,
and the share of each regime) before rises vs before falls vs quiet.
Descriptive — no thresholds tuned. OUTPUT artifacts/ch4_uf/ch2_before_moves.json"""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, "tools"); sys.path.insert(0, ".")
from canon_kernel_causal import readings
from ch2_field_units import path_unit_field, check_feed, FeedError
from ch2_canon_census import tradeable_flags
OUT = ["D_k", "M_k", "R_rev_k", "U_star_k", "C_k", "P_k", "B_k", "URF_k", "w_k", "psi_k", "T_k"]
pool = pd.read_parquet("artifacts/ch2_life/ohlcv_pool.parquet")
cnt = pool.groupby("Symbol").size(); names = sorted(cnt[cnt >= 1000].index)
rows = []
for s in names:
    d = pool[pool.Symbol == s].sort_values("Date").reset_index(drop=True)
    F = path_unit_field(d, 100); ok = np.isfinite(F).all(axis=1); d = d[ok].reset_index(drop=True); F = F[ok]
    if len(F) < 400: continue
    try:
        r = readings(F, tau_D="own"); check_feed(F, r)
    except FeedError: continue
    tf = tradeable_flags(d).tradeable.values; c = d.Close.values; dt = d.Date.astype(str).str[:10].values; tb = r.t.values.astype(int)
    for k in range(len(r) - 1):
        a, b = tb[k] + 1, tb[k + 1] + 1
        if b >= len(c) or not tf[tb[k]]: continue
        mv = c[b] / c[a] - 1
        lab = "rise" if mv > 0.10 else "fall" if mv < -0.10 else "quiet" if abs(mv) < 0.02 else None
        if lab: rows.append([dt[a], lab] + [r.iloc[k][o] for o in OUT] + [r.iloc[k].regime])
df = pd.DataFrame(rows, columns=["date", "lab"] + OUT + ["regime"]); df["half"] = np.where(df.date <= "2023-12-31", "H1", "H2")
res = {"declared": __doc__}
for h, g in df.groupby("half"):
    res[h] = {}
    for lab, x in g.groupby("lab"):
        e = {"n": int(len(x))}; e.update({o: round(float(x[o].astype(float).mean()), 4) for o in OUT})
        e.update({f"regime_{k}": round(float(v), 3) for k, v in x.regime.value_counts(normalize=True).items()})
        res[h][lab] = e
print(json.dumps({k: v for k, v in res.items() if k != "declared"}, indent=1))
json.dump(res, open("artifacts/ch4_uf/ch2_before_moves.json", "w"), indent=1)
