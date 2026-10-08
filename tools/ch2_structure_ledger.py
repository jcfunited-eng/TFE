"""CH2 structural assessment, physics first — declared 2026-10-08 before running.
Joe: "full structural assessment with the proper filtering and resolution ... scale
should be at least 50 bar ... physics first, not quant."

1 DATA      full bar O,H,L,C,V -> move-unit field (each channel in its own typical
            daily move, causal); check_feed must pass (else the name is refused).
2 KERNEL    canon kernel as shipped (tools/canon_kernel_causal.readings), untouched.
3 RESOLUTION per stock, causal: tau_D(t) = 98th percentile of its own D over the
            prior 252 bars -> about one boundary per 50 bars (MINE: the quantile).
4 FILTER    tools/ch2_canon_census.tradeable_flags (bars, price, $ volume, zero-volume,
            pump, zombie) must be True on the gate's end bar — filter, then look.
5 STRUCTURE each closed gate's FULL L4 tuple -> class: (D_k, R_rev_k, P_k, sign M_k,
            U*_k band [<1/3, <2/3, rest], B_k band [floor, <0, >=0], C_k, the gate's own
            price direction). Species = (class of previous gate, class of this gate).
6 OUTCOME   direction of the NEXT gate, measured tradeably: close at the bar after this
            gate's boundary is known (t_b+1) to close at t_b'+1 of the next gate.
7 LEDGER    strictly as-of-issue: a completion counts only after its reveal date is
            before the issue date. Predict when the species has n >= 20 completions and
            >= 75% of them one way (the record's species-law band). Per year: predictions,
            hit rate, vs the null (always predict the more common direction that year).
OUTPUT artifacts/ch4_uf/ch2_structure_ledger.json
RUN 1 (10-08) VOID: median gate length 1 bar (q98 resolution clusters); predictions not reported.
RUN 2 (10-08, declared before running): field = path_unit_field(L=100) (Joe: scale >= 50 bars),
resolution = own (HIS: 3.77 x own trailing median D); everything else unchanged.
RUN 2 first pass refused 1,734 names on a WRONG health check (median piece length; events
make 1-bar pieces by construction). Check corrected to time coverage >= 80% in 5+ bar
structures (outcome-blind); rerun = run 2b.
"""
import sys, json, numpy as np, pandas as pd
from collections import defaultdict
sys.path.insert(0, "tools"); sys.path.insert(0, ".")
from canon_kernel_causal import readings
from ch2_field_units import path_unit_field, check_feed, FeedError
from ch2_canon_census import tradeable_flags

def own_D(F):
    n = len(F); W = 20
    dF = np.zeros_like(F); dF[1:] = F[1:] - F[:-1]
    sig = np.array([np.mean(np.sum((F[max(0, t-W+1):t+1] - F[max(0, t-W+1):t+1].mean(0))**2, 1)) for t in range(n)])
    kap = np.zeros(n); kap[1:-1] = np.linalg.norm(F[2:] - 2*F[1:-1] + F[:-2], axis=1)
    return np.linalg.norm(dF, axis=1) + sig + kap

def band(x, cuts): return int(np.searchsorted(cuts, x, side="right"))

pool = pd.read_parquet("artifacts/ch2_life/ohlcv_pool.parquet")
cnt = pool.groupby("Symbol").size(); names = sorted(cnt[cnt >= 1000].index)
events = []; refused = {}; glen = []
for i, s in enumerate(names):
    d = pool[pool.Symbol == s].sort_values("Date").reset_index(drop=True)
    F = path_unit_field(d, 100); ok = np.isfinite(F).all(axis=1)
    d = d[ok].reset_index(drop=True); F = F[ok]
    if len(F) < 400: continue
    try: check_feed(F)
    except FeedError as e: refused[s] = str(e); continue
    r = readings(F, tau_D="own")
    if len(r) < 4: continue
    try: check_feed(F, r)
    except FeedError as e: refused[s] = str(e); continue
    tf = tradeable_flags(d).tradeable.values; c = d.Close.values; dates = d.Date.astype(str).str[:10].values
    tb = r.t.values.astype(int); glen += list(np.diff(tb))
    cls = []
    for k in range(len(r)):
        x = r.iloc[k]; ta = tb[k-1] if k else 0
        gdir = int(np.sign(c[min(tb[k], len(c)-1) - 1] / c[max(ta - 1, 0)] - 1))
        cls.append((int(x.D_k), int(x.R_rev_k), int(x.P_k), int(np.sign(x.M_k)), band(x.U_star_k, [1/3, 2/3]),
                    0 if x.B_k <= -0.999 else (1 if x.B_k < 0 else 2), int(x.C_k), gdir))
    for k in range(1, len(r) - 1):
        a, b2 = tb[k] + 1, tb[k+1] + 1
        if b2 >= len(c) or not tf[tb[k]]: continue
        events.append((dates[a], dates[b2], s, (cls[k-1], cls[k]), int(np.sign(c[b2] / c[a] - 1)), c[b2] / c[a] - 1))
    if i % 300 == 0: print(i, len(events), flush=True)
ev = pd.DataFrame(events, columns=["issue", "reveal", "sym", "species", "out", "ret"]).sort_values("issue").reset_index(drop=True)
# as-of-issue ledger
done = defaultdict(lambda: [0, 0]); pend = sorted(zip(ev.reveal, ev.species, ev.out)); pi = 0
pred = []
for row in ev.itertuples():
    while pi < len(pend) and pend[pi][0] < row.issue:
        _, sp, o = pend[pi]; done[sp][0 if o > 0 else 1] += 1 if o != 0 else 0; pi += 1
    up, dn = done[row.species]; n = up + dn
    p = (1 if up > dn else -1) if n >= 20 and max(up, dn) / n >= 0.75 else 0
    pred.append(p)
ev["pred"] = pred; ev["year"] = ev.issue.str[:4]
res = {"declared": __doc__, "names": len(names), "refused": len(refused), "events": len(ev),
       "median_gate_bars": float(np.median(glen)) if glen else None, "per_year": {}}
for y, g in ev.groupby("year"):
    nul = max((g.out > 0).mean(), (g.out < 0).mean())
    h = g[g.pred != 0]
    res["per_year"][y] = {"gates": int(len(g)), "null_hit": round(float(nul) * 100, 1), "predictions": int(len(h)),
                          "hit": round(float((h.pred == h.out).mean()) * 100, 1) if len(h) else None,
                          "mean_ret_when_pred_up": round(float(h[h.pred > 0].ret.mean()) * 100, 2) if (h.pred > 0).any() else None,
                          "mean_ret_when_pred_down": round(float(h[h.pred < 0].ret.mean()) * 100, 2) if (h.pred < 0).any() else None}
print(json.dumps({k: v for k, v in res.items() if k != "declared"}, indent=1))
json.dump(res, open("artifacts/ch4_uf/ch2_structure_ledger_run2b.json", "w"), indent=1)
