"""THE STATE ATLAS v1 — the whole field's state words and where they
flow. Declared 2026-08-21 before running. Joseph's nine-gauge roles
(reposted verbatim in-session) are the alphabet's constitution.

METHOD GATE:
1. L0-L4 OUTPUTS: D_k, Rev_k, U_star_k, B_k, S_UF, URF per reading;
   field bend as the declared session-close proxy for M_k (the chain
   does not export M/C/P — absent, not faked). Flow (volume) enters
   only as the metadata channel (down-side concentration).
2. RESOLUTION: session closes over the year lanes, gauges read from
   the session's five readings.
3. OBJECT: the joint state word per life per session, each gauge in
   its stated role:
     D  direction: majority sign of D_k over the session: + / 0 / -
     M  bend RELATIVE to direction: field bend sign agrees with D
        (CONT) or opposes it (BACK); D neutral -> raw bend up/dn
     R  reversal fired this session: 0 / 1 (first-class state)
     U  instability direction: rising / falling vs prior session
     B  fuel trend: B_k now vs 5 sessions back: filling / draining
     S  support: viable / weak vs own trailing 22-session median
     Q  resonance: reinforced / isolated vs own trailing 22-session
        median of URF
     F  flow side: dollar-flow on down readings > up readings this
        session (exit-heavy) or not (metadata channel)
   For every state word: population count and forward event
   frequencies — next session and within 5 sessions: close +5% or
   more (UP5), close -5% or less (DN5), any ignition (IGN5), any
   death (EXT5). Frequencies over exact discrete structures; no
   pooled scalar outcomes.
4. L5 SEPARATE: operating companies only; nothing else.
5. SEEN FIRST: the v2-v4 receipts, the reload, the bend pocket, the
   359 contact sheets. Alphabet declared above once; both halves by
   calendar (first/second half of each life's sessions assigned by
   date vs the global split); full spectrum filed, nothing dropped.
One shot.
"""
import json
import os
import sys
from collections import defaultdict
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, "/workspaces/Tao_Financial_Engine")
LANES = "/workspaces/Tao_Financial_Engine/artifacts/ch6_harvest/year_lanes"
OUT = ("/workspaces/Tao_Financial_Engine/artifacts/ch6_harvest/"
       "ch6_state_atlas_v1.json")
SPLIT = "2026-03-12"  # the standing derive/confirm boundary
TT = json.load(open("/workspaces/Tao_Financial_Engine/artifacts/"
                    "ch6_harvest/ticker_types.json"))
OP = {s for s, t in TT.items() if t in ("CS", "ADRC")}
COLS = ["date", "close", "volume", "D_k", "Rev_k", "U_star_k", "B_k",
        "S_UF", "URF", "ignition", "extinction"]


def one(path):
    sym = os.path.basename(path)[:-8]
    if sym not in OP:
        return []
    lf = pd.read_parquet(path, columns=COLS)
    if len(lf) < 150:
        return []
    c = lf["close"].to_numpy(float)
    v = lf["volume"].to_numpy(float)
    D = lf["D_k"].to_numpy(float)
    REV = lf["Rev_k"].to_numpy(float)
    US = lf["U_star_k"].to_numpy(float)
    B = lf["B_k"].to_numpy(float)
    SUF = lf["S_UF"].to_numpy(float)
    URF = lf["URF"].to_numpy(float)
    IGN = lf["ignition"].to_numpy(float)
    EXT = lf["extinction"].to_numpy(float)
    dates = lf["date"].to_numpy()
    se = [i for i in range(len(lf) - 1) if dates[i] != dates[i + 1]]
    se.append(len(lf) - 1)
    n = len(se)
    if n < 40:
        return []
    sc = c[se]
    s_us = US[se]
    s_b = B[se]
    s_suf = SUF[se]
    s_urf = URF[se]
    rows = []
    for j in range(23, n - 5):
        t0, t1 = se[j - 1] + 1, se[j] + 1
        dn = int((D[t0:t1] < 0).sum())
        up = int((D[t0:t1] > 0).sum())
        d = "-" if dn >= 3 else ("+" if up >= 3 else "0")
        bend = sc[j] - 2 * sc[j - 1] + sc[j - 2]
        if d == "+":
            m = "CONT" if bend > 0 else "BACK"
        elif d == "-":
            m = "CONT" if bend < 0 else "BACK"
        else:
            m = "up" if bend > 0 else "dn"
        r = "1" if REV[t0:t1].sum() > 0 else "0"
        u = "^" if s_us[j] > s_us[j - 1] else "v"
        b = "fill" if s_b[j] > s_b[j - 5] else "drain"
        s = "via" if s_suf[j] > float(np.median(s_suf[j - 22:j])) else "weak"
        q = "rein" if s_urf[j] > float(np.median(s_urf[j - 22:j])) else "iso"
        flow = c[t0:t1] * v[t0:t1]
        dmask = D[t0:t1] < 0
        f = "exit" if flow[dmask].sum() > flow[~dmask].sum() else "calm"
        word = f"D{d} M{m} R{r} U{u} B{b} S{s} Q{q} F{f}"
        fwd5 = sc[j + 1:j + 6]
        up5 = int((100 * (fwd5.max() / sc[j] - 1)) >= 5)
        dn5 = int((100 * (fwd5.min() / sc[j] - 1)) <= -5)
        t5 = se[min(j + 5, n - 1)] + 1
        ign5 = int(IGN[t1:t5].sum() > 0)
        ext5 = int(EXT[t1:t5].sum() > 0)
        half = "derive" if str(dates[se[j]])[:10] < SPLIT else "confirm"
        rows.append((word, half, up5, dn5, ign5, ext5))
    return rows


files = sorted(os.path.join(LANES, f) for f in os.listdir(LANES)
               if f.endswith(".parquet"))
agg = defaultdict(lambda: np.zeros(5, dtype=np.int64))
with Pool(8) as p:
    for rows in p.imap_unordered(one, files, chunksize=16):
        for word, half, u5, d5, i5, e5 in rows:
            agg[(word, half)] += np.array([1, u5, d5, i5, e5])
res = {"session_words": 0, "split_date": SPLIT, "atlas": {}}
words = sorted({w for w, _ in agg})
for w in words:
    entry = {}
    for half in ("derive", "confirm"):
        a = agg.get((w, half))
        if a is None:
            continue
        n_, u5, d5, i5, e5 = (int(x) for x in a)
        res["session_words"] += n_
        entry[half] = {"n": n_, "UP5": round(u5 / n_, 3),
                       "DN5": round(d5 / n_, 3),
                       "IGN5": round(i5 / n_, 3),
                       "EXT5": round(e5 / n_, 3)}
    res["atlas"][w] = entry
json.dump(res, open(OUT, "w"), indent=1)
print("state words observed:", res["session_words"],
      "distinct:", len(res["atlas"]))
print("filed:", OUT)
