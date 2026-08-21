"""CONFIDENCE FLOOR STUDY v2 — pulses followed whole, discrete
outcomes, frequencies over exact structures, derive/confirm halves.
Declared through the Method Gate 2026-08-21 BEFORE running; v1 is
retracted (it entered on charging pumps, observed past completion,
and judged by pooled scalar means — filed receipts of the failure at
ch6_confidence_floor_study.json, kept as the record of the mistake).

1. L0-L4 OUTPUTS: ignition, extinction, URF, S_UF, D_k per reading.
   Price only as field position (spike top, pre-spike base, closes).
2. RESOLUTION: 5 readings/session, year lanes (where the shape lives).
3. OBJECT: the PULSE as one life: spike session (close gain >=8%,
   top >=15% over the 20-session median base) -> then either
   RE-IGNITES (ignition or a higher close before any down structure:
   the charging class, never entered) or DISTRIBUTION BEGINS (first
   session closing below the prior close WITH damage that session: a
   death, a dead-channel reading, or D_k negative on >=3 of its 5
   readings). Entry = next session close after distribution begins.
   Each entered pulse ends in exactly ONE outcome within 25 sessions:
     COMPLETED - a session close at or below the pre-spike base
     REFUTED   - a session close above the spike top
     EXPIRED   - neither within 25 sessions
4. L5 SEPARATE: no governance laws simulated; population is operating
   companies only (identity is L5 and is applied).
5. SEEN FIRST: the five 2026-08-20 winners' kernel facts, the 359
   contact sheets, the v1 wreckage. Constants declared once above;
   no sweeps; both halves reported whatever they say.
States at entry (exact, discrete, no thresholds beyond the chain's
own signs): (deaths_since_spike: 0 / 1 / 2+) x (dead_reading_seen:
0/1) x (D-majority sign on distribution day: -/+). Frequencies of
COMPLETED vs REFUTED per state, derive = first half of the year's
entries, confirm = second half, frozen. Null = unconditional rates.
Also filed: sessions from entry to completion (the honest clock).
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
       "ch6_confidence_floor_v2.json")
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
    ext = lf["extinction"].to_numpy(float)
    ign = lf["ignition"].to_numpy(float)
    D = lf["D_k"].to_numpy(float)
    dates = lf["date"].to_numpy()
    se = [i for i in range(len(lf) - 1) if dates[i] != dates[i + 1]]
    se.append(len(lf) - 1)
    sc = c[se]
    n = len(se)
    pulses = []
    k = 21
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
        # follow THIS pulse forward: re-ignite or distribution begins
        entered = None
        charge = False
        for j in range(k + 1, min(k + 11, n)):
            t0, t1 = se[j - 1] + 1, se[j] + 1
            if sc[j] > top or ign[t0:t1].sum() > 0:
                charge = True   # still charging: never entered
                break
            down = sc[j] < sc[j - 1]
            damage = (ext[t0:t1].sum() > 0
                      or (urf[t0:t1] <= 0).sum() > 0
                      or (D[t0:t1] < 0).sum() >= 3)
            if down and damage:
                entered = j
                break
        if charge or entered is None or entered + 1 >= n:
            k += 1 if charge is False else (j - k)
            k = max(k, j)
            continue
        ei = entered + 1          # enter next session close
        entry = sc[ei]
        if entry <= 0:
            k = ei
            continue
        # state at entry (exact discrete signature)
        a, b = se[k] + 1, se[entered] + 1
        deaths = int(ext[a:b].sum())
        deaths_c = "0" if deaths == 0 else ("1" if deaths == 1 else "2+")
        dead_read = "1" if (urf[a:b] <= 0).sum() > 0 else "0"
        t0, t1 = se[entered - 1] + 1, se[entered] + 1
        dsign = "-" if (D[t0:t1] < 0).sum() >= 3 else "+"
        state = f"d{deaths_c}|dr{dead_read}|D{dsign}"
        # one discrete outcome
        outcome, age = "EXPIRED", 25
        for j in range(ei + 1, min(ei + 26, n)):
            if sc[j] <= base:
                outcome, age = "COMPLETED", j - ei
                break
            if sc[j] > top:
                outcome, age = "REFUTED", j - ei
                break
        harvest = 100 * (entry - sc[min(ei + age, n - 1)]) / entry
        pulses.append((sym, str(dates[se[ei]])[:10], state, outcome,
                       age, round(harvest, 2)))
        k = min(ei + age, n - 2) + 1
    return pulses


files = sorted(os.path.join(LANES, f) for f in os.listdir(LANES)
               if f.endswith(".parquet"))
rows = []
with Pool(8) as p:
    for r in p.imap_unordered(one, files, chunksize=16):
        rows.extend(r)
ev = pd.DataFrame(rows, columns=["sym", "entry_date", "state", "outcome",
                                 "age", "harvest_pct"])
ev = ev.sort_values("entry_date")
mid = ev["entry_date"].iloc[len(ev) // 2] if len(ev) else ""
res = {"pulses_entered": int(len(ev)), "split_date": mid}
for half, df in [("derive", ev[ev.entry_date < mid]),
                 ("confirm", ev[ev.entry_date >= mid])]:
    h = {"n": int(len(df))}
    if len(df):
        h["outcomes"] = {k: int(v) for k, v in
                         df.outcome.value_counts().items()}
        h["completed_rate"] = round(
            float((df.outcome == "COMPLETED").mean()), 3)
        h["refuted_rate"] = round(
            float((df.outcome == "REFUTED").mean()), 3)
        h["mean_harvest_pct_all"] = round(float(df.harvest_pct.mean()), 2)
        comp = df[df.outcome == "COMPLETED"]
        h["sessions_to_completion"] = {
            "p25": int(comp.age.quantile(.25)) if len(comp) else None,
            "p50": int(comp.age.median()) if len(comp) else None,
            "p75": int(comp.age.quantile(.75)) if len(comp) else None,
            "p90": int(comp.age.quantile(.90)) if len(comp) else None}
        h["states"] = {}
        for st, g in df.groupby("state"):
            if len(g) >= 8:
                h["states"][st] = {
                    "n": int(len(g)),
                    "completed": round(float((g.outcome == "COMPLETED").mean()), 3),
                    "refuted": round(float((g.outcome == "REFUTED").mean()), 3),
                    "mean_harvest_pct": round(float(g.harvest_pct.mean()), 2)}
    res[half] = h
json.dump(res, open(OUT, "w"), indent=1)
ev.to_parquet(OUT.replace(".json", "_pulses.parquet"))
print(json.dumps(res, indent=1))
print("filed:", OUT)
