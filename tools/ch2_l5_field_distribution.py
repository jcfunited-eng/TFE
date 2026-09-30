"""CH2 L5 — the FULL FIELD: the state of the whole pool as the kernel reads it.
Declared 2026-09-30 before running.

Joe: "the analysis needs to be FULL field — and not single signals."

The field is every particle. Its state on a day is the distribution of the
kernel's readings across the pool — counts, not averages of tuples:
  releasing   share of tradeable names whose gate ended that day (herd
              resolution, prices in the norm, volume as relevance)
  storing     share whose standing gate is >= 21 bars old
  fresh       share whose standing gate is <= 5 bars old
  rel_up      of the day's releases, the share whose boundary bar closed
              up (the L0 signed dF, which the canon carries)
Each is read against its own trailing 252 days (causal): HI = at or above
the 80th percentile, LO = at or below the 20th, MID otherwise.

GOVERNANCE (declared): long on days when the field is releasing HI (the
field-wide shock) — the physical statement behind "SPY busy", now read
from the field itself with no index; the other three describe the same
day and are reported as the field's full state, not as separate signals.
ARMS: releasing HI; releasing HI split by rel_up (the field's release
direction, from the kernel's own signed dF); storing HI; releasing LO.
HOLD 20; one position per name; tradeable only. PER YEAR vs the null.
PASS BAR: WR >= null + 3 points in 5 of 6 years AND mean better in 5 of 6.
OUTPUT: artifacts/ch4_uf/ch2_l5_field_distribution.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
HOLD = 20
OUT = ROOT / "artifacts" / "ch4_uf" / "ch2_l5_field_distribution.json"


def band(x: pd.Series) -> pd.Series:
    prev = x.shift(1)
    hi = prev.rolling(252, min_periods=60).quantile(0.8); lo = prev.rolling(252, min_periods=60).quantile(0.2)
    return pd.Series(np.where(x >= hi, "HI", np.where(x <= lo, "LO", "MID")), index=x.index).where(hi.notna())


def positions(g: pd.DataFrame, cond: np.ndarray):
    idx = np.where(cond)[0]; taken, last_exit = [], -1
    for i in idx:
        if i <= last_exit: continue
        taken.append(i); last_exit = i + HOLD
    return g.iloc[taken]


def main():
    ev = pd.read_parquet(ROOT / "artifacts" / "ch4_uf" / "ch2_particle_days_B.parquet")
    bars = pd.read_parquet(ROOT / "artifacts" / "ch2_life" / "ohlcv_pool.parquet", columns=["Date", "Symbol", "Close"])
    bars["date"] = bars.Date.astype(str).str[:10]; bars = bars.sort_values(["Symbol", "date"])
    bars["up"] = (bars.groupby("Symbol").Close.diff() > 0)
    ev = ev.merge(bars[["Symbol", "date", "up"]].rename(columns={"Symbol": "symbol"}), on=["symbol", "date"], how="left")
    # the boundary known at close t formed at bar t-1; its direction is bar t-1's close vs t-2 -> shift 'up' by one within symbol
    ev = ev.sort_values(["symbol", "date"]).reset_index(drop=True)
    ev["bar_up_prev"] = ev.groupby("symbol").up.shift(1)
    tr = ev[ev.tradeable]
    day = tr.groupby("date").agg(n=("symbol", "size"), releasing=("release", "mean"), storing=("age", lambda a: float((a >= 21).mean())),
                                 fresh=("age", lambda a: float((a <= 5).mean())))
    rel = tr[tr.release].groupby("date").bar_up_prev.mean().rename("rel_up")
    day = day.join(rel)
    # trailing bands (causal) — the field's state
    state = pd.DataFrame({k: band(day[k]) for k in ("releasing", "storing", "fresh", "rel_up")}, index=day.index)
    state["releasing_val"] = day.releasing; state["rel_up_val"] = day.rel_up
    state = state.dropna(subset=["releasing"])
    print("field state days:", len(state)); print(state.releasing.value_counts().to_dict())
    print("the field's full state, share of days in each (releasing x storing x rel_up):")
    print(state.groupby(["releasing", "storing", "rel_up"]).size().sort_values(ascending=False).head(12).to_string())
    ev = ev.merge(state.reset_index().rename(columns={"index": "date"}), on="date", how="inner")
    ev = ev[ev.r20.notna()].sort_values(["symbol", "date"]).reset_index(drop=True)
    ev["year"] = ev.date.str[:4]
    trad = ev.tradeable.values
    R = ev.releasing.values; S = ev.storing.values; U = ev.rel_up.values
    arms = {"N0 every tradeable day": trad,
            "D1 field releasing HI": trad & (R == "HI"),
            "D2 field releasing HI & releases mostly DOWN (rel_up LO)": trad & (R == "HI") & (U == "LO"),
            "D3 field releasing HI & releases mostly UP (rel_up HI)": trad & (R == "HI") & (U == "HI"),
            "D4 field storing HI (quiet stored field)": trad & (S == "HI"),
            "D5 field releasing LO": trad & (R == "LO"),
            "D6 field releasing LO & storing HI": trad & (R == "LO") & (S == "HI")}
    res = {"declared": "field state, governance, arms, per-year report and pass bar in the docstring before results", "arms": {}}
    pd.set_option("display.width", 220); tables = {}
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
        print(f"[field] {name}: years WR >= null+3: {wr_ok}/6, mean > null: {mean_ok}/6, PASS={res['arms'][name]['PASS']}")
    state.to_csv(ROOT / "artifacts" / "ch2_life" / "field_state_daily.csv")
    json.dump(res, open(OUT, "w"), indent=1); print("filed:", OUT)


if __name__ == "__main__":
    main()
