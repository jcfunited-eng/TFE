"""THE CONFIDENCE FLOOR STUDY — declared through the Method Gate
(docs/CH6_METHOD_GATE.md) BEFORE running, 2026-08-21.

1. L0-L4 OUTPUTS read: ignition, extinction, URF, S_UF, D_k from the
   year lanes. Price only as field position (spike top, base, marks).
2. RESOLUTION: 5 readings/session over the ~250-session year window —
   the resolution where the trainer shape was seen and filed.
3. OBJECT: the post-entry recovery boundary of the harvested class —
   the structural state after which the fall no longer resumes. Four
   declared markers, measured per open ride at every session:
     M1 ignition fired since entry (the chain confirms the move)
     M2 healed: no deaths in last 5 sessions AND URF>=0.55 AND
        S_UF>=0.85 at the session close
     M3 push flip: D_k positive on >=8 of the last 10 readings
     M4 price closed above the spike top we entered against
   Measurement: forward 5-session SHORT return from each session,
   conditioned on each marker (and the pair M1&M2) being present vs
   absent. The floor is the condition whose presence flips forward
   expectancy decisively against holding.
4. L5 SEPARATE: no governance here — pure measurement; the entry
   population is the TRAINER SHAPE declared from the five banked
   wins of 2026-08-20 (ch6_trainers.json): one-session close gain
   >=8% within the last 8 sessions, spike top >=15% over the
   20-session median base, ZERO ignitions from spike through entry,
   S_UF>=0.75, 0.40<=URF<=0.65 at the decision close; enter at the
   NEXT session close (honest availability). Rides observed 25
   sessions, no exits — states are measured, not traded.
5. SEEN FIRST: the five winners' kernel facts (filed raw), the 359
   contact sheets, yesterday's live receipts. Constants above are
   declared once, from the trainers; no sweeps, best-of nothing.
One shot."""
import json
import os
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, "/workspaces/Tao_Financial_Engine")
LANES = "/workspaces/Tao_Financial_Engine/artifacts/ch6_harvest/year_lanes"
OUT = ("/workspaces/Tao_Financial_Engine/artifacts/ch6_harvest/"
       "ch6_confidence_floor_study.json")
RPS = 5
TT = json.load(open("/workspaces/Tao_Financial_Engine/artifacts/"
                    "ch6_harvest/ticker_types.json"))
OP = {s for s, t in TT.items() if t in ("CS", "ADRC")}


def one(path):
    sym = os.path.basename(path)[:-8]
    if sym not in OP:
        return []
    lf = pd.read_parquet(path, columns=["date", "close", "URF", "S_UF",
                                        "extinction", "ignition", "D_k"])
    if len(lf) < 60 * RPS:
        return []
    c = lf["close"].to_numpy(float)
    urf = lf["URF"].to_numpy(float)
    suf = lf["S_UF"].to_numpy(float)
    ext = lf["extinction"].to_numpy(float)
    ign = lf["ignition"].to_numpy(float)
    D = lf["D_k"].to_numpy(float)
    dates = lf["date"].to_numpy()
    se = [i for i in range(len(lf) - 1) if dates[i] != dates[i + 1]]
    se.append(len(lf) - 1)
    sc = c[se]  # session closes
    rows = []
    si = 30
    while si < len(se) - 7:
        # spike: best 1-session gain in last 8 sessions
        lo = max(1, si - 8)
        gains = [(100 * (sc[k] / sc[k - 1] - 1), k) for k in
                 range(lo, si + 1)]
        g, k = max(gains)
        base = float(np.median(sc[max(0, k - 20):k]))
        if g < 8 or base <= 0 or sc[k] < 1:
            si += 1
            continue
        top = float(sc[k])
        if 100 * (top / base - 1) < 15:
            si += 1
            continue
        t = se[si]
        if ign[se[k] - RPS:t + 1].sum() > 0:  # zero ignitions since spike
            si += 1
            continue
        if suf[t] < 0.75 or not (0.40 <= urf[t] <= 0.65):
            si += 1
            continue
        ei = si + 1  # enter next session close
        entry = sc[ei]
        if entry <= 0:
            si += 1
            continue
        # observe 25 sessions; at each, markers + forward 5-session move
        for sj in range(ei + 1, min(ei + 26, len(se) - 5)):
            tj = se[sj]
            m1 = 1 if ign[se[ei]:tj + 1].sum() > 0 else 0
            m2 = 1 if (ext[tj - 5 * RPS + 1:tj + 1].sum() == 0
                       and urf[tj] >= 0.55 and suf[tj] >= 0.85) else 0
            m3 = 1 if (D[tj - 10:tj + 1] > 0).sum() >= 8 else 0
            m4 = 1 if sc[sj] > top else 0
            fwd_short = 100 * (sc[sj] - sc[sj + 5]) / sc[sj]
            open_short = 100 * (entry - sc[sj]) / entry
            rows.append((sym, str(dates[se[ei]]), sj - ei, m1, m2, m3,
                         m4, round(fwd_short, 3), round(open_short, 3)))
        si = sj + 1 if rows else si + 1
    return rows


files = sorted(os.path.join(LANES, f) for f in os.listdir(LANES)
               if f.endswith(".parquet"))
rows = []
with Pool(8) as p:
    for r in p.imap_unordered(one, files, chunksize=16):
        rows.extend(r)
ev = pd.DataFrame(rows, columns=["sym", "entry_date", "age", "m1", "m2",
                                 "m3", "m4", "fwd5_short", "open_short"])
res = {"rides": int(ev.groupby(["sym", "entry_date"]).ngroups),
       "observations": int(len(ev))}
for name, mask in [
        ("M1_ignition", ev.m1 == 1), ("M2_healed", ev.m2 == 1),
        ("M3_push_flip", ev.m3 == 1), ("M4_above_spike_top", ev.m4 == 1),
        ("M1_and_M2", (ev.m1 == 1) & (ev.m2 == 1)),
        ("M1_and_M4", (ev.m1 == 1) & (ev.m4 == 1)),
        ("none_of_them", (ev.m1 + ev.m2 + ev.m3 + ev.m4) == 0)]:
    a, b = ev[mask], ev[~mask]
    res[name] = {
        "present_n": int(len(a)),
        "present_fwd5_short_mean": round(float(a.fwd5_short.mean()), 2)
        if len(a) else None,
        "absent_fwd5_short_mean": round(float(b.fwd5_short.mean()), 2)
        if len(b) else None,
        "present_win_rate": round(float((a.fwd5_short > 0).mean()), 3)
        if len(a) else None,
    }
json.dump(res, open(OUT, "w"), indent=1)
ev.to_parquet(OUT.replace(".json", "_obs.parquet"))
print(json.dumps(res, indent=1))
print("filed:", OUT)
