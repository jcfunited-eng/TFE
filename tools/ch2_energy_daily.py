"""Per stock-day ENERGY reading on the valid feed (one kernel per ticker, whole bar,
path_unit_field L=100, own resolution, psi_r, check_feed). For day t: D_k of the latest
structure whose boundary is known at close t (gate ending t_b is known at close t_b+1).
OUTPUT artifacts/ch4_uf/ch2_energy_daily.parquet (symbol, date, D_k_live)."""
import sys, numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, "tools"); sys.path.insert(0, ".")
from canon_kernel_causal import readings
from ch2_field_units import path_unit_field, check_feed, FeedError
POOL = sys.argv[1] if len(sys.argv) > 1 else "artifacts/ch2_life/ohlcv_pool.parquet"
OUT = sys.argv[2] if len(sys.argv) > 2 else "artifacts/ch4_uf/ch2_energy_daily.parquet"
parts = []
for s, d in pd.read_parquet(POOL).groupby("Symbol"):
    d = d.sort_values("Date").reset_index(drop=True)
    F = path_unit_field(d, 100); ok = np.isfinite(F).all(axis=1); d = d[ok].reset_index(drop=True); F = F[ok]
    if len(F) < 400: continue
    cc = pd.Series(F[:, 3]); rr = np.where(cc > cc.rolling(10, min_periods=1).mean(), 1.0, 0.5)
    try:
        r = readings(F, tau_D="own", r=rr); check_feed(F, r)
    except FeedError:
        continue
    col = np.full(len(F), np.nan); known = np.zeros(len(F), bool)
    for t_b, dk in zip(r.t.values.astype(int), r.D_k.values):
        if t_b + 1 < len(F): col[t_b + 1] = dk; known[t_b + 1] = True
    # release exit (10-08): for a buy at close t, the first close >= t+1 at which a NEW
    # structure boundary is known (the release), capped at t+10 sessions
    c = d.Close.values.astype(float); n = len(c); nxt = np.full(n, -1)
    j = -1
    for t in range(n - 1, -1, -1):
        nxt[t] = j
        if known[t]: j = t
    cols = {}
    for cap in (10, 30):
        ex = np.array([min(nxt[t], t + cap) if nxt[t] > t else t + cap for t in range(n)])
        ok2 = ex < n
        cols[f"r_rel{cap}"] = np.where(ok2, c[np.minimum(ex, n - 1)] / c - 1, np.nan)
        cols[f"h_rel{cap}"] = np.where(ok2, ex - np.arange(n), np.nan)
    parts.append(pd.DataFrame({"symbol": s, "date": d.Date.astype(str).str[:10], "D_k_live": pd.Series(col).ffill().values, **cols}))
pd.concat(parts).dropna(subset=["D_k_live"]).to_parquet(OUT); print("wrote", OUT)
