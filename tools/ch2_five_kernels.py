"""Five kernels per stock — declared 2026-10-08 before running (MINE, Joe: "you know
what we are trying to achieve"). The kernel (standalone_truth_kernel.py) reads ONE
series; the bar has five. Each of Open, High, Low, Close, Volume gets its own kernel:
path_unit_field L=100 channel, own resolution (3.77 x own trailing median D, HIS),
relevance psi_r on its own series (the file's rule), canon kernel untouched. Feed check
per channel (time coverage + pinned outputs); a stock is read only if all five pass.
JOINT STATE on day t: each channel's latest closed-gate reading known at close t (gate
ending t_b is known at close t_b+1) -> (D_k of O,H,L,C,V). Sampled every 5th session.
OUTCOME: close t -> close t+20 (the structure scale); RISE > +10 %, FALL < -10 %.
SELECTION on studied H1 (<= 2021) only: joint D_k patterns with n >= 300 whose rise share
among large moves is >= base + 5 pts (UP set) or <= base - 5 pts (DOWN set).
TEST, no reselection: studied H2 (>= 2022) and the blind 1,500 (all years, and each half).
PASS: UP set rise share >= base + 3 and DOWN set <= base - 3 in studied H2 AND blind.
OUTPUT artifacts/ch4_uf/ch2_five_kernels.json + rows parquet."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, "tools"); sys.path.insert(0, ".")
from canon_kernel_causal import readings
from ch2_field_units import path_unit_field, check_feed, FeedError
from ch2_canon_census import tradeable_flags
CH = ["O", "H", "L", "C", "V"]

def joint(d):
    F = path_unit_field(d, 100); ok = np.isfinite(F).all(axis=1); d = d[ok].reset_index(drop=True); F = F[ok]
    if len(F) < 400: return None
    n = len(F); state = np.zeros((n, 5)); known = np.zeros(n, bool)
    for j in range(5):
        x = F[:, [j]]; s = pd.Series(x[:, 0]); r_ = np.where(s > s.rolling(10, min_periods=1).mean(), 1.0, 0.5)
        r = readings(x, tau_D="own", r=r_)
        check_feed(x, r, outputs=("D_k", "M_k", "URF_k"))     # single-channel: share test trivially 100%
        col = np.full(n, np.nan)
        for t_b, dk in zip(r.t.values.astype(int), r.D_k.values):
            if t_b + 1 < n: col[t_b + 1] = dk
        state[:, j] = pd.Series(col).ffill().values
    return d, state

def run(path, tag):
    pool = pd.read_parquet(path); rows = []; refused = 0
    for s, d in pool.groupby("Symbol"):
        d = d.sort_values("Date").reset_index(drop=True)
        if len(d) < 1000: continue
        try:
            out = joint(d)
        except FeedError:
            refused += 1; continue
        if out is None: continue
        d, st = out; c = d.Close.values; tf = tradeable_flags(d).tradeable.values; dt = d.Date.astype(str).str[:10].values
        for t in range(300, len(c) - 20, 5):
            if not tf[t] or np.isnan(st[t]).any(): continue
            rows.append((s, dt[t], "".join("+0-"[1 - int(v)] for v in st[t]), c[t + 20] / c[t] - 1))
    df = pd.DataFrame(rows, columns=["sym", "date", "pattern", "r20"]); df["set"] = tag
    print(tag, "names refused", refused, "rows", len(df), flush=True)
    return df

if __name__ == "__main__":
    import warnings; warnings.filterwarnings("ignore")
    # check_feed's channel-share test would refuse every 1-D field; call it on 2+ channels only
    studied = run("artifacts/ch2_life/ohlcv_pool.parquet", "studied")
    blind = run("artifacts/ch2_life/ohlcv_blind.parquet", "blind")
    df = pd.concat([studied, blind]); df.to_parquet("artifacts/ch4_uf/ch2_five_kernels_rows.parquet")
    df["half"] = np.where(df.date <= "2021-12-31", "H1", "H2"); big = df[df.r20.abs() > 0.10].copy(); big["rise"] = big.r20 > 0
    sel = big[(big.set == "studied") & (big.half == "H1")]; base = sel.rise.mean()
    st = sel.groupby("pattern").rise.agg(["mean", "size"]); st = st[st["size"] >= 300]
    UP = sorted(st[st["mean"] >= base + 0.05].index); DOWN = sorted(st[st["mean"] <= base - 0.05].index)
    res = {"declared": __doc__, "selection_base": round(base * 100, 1), "UP": {p: [round(float(st.loc[p, "mean"]) * 100, 1), int(st.loc[p, "size"])] for p in UP},
           "DOWN": {p: [round(float(st.loc[p, "mean"]) * 100, 1), int(st.loc[p, "size"])] for p in DOWN}, "tests": {}}
    def test(g, name):
        b = g.rise.mean(); u = g[g.pattern.isin(UP)]; x = g[g.pattern.isin(DOWN)]
        res["tests"][name] = {"base": round(b * 100, 1), "large_moves": int(len(g)),
            "UP": [round(u.rise.mean() * 100, 1) if len(u) else None, int(len(u))], "DOWN": [round(x.rise.mean() * 100, 1) if len(x) else None, int(len(x))]}
    test(sel, "studied H1 (selection)")
    test(big[(big.set == "studied") & (big.half == "H2")], "studied H2 (test)")
    test(big[big.set == "blind"], "blind all (test)")
    test(big[(big.set == "blind") & (big.half == "H1")], "blind H1 (test)")
    test(big[(big.set == "blind") & (big.half == "H2")], "blind H2 (test)")
    print(json.dumps({k: v for k, v in res.items() if k != "declared"}, indent=1))
    json.dump(res, open("artifacts/ch4_uf/ch2_five_kernels.json", "w"), indent=1)
