"""THE BEND AXIS — v4, declared 2026-08-21 before running.

Joseph: "try it." The question the flat field could not answer:
when resonance turns UP on the fall's first day, is it ACCELERATING
(the crowd reloading) or BENDING OVER (the turn dying)? Same for the
field itself.

METHOD GATE:
1. L0-L4 OUTPUTS: URF trajectory (exported) for the resonance bend;
   session closes as the field position for the field bend; the v3
   frame's D/Rev/U*/S_UF/B for context. M_k itself is NOT exported
   by the running chain — this is the bend of the exported
   trajectories, named as such, not a fake M_k.
2. RESOLUTION: session closes over the year lanes (the frame where
   the reload signature was found).
3. OBJECT: second differences at the entry session e —
     resonance bend:  URF_e - 2*URF_(e-1) + URF_(e-2)
     field bend:      (c_e - 2*c_(e-1) + c_(e-2)) / c_(e-2)
   Read as signs (accelerating / bending over), applied to:
     (a) the whole entered population,
     (b) entries with resonance rising (Q^),
     (c) the reload cell (U^ Sv Q^).
   DECLARED HYPOTHESIS: within Q^, accelerating resonance -> refuted;
   bending-over resonance -> the turn dies, completion recovers.
4. L5 SEPARATE: operating companies only.
5. SEEN FIRST: the v3 spectrum (filed, committed) and the reload
   receipt. Constants unchanged from v2/v3. Both halves, all cells,
   one shot.
"""
import json
import os
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, "/workspaces/Tao_Financial_Engine")
LANES = "/workspaces/Tao_Financial_Engine/artifacts/ch6_harvest/year_lanes"
OUT = ("/workspaces/Tao_Financial_Engine/artifacts/ch6_harvest/"
       "ch6_bend_axis_v4.json")
RPS = 5
TT = json.load(open("/workspaces/Tao_Financial_Engine/artifacts/"
                    "ch6_harvest/ticker_types.json"))
OP = {s for s, t in TT.items() if t in ("CS", "ADRC")}
COLS = ["date", "close", "URF", "S_UF", "extinction", "ignition",
        "D_k", "Rev_k", "U_star_k", "B_k"]


def one(path):
    sym = os.path.basename(path)[:-8]
    if sym not in OP:
        return []
    lf = pd.read_parquet(path, columns=COLS)
    if len(lf) < 60 * RPS:
        return []
    c = lf["close"].to_numpy(float)
    urf = lf["URF"].to_numpy(float)
    suf = lf["S_UF"].to_numpy(float)
    ext = lf["extinction"].to_numpy(float)
    ign = lf["ignition"].to_numpy(float)
    D = lf["D_k"].to_numpy(float)
    US = lf["U_star_k"].to_numpy(float)
    dates = lf["date"].to_numpy()
    se = [i for i in range(len(lf) - 1) if dates[i] != dates[i + 1]]
    se.append(len(lf) - 1)
    sc = c[se]
    s_suf = suf[se]
    s_urf = urf[se]
    s_us = US[se]
    n = len(se)
    out = []
    k = 22
    while k < n - 2:
        gain = 100 * (sc[k] / sc[k - 1] - 1) if sc[k - 1] > 0 else 0
        base = float(np.median(sc[k - 20:k]))
        if gain < 8 or base <= 0 or sc[k] < 1:
            k += 1
            continue
        top = float(sc[k])
        if 100 * (top / base - 1) < 15:
            k += 1
            continue
        entered, charge = None, False
        for j in range(k + 1, min(k + 11, n)):
            t0, t1 = se[j - 1] + 1, se[j] + 1
            if sc[j] > top or ign[t0:t1].sum() > 0:
                charge = True
                break
            down = sc[j] < sc[j - 1]
            damage = (ext[t0:t1].sum() > 0
                      or (urf[t0:t1] <= 0).sum() > 0
                      or (D[t0:t1] < 0).sum() >= 3)
            if down and damage:
                entered = j
                break
        if charge or entered is None or entered + 1 >= n:
            k = max(k + 1, j)
            continue
        e = entered
        ei = e + 1
        entry = sc[ei]
        if entry <= 0 or e < 23:
            k = ei
            continue
        q_up = s_urf[e] > s_urf[e - 1]
        res_bend = s_urf[e] - 2 * s_urf[e - 1] + s_urf[e - 2]
        fld_bend = (sc[e] - 2 * sc[e - 1] + sc[e - 2]) / sc[e - 2] \
            if sc[e - 2] > 0 else 0.0
        reload_cell = (s_us[e] > s_us[e - 1]
                       and s_suf[e] < float(np.median(s_suf[e - 22:e]))
                       and q_up)
        outcome, age = "EXPIRED", 25
        for j2 in range(ei + 1, min(ei + 26, n)):
            if sc[j2] <= base:
                outcome, age = "COMPLETED", j2 - ei
                break
            if sc[j2] > top:
                outcome, age = "REFUTED", j2 - ei
                break
        harvest = 100 * (entry - sc[min(ei + age, n - 1)]) / entry
        out.append((sym, str(dates[se[ei]])[:10], int(q_up),
                    1 if res_bend > 0 else 0, 1 if fld_bend > 0 else 0,
                    int(reload_cell), outcome, round(harvest, 2)))
        k = min(ei + age, n - 2) + 1
    return out


files = sorted(os.path.join(LANES, f) for f in os.listdir(LANES)
               if f.endswith(".parquet"))
rows = []
with Pool(8) as p:
    for r in p.imap_unordered(one, files, chunksize=16):
        rows.extend(r)
ev = pd.DataFrame(rows, columns=["sym", "entry_date", "q_up",
                                 "res_accel", "fld_accel",
                                 "reload", "outcome", "harvest_pct"])
ev = ev.sort_values("entry_date")
mid = ev["entry_date"].iloc[len(ev) // 2] if len(ev) else ""
halves = {"derive": ev[ev.entry_date < mid],
          "confirm": ev[ev.entry_date >= mid]}


def cell(df):
    if len(df) < 10:
        return {"n": int(len(df))}
    return {"n": int(len(df)),
            "completed": round(float((df.outcome == "COMPLETED").mean()), 3),
            "refuted": round(float((df.outcome == "REFUTED").mean()), 3),
            "mean_harvest_pct": round(float(df.harvest_pct.mean()), 2)}


res = {"pulses": int(len(ev)), "split_date": mid}
for h, d in halves.items():
    res[h] = {
        "all": cell(d),
        "Q_up__res_accelerating": cell(d[(d.q_up == 1) & (d.res_accel == 1)]),
        "Q_up__res_bending_over": cell(d[(d.q_up == 1) & (d.res_accel == 0)]),
        "Q_down": cell(d[d.q_up == 0]),
        "field_accel_up": cell(d[d.fld_accel == 1]),
        "field_bending_down": cell(d[d.fld_accel == 0]),
        "reload__res_accelerating": cell(d[(d.reload == 1) & (d.res_accel == 1)]),
        "reload__res_bending_over": cell(d[(d.reload == 1) & (d.res_accel == 0)]),
        "Qup_accel__field_bend_dn": cell(d[(d.q_up == 1) & (d.res_accel == 1)
                                           & (d.fld_accel == 0)]),
        "Qup_bendover__field_bend_dn": cell(d[(d.q_up == 1) & (d.res_accel == 0)
                                              & (d.fld_accel == 0)]),
    }
json.dump(res, open(OUT, "w"), indent=1)
ev.to_parquet(OUT.replace(".json", "_pulses.parquet"))
print(json.dumps(res, indent=1))
print("filed:", OUT)
