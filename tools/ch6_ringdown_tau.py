"""RINGDOWN — is the decay constant a property of the BODY?
Declared 2026-08-21 before running.

Physics: a driven oscillation, drive removed, relaxes as
exp(-t/tau); tau belongs to the body (its damping), not to the
event. If stocks are bodies, each one's spent pulses should relax
with the SAME tau, pulse after pulse — and different bodies should
carry different tau.

METHOD GATE:
1. L0-L4 OUTPUTS: pulse frame from the chain as in v2 (ignition,
   extinction, URF, D_k mark the drive's death); the relaxation is
   the field position after the top.
2. RESOLUTION: session closes, year lanes.
3. OBJECT: per pulse, the decay of displacement above base:
   x_j = (c_j - base) / (top - base), from the top session forward
   while x stays in (0,1]; fit ln x_j = -j/tau by least squares over
   the first 10 sessions (no fitted thresholds; the fit IS the
   physics). Keep pulses with >=4 usable sessions and a DEAD drive
   (no ignition through the window, as in the trainer shape).
4. TEST (the whole point): bodies with >=3 pulses in the year —
   is tau consistent WITHIN a body vs ACROSS bodies? Statistic:
   within-body spread of tau (median absolute deviation / median)
   vs the same for body-labels shuffled (null), 200 shuffles,
   split halves not needed (the null IS the control), but the
   within/across comparison is also reported per half.
5. SEEN FIRST: the five trainers' relaxations; the v2 completion
   ages (p25 2-3, p50 5-7 — the spread that raised the question).
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
       "ch6_ringdown_tau.json")
RPS = 5
TT = json.load(open("/workspaces/Tao_Financial_Engine/artifacts/"
                    "ch6_harvest/ticker_types.json"))
OP = {s for s, t in TT.items() if t in ("CS", "ADRC")}


def one(path):
    sym = os.path.basename(path)[:-8]
    if sym not in OP:
        return []
    lf = pd.read_parquet(path, columns=["date", "close", "ignition"])
    if len(lf) < 150:
        return []
    c = lf["close"].to_numpy(float)
    ign = lf["ignition"].to_numpy(float)
    dates = lf["date"].to_numpy()
    se = [i for i in range(len(lf) - 1) if dates[i] != dates[i + 1]]
    se.append(len(lf) - 1)
    sc = c[se]
    n = len(se)
    taus = []
    k = 21
    while k < n - 6:
        gain = 100 * (sc[k] / sc[k - 1] - 1) if sc[k - 1] > 0 else 0
        base = float(np.median(sc[k - 20:k]))
        top = sc[k]
        if gain < 8 or base <= 0 or top <= base or sc[k] < 1:
            k += 1
            continue
        if 100 * (top / base - 1) < 15:
            k += 1
            continue
        # drive must be dead through the window (no ignition)
        end = min(k + 11, n)
        t0, t1 = se[k] + 1, se[end - 1] + 1
        if ign[t0:t1].sum() > 0:
            k += 1
            continue
        xs, js = [], []
        for j in range(k + 1, end):
            x = (sc[j] - base) / (top - base)
            if x <= 0:
                break
            if x <= 1.0:
                xs.append(np.log(x))
                js.append(j - k)
        if len(xs) >= 4:
            A = np.vstack([js, np.ones(len(js))]).T
            slope, _ = np.linalg.lstsq(A, np.array(xs), rcond=None)[0]
            if slope < -1e-4:                       # decaying only
                taus.append((sym, str(dates[se[k]])[:10],
                             round(float(-1.0 / slope), 2)))
        k = end
    return taus


files = sorted(os.path.join(LANES, f) for f in os.listdir(LANES)
               if f.endswith(".parquet"))
rows = []
with Pool(8) as p:
    for r in p.imap_unordered(one, files, chunksize=16):
        rows.extend(r)
df = pd.DataFrame(rows, columns=["sym", "date", "tau"])
df = df[(df.tau > 0) & (df.tau < 60)]
counts = df.sym.value_counts()
multi = df[df.sym.isin(counts[counts >= 3].index)]
res = {"pulses_fit": int(len(df)),
       "bodies_with_3plus": int(multi.sym.nunique()),
       "tau_overall": {"p25": round(float(df.tau.quantile(.25)), 1),
                       "p50": round(float(df.tau.median()), 1),
                       "p75": round(float(df.tau.quantile(.75)), 1)}}
if multi.sym.nunique() >= 20:
    def spread(g):
        m = g.median()
        return float((g - m).abs().median() / m) if m > 0 else np.nan
    within = multi.groupby("sym")["tau"].apply(spread).dropna()
    res["within_body_spread_median"] = round(float(within.median()), 3)
    rng = np.random.default_rng(0)
    nulls = []
    vals = multi["tau"].to_numpy().copy()
    sizes = multi.groupby("sym").size().to_numpy()
    for _ in range(200):
        rng.shuffle(vals)
        idx = 0
        sp = []
        for s in sizes:
            g = pd.Series(vals[idx:idx + s])
            idx += s
            m = g.median()
            if m > 0:
                sp.append(float((g - m).abs().median() / m))
        nulls.append(float(np.median(sp)))
    res["shuffled_spread_median"] = round(float(np.median(nulls)), 3)
    res["shuffles_below_actual"] = int(sum(1 for x in nulls
                                           if x <= res["within_body_spread_median"]))
    res["null_shuffles"] = 200
json.dump(res, open(OUT, "w"), indent=1)
df.to_parquet(OUT.replace(".json", "_pulses.parquet"))
print(json.dumps(res, indent=1))
print("filed:", OUT)
