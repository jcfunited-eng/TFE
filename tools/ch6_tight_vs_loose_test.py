"""TIGHT vs LOOSE pick shapes under the engine's real banking rules,
plus the quiet-cut exit — declared 2026-08-28 BEFORE running.

METHOD GATE:
1. L0-L4 OUTPUTS: ignition, extinction, URF (dead readings) from the
   year lanes; price as field position only.
2. RESOLUTION: session closes, year lanes, operating companies.
3. OBJECTS:
   POPULATION A (TIGHT — the trainers' actual bounds): a single
   session close-gain >=8% standing >=15% over the 20-session median
   base, the spike within 8 sessions of the decision close, zero
   ignitions from spike through decision; enter next session close.
   POPULATION B (LOOSE — what the live readers did to ASAN/GTE/PTEN):
   close >=15% above its own close 20 sessions back, NO single-session
   >=8% jump in the last 8 sessions (the gradual climb), zero
   ignitions in the last 22 sessions; enter at the first down close.
   EXITS for both, the engine's own: bank at any session close with
   the short >= +2%; stop at -20%; out at the 5th session close.
   EXIT VARIANT (the proposed quiet-cut, tested on A only): in
   addition, cut at the next close if after 2 full sessions the tape
   shows ZERO deaths and ZERO dead-channel readings since entry AND
   the close sits at or above entry — the fall never began.
4. L5 SEPARATE: identity only (operating companies).
5. SEEN FIRST: the five live bleeders' tapes and readings (ASAN, GTE,
   PTEN, PHR, SSL), the six banked winners, the v2/v3 receipts.
Both halves by entry date; all dollars per $2,500 slice. One shot."""
import json
import os
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, "/workspaces/Tao_Financial_Engine")
LANES = "/workspaces/Tao_Financial_Engine/artifacts/ch6_harvest/year_lanes"
OUT = ("/workspaces/Tao_Financial_Engine/artifacts/ch6_harvest/"
       "ch6_tight_vs_loose.json")
RPS = 5
TT = json.load(open("/workspaces/Tao_Financial_Engine/artifacts/"
                    "ch6_harvest/ticker_types.json"))
OP = {s for s, t in TT.items() if t in ("CS", "ADRC")}


def run_exit(sc, ext_s, dead_s, ei, quiet_cut):
    """Engine exits from entry close ei; returns (pnl_pct, reason)."""
    entry = sc[ei]
    n = len(sc)
    for j in range(ei + 1, min(ei + 6, n)):
        gain = 100 * (entry - sc[j]) / entry
        if gain >= 2.0:
            return gain, "BANK"
        if gain <= -20.0:
            return gain, "STOP"
        if quiet_cut and j >= ei + 2:
            if (ext_s[ei + 1:j + 1].sum() == 0
                    and dead_s[ei + 1:j + 1].sum() == 0
                    and sc[j] >= entry):
                return gain, "QUIET_CUT"
    j = min(ei + 5, n - 1)
    return 100 * (entry - sc[j]) / entry, "CLOCK"


def one(path):
    sym = os.path.basename(path)[:-8]
    if sym not in OP:
        return []
    lf = pd.read_parquet(path, columns=["date", "close", "URF",
                                        "extinction", "ignition"])
    if len(lf) < 60 * RPS:
        return []
    c = lf["close"].to_numpy(float)
    urf = lf["URF"].to_numpy(float)
    ext = lf["extinction"].to_numpy(float)
    ign = lf["ignition"].to_numpy(float)
    dates = lf["date"].to_numpy()
    se = [i for i in range(len(lf) - 1) if dates[i] != dates[i + 1]]
    se.append(len(lf) - 1)
    sc = c[se]
    n = len(se)
    ext_s = np.array([ext[se[k - 1] + 1:se[k] + 1].sum() if k else 0
                      for k in range(n)])
    dead_s = np.array([(urf[se[k - 1] + 1:se[k] + 1] <= 0).sum() if k else 0
                       for k in range(n)])
    ign_s = np.array([ign[se[k - 1] + 1:se[k] + 1].sum() if k else 0
                      for k in range(n)])
    out = []
    k = 22
    while k < n - 7:
        date = str(dates[se[k]])[:10]
        base = float(np.median(sc[k - 20:k]))
        if base <= 0 or sc[k] < 1:
            k += 1
            continue
        # TIGHT: single-session >=8% jump within last 8 sessions,
        # top >=15% over base, zero ignitions since the jump
        jumps = [(j, 100 * (sc[j] / sc[j - 1] - 1))
                 for j in range(max(1, k - 8), k + 1)]
        big = [(j, g) for j, g in jumps if g >= 8]
        if big:
            j0, _ = max(big, key=lambda x: x[1])
            top = sc[j0]
            if (100 * (top / base - 1) >= 15
                    and ign_s[j0:k + 1].sum() == 0):
                for qc in (False, True):
                    pnl, reason = run_exit(sc, ext_s, dead_s, k + 1, qc)
                    out.append(("TIGHT_QC" if qc else "TIGHT", sym, date,
                                round(pnl, 2), reason))
                k += 6
                continue
        # LOOSE: >=15% above 20 sessions back, NO >=8% jump in last 8
        # sessions, zero ignitions in 22, first down close
        if (sc[k] >= 1.15 * sc[k - 20] and not big
                and ign_s[k - 21:k + 1].sum() == 0
                and sc[k] < sc[k - 1]):
            pnl, reason = run_exit(sc, ext_s, dead_s, k + 1, False)
            out.append(("LOOSE", sym, date, round(pnl, 2), reason))
            k += 6
            continue
        k += 1
    return out


files = sorted(os.path.join(LANES, f) for f in os.listdir(LANES)
               if f.endswith(".parquet"))
rows = []
with Pool(8) as p:
    for r in p.imap_unordered(one, files, chunksize=16):
        rows.extend(r)
ev = pd.DataFrame(rows, columns=["pop", "sym", "date", "pnl_pct", "reason"])
ev = ev.sort_values("date")
res = {"trades": int(len(ev))}
for pop in ("TIGHT", "TIGHT_QC", "LOOSE"):
    d = ev[ev["pop"] == pop]
    if not len(d):
        continue
    mid = d["date"].iloc[len(d) // 2]
    entry = {}
    for half, g in [("derive", d[d.date < mid]), ("confirm", d[d.date >= mid])]:
        entry[half] = {
            "n": int(len(g)),
            "usd_per_2500": round(float(g.pnl_pct.mean()) * 25, 2),
            "win_rate": round(float((g.pnl_pct > 0).mean()), 3),
            "exits": {kk: int(vv) for kk, vv in
                      g.reason.value_counts().items()},
        }
    res[pop] = entry
json.dump(res, open(OUT, "w"), indent=1)
ev.to_parquet(OUT.replace(".json", "_trades.parquet"))
print(json.dumps(res, indent=1))
print("filed:", OUT)
