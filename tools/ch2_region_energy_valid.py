"""Region energy on the VALID kernel feed — declared 2026-10-08 before running.
Fixes the inconsistency found in the flare test: the stock was read on the valid feed
but its region's energy band came from the old log-close v2 kernel.
KEPT: pedigree cell membership (sigma/attention/price character, herd_state_live.cell)
and region greed band (gband: share of members rising — price, not kernel).
REPLACED: region energy E_c(t) = mean over the cell's members (>= 5 with data) of each
member's valid-feed per-bar action D[t-1] (path_unit_field L=100; D = |dF| + sigma(W=20)
+ kappa; D[t-1] is knowable at close t), banded against the cell's own trailing 20 days
(pinned 25/75, as tools/ch4_uf_spectrum_herd.trailing_band3).
Members available = pool + blind OHLCV names (4,387).
TEST (unchanged, declared earlier): BUILD = E1 G1 & own D_k > 0 must beat the
all-structures mean in >= 8/10 years; EXHAUSTED = E2 G2 below it in >= 8/10 — on the
studied pool AND the blind names separately.
OUTPUT artifacts/ch4_uf/ch2_region_energy_valid.json"""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, "tools"); sys.path.insert(0, ".")
from ch2_field_units import path_unit_field
from ch4_uf_spectrum_herd import trailing_band3
parts = []
for f in ("artifacts/ch2_life/ohlcv_pool.parquet", "artifacts/ch2_life/ohlcv_blind.parquet"):
    pool = pd.read_parquet(f)
    for s, d in pool.groupby("Symbol"):
        d = d.sort_values("Date").reset_index(drop=True)
        F = pd.DataFrame(path_unit_field(d, 100))
        dF = F.diff().fillna(0.0); nd = np.sqrt((dF ** 2).sum(axis=1))
        sig = sum(F[c].rolling(20, min_periods=1).var(ddof=0) for c in F.columns)
        kap = np.sqrt(((F.shift(-1) - 2 * F + F.shift(1)) ** 2).sum(axis=1))
        D = (nd + sig + kap).shift(1)                      # D[t-1], knowable at close t
        parts.append(pd.DataFrame({"sym": s, "date": d.Date.dt.strftime("%Y%m%d"), "E": D.values}))
act = pd.concat(parts); act = act[np.isfinite(act.E)]
herd = pd.read_parquet("artifacts/ch4_uf/herd_state_live.parquet", columns=["sym", "date", "cell", "gband"])
herd["date"] = herd.date.astype(str)
m = act.merge(herd, on=["sym", "date"], how="inner")
cellE = m.groupby(["cell", "date"]).E.agg(["mean", "size"]).reset_index()
cellE = cellE[cellE["size"] >= 5]
bands = []
for c, g in cellE.groupby("cell"):
    g = g.sort_values("date"); b = trailing_band3(g["mean"].to_numpy(float))
    bands.append(pd.DataFrame({"cell": c, "date": g.date.values, "eband_v": b}))
bands = pd.concat(bands); bands = bands[bands.eband_v >= 0]
key = herd.merge(bands, on=["cell", "date"], how="inner")[["sym", "date", "eband_v", "gband"]]
res = {"declared": __doc__, "member_days": int(len(m))}
for name, path in (("studied", "artifacts/ch4_uf/ch2_flare_region_rows.parquet"), ("blind", "artifacts/ch4_uf/ch2_flare_region_rows_blind.parquet")):
    ev = pd.read_parquet(path).drop(columns=["eband"]).merge(key.drop(columns=["gband"]), on=["sym", "date"], how="inner")
    ev["year"] = ev.date.str[:4]
    out = {"structures": int(len(ev)), "years": {}}
    wb = wx = 0; ys = sorted(ev.year.unique())
    for y in ys:
        g = ev[ev.year == y]; base = g.mv.mean()
        u = g[(g.eband_v == 1) & (g.gband == 1) & (g.D_k > 0)]; x = g[(g.eband_v == 2) & (g.gband == 2)]
        bu = bool(len(u) and u.mv.mean() > base); bx = bool(len(x) and x.mv.mean() < base); wb += bu; wx += bx
        out["years"][y] = {"all": [len(g), round(base * 100, 2)], "build": [len(u), round(u.mv.mean() * 100, 2) if len(u) else None, bu],
                           "exhausted": [len(x), round(x.mv.mean() * 100, 2) if len(x) else None, bx]}
    out["build_years"] = f"{wb}/{len(ys)}"; out["exhausted_years"] = f"{wx}/{len(ys)}"
    res[name] = out
    print(name, out["structures"], "BUILD", out["build_years"], "EXHAUSTED", out["exhausted_years"])
    for y, v in out["years"].items(): print("  ", y, v)
json.dump(res, open("artifacts/ch4_uf/ch2_region_energy_valid.json", "w"), indent=1)
