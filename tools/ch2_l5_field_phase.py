"""CH2 L5 — the field's phase in its own charge/discharge cycle. Declared before running.

Seen first (artifacts/ch2_life/field_over_time.png): the pool's storing
share (gates >= 21 bars old) oscillates 0.65 → 0.78 → 0.65 four times a
year, every year — the field charges between reporting seasons and
discharges through them; the releasing share spikes at each discharge and
at the crises. The kernel was told nothing about quarters.

FIELD STATE, causal, all from the kernel's readings over the pool:
  storing(t)     share of tradeable names with gate age >= 21
  phase          CHARGING if storing(t) > storing(t-20), else DISCHARGING
  releasing(t)   share whose gate ended that day; HI/LO vs trailing 252
  polarity       the 20-day median of the daily share of releases whose
                 boundary bar closed UP (L0 signed dF): UP if > 0.5 else DOWN
ARMS (governance over the field's phase and polarity, nothing single):
  P1 charging            P2 discharging
  P3 discharging & polarity DOWN     P4 discharging & polarity UP
  P5 charging & polarity DOWN        P6 charging & polarity UP
  P7 discharging & releasing HI & polarity DOWN   (the field-wide down-release inside a discharge)
  P8 charging & releasing LO         (deep in the quiet: charge with no release)
HOLD 20; one position per name; tradeable only. PER YEAR vs the null.
PASS BAR: WR >= null + 3 points in 5 of 6 years AND mean better in 5 of 6.
OUTPUT: artifacts/ch4_uf/ch2_l5_field_phase.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
HOLD = 20
OUT = ROOT / "artifacts" / "ch4_uf" / "ch2_l5_field_phase.json"


def positions(g, cond):
    idx = np.where(cond)[0]; taken, last_exit = [], -1
    for i in idx:
        if i <= last_exit: continue
        taken.append(i); last_exit = i + HOLD
    return g.iloc[taken]


def main():
    ev = pd.read_parquet(ROOT / "artifacts" / "ch4_uf" / "ch2_particle_days_B.parquet")
    st = pd.read_csv(ROOT / "artifacts" / "ch2_life" / "field_state_daily.csv", index_col=0)
    tr = ev[ev.tradeable]
    storing = tr.groupby("date").age.apply(lambda a: float((a >= 21).mean()))
    fs = pd.DataFrame({"storing": storing}).join(st[["releasing", "rel_up_val"]])
    fs["phase"] = np.where(fs.storing > fs.storing.shift(20), "CHARGING", "DISCHARGING")
    fs.loc[fs.storing.shift(20).isna(), "phase"] = None
    fs["polarity"] = np.where(fs.rel_up_val.rolling(20, min_periods=10).median() > 0.5, "UP", "DOWN")
    fs.loc[fs.rel_up_val.rolling(20, min_periods=10).median().isna(), "polarity"] = None
    fs = fs.dropna(subset=["phase", "polarity", "releasing"])
    print("field days:", len(fs)); print(fs.groupby(["phase", "polarity"]).size().to_string())
    ev = ev.merge(fs.reset_index().rename(columns={"index": "date"})[["date", "phase", "polarity", "releasing"]], on="date", how="inner")
    ev = ev[ev.r20.notna()].sort_values(["symbol", "date"]).reset_index(drop=True); ev["year"] = ev.date.str[:4]
    T = ev.tradeable.values; ch = (ev.phase == "CHARGING").values; dn = (ev.polarity == "DOWN").values
    rh = (ev.releasing == "HI").values; rl = (ev.releasing == "LO").values
    arms = {"N0 every tradeable day": T, "P1 charging": T & ch, "P2 discharging": T & ~ch,
            "P3 discharging & polarity DOWN": T & ~ch & dn, "P4 discharging & polarity UP": T & ~ch & ~dn,
            "P5 charging & polarity DOWN": T & ch & dn, "P6 charging & polarity UP": T & ch & ~dn,
            "P7 discharging & releasing HI & polarity DOWN": T & ~ch & rh & dn, "P8 charging & releasing LO": T & ch & rl}
    res = {"declared": "field state, phase, polarity, arms, per-year report and pass bar in the docstring before results", "arms": {}}
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
        print(f"[phase] {name}: years WR >= null+3: {wr_ok}/6, mean > null: {mean_ok}/6, PASS={res['arms'][name]['PASS']}")
    fs.to_csv(ROOT / "artifacts" / "ch2_life" / "field_phase_daily.csv")
    json.dump(res, open(OUT, "w"), indent=1); print("filed:", OUT)


if __name__ == "__main__":
    main()
