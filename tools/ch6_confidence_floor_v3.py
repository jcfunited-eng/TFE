"""CONFIDENCE FLOOR v3 — the JOINT TUPLE GEOMETRY of the pulses that
came back down. Joseph's correction 2026-08-21: read the tuple as one
shape — D_k direction, Rev_k as a first-class state change, U*
instability read AGAINST support (S_UF) and resonance (URF), B_k
carry filling or exhausting — not three facts counted separately.

METHOD GATE:
1. L0-L4 OUTPUTS: D_k, Rev_k, U_star_k, B_k, S_UF, URF per reading
   (six of the nine instruments; M/C/P are not exported by the
   running chain — declared missing, not faked). Price only as field
   position (same pulse frame as v2).
2. RESOLUTION: 5 readings/session, year lanes.
3. OBJECT: the joint signature at the session the fall begins — six
   coordinates read together, each from the chain's own signs or
   self-referenced comparisons (no fitted thresholds):
     D: majority sign of D_k on the distribution session (+/-)
     R: any Rev_k fired on that session (0/1)
     U: U* at that close rising/falling vs prior session close
     S: S_UF at that close above/below its own trailing 22-session
        median (support viable vs weak)
     Q: URF at that close rising/falling vs prior session close
        (resonance reinforcing or fading)
     B: B_k at that close vs at the spike top (carry filling/draining)
   Frequencies of COMPLETED vs REFUTED per joint signature.
4. L5 SEPARATE: operating companies only; no other governance.
5. SEEN FIRST: v2's 1,292 pulse endings; the five trainers. Pulse
   frame constants identical to v2, declared there. Derive = first
   half by entry date, confirm = second half, frozen. Spectrum
   reported whole — no cell dropped for being inconvenient.
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
       "ch6_confidence_floor_v3.json")
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
    REV = lf["Rev_k"].to_numpy(float)
    US = lf["U_star_k"].to_numpy(float)
    B = lf["B_k"].to_numpy(float)
    dates = lf["date"].to_numpy()
    se = [i for i in range(len(lf) - 1) if dates[i] != dates[i + 1]]
    se.append(len(lf) - 1)
    sc = c[se]
    s_suf = suf[se]
    s_urf = urf[se]
    s_us = US[se]
    s_b = B[se]
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
        t0, t1 = se[e - 1] + 1, se[e] + 1
        sig = "".join([
            "D-" if (D[t0:t1] < 0).sum() >= 3 else "D+",
            " R1" if REV[t0:t1].sum() > 0 else " R0",
            " U^" if s_us[e] > s_us[e - 1] else " Uv",
            " S^" if s_suf[e] > float(np.median(s_suf[e - 22:e])) else " Sv",
            " Q^" if s_urf[e] > s_urf[e - 1] else " Qv",
            " B^" if s_b[e] > s_b[k] else " Bv",
        ])
        outcome, age = "EXPIRED", 25
        for j2 in range(ei + 1, min(ei + 26, n)):
            if sc[j2] <= base:
                outcome, age = "COMPLETED", j2 - ei
                break
            if sc[j2] > top:
                outcome, age = "REFUTED", j2 - ei
                break
        harvest = 100 * (entry - sc[min(ei + age, n - 1)]) / entry
        out.append((sym, str(dates[se[ei]])[:10], sig, outcome, age,
                    round(harvest, 2)))
        k = min(ei + age, n - 2) + 1
    return out


files = sorted(os.path.join(LANES, f) for f in os.listdir(LANES)
               if f.endswith(".parquet"))
rows = []
with Pool(8) as p:
    for r in p.imap_unordered(one, files, chunksize=16):
        rows.extend(r)
ev = pd.DataFrame(rows, columns=["sym", "entry_date", "sig", "outcome",
                                 "age", "harvest_pct"])
ev = ev.sort_values("entry_date")
mid = ev["entry_date"].iloc[len(ev) // 2] if len(ev) else ""
halves = {"derive": ev[ev.entry_date < mid],
          "confirm": ev[ev.entry_date >= mid]}
res = {"pulses": int(len(ev)), "split_date": mid,
       "base_rates": {h: {"n": int(len(d)),
                          "completed": round(float((d.outcome == "COMPLETED").mean()), 3),
                          "refuted": round(float((d.outcome == "REFUTED").mean()), 3)}
                      for h, d in halves.items()},
       "signatures": {}}
for sig in sorted(ev.sig.unique()):
    entry = {}
    keep = False
    for h, d in halves.items():
        g = d[d.sig == sig]
        entry[h] = {"n": int(len(g))}
        if len(g) >= 10:
            entry[h].update({
                "completed": round(float((g.outcome == "COMPLETED").mean()), 3),
                "refuted": round(float((g.outcome == "REFUTED").mean()), 3),
                "mean_harvest_pct": round(float(g.harvest_pct.mean()), 2)})
            keep = True
    if keep:
        res["signatures"][sig] = entry
json.dump(res, open(OUT, "w"), indent=1)
ev.to_parquet(OUT.replace(".json", "_pulses.parquet"))
print(json.dumps(res, indent=1))
print("filed:", OUT)
