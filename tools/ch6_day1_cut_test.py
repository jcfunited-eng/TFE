"""DAY-1 CUT for the CH6 short book — declared 2026-09-23 BEFORE running.

RESULT 2026-09-23 — FAILED THE DECLARED BAR. THIS FILE IS THE GRAVE.
  3,586 entries per arm (the year lanes on disk cover 2025-2026 only,
  not a decade — say so). Dollars per $2,500 slice:
                 derive       confirm      2025        2026
    TIGHT       -11.27       -13.03      -14.19      -11.21
    TIGHT_QC     -8.71       -10.21       -9.98       -9.23   (shipped)
    TIGHT_D1    -11.09        -9.99      -12.68       -9.54   (this rule)
  D1 loses to the shipped ladder in the derive half and in both years;
  it cut 883 positions on day one, and 178 of those would have BANKED.
  The +$732 it showed on the 124-trade live book was fitted to that
  book. Do not ship. Do not re-tune the threshold (that is band-mining).
  Filed: artifacts/ch6_harvest/ch6_day1_cut_test.json (+ _trades.parquet).
  The replay also restates the standing fact: the TIGHT door loses
  $11-13 a trade under the engine's own exits, and no exit rule
  rescues a door — the exit-law bar in tfe-condemned-ideas.

Claude's rule (MINE), on trial. Joe's word: "if you see a good fix for
CH6 go for it."

WHAT THE LIVE BOOK SHOWED (124 closed, all shorts, 2026-08-26..09-23):
  HARVEST   63/63  +$5,161      QUIET-CUT 25/0  -$3,380
  TIME      20/6   -$1,585      sound-structure 15/6 -$131   ANOMALY 1 -$577
  Short gain at the FIRST completed close after the fill, by outcome:
  harvest +1.95% mean, quiet-cut -2.41%, time -1.46%. The losers are
  already above entry at the first close; the shipped quiet-cut waits
  for two closes plus a lane read, and the worst had run 9-19% by then.

THE RULE UNDER TEST:
  At the first completed close after entry, a short whose close sits
  at or above its entry price is cut, executed at the NEXT session's
  close (the fact is knowable only at that first close; the live
  engine's pending-cut machinery executes at the next mark). Every
  other exit stays exactly as shipped: bank at any close >= +2%, stop
  at -20%, the shipped quiet-cut at >= 2 sessions, out at the 5th close.

METHOD (the filed harness, tools/ch6_tight_vs_loose_test.py, unchanged
except for the one added arm):
  population TIGHT = the trainers' bounds (single-session close-gain
  >= 8% standing >= 15% over the 20-session median base, within 8
  sessions, zero ignitions since the jump), enter next session close,
  operating companies only, year lanes.
  arms: TIGHT (no quiet-cut) | TIGHT_QC (shipped) | TIGHT_D1 (shipped + day-1 cut)
  same entries in every arm. Dollars per $2,500 slice. Derive/confirm
  halves by entry date AND per calendar year. No costs modelled.
  Execution handicap is on the new arm only (next close, not the close
  that showed the fact). One shot; the result is filed whichever way
  it falls.

PASS BAR, declared: TIGHT_D1 beats TIGHT_QC in usd_per_2500 in BOTH
halves and in at least 7 of the years with n >= 100. Otherwise the
rule is not shipped and this file is its grave.
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
       "ch6_day1_cut_test.json")
RPS = 5
WORKERS = int(os.environ.get("CH6_WORKERS", "6"))
TT = json.load(open("/workspaces/Tao_Financial_Engine/artifacts/"
                    "ch6_harvest/ticker_types.json"))
OP = {s for s, t in TT.items() if t in ("CS", "ADRC")}


def run_exit(sc, ext_s, dead_s, ei, quiet_cut, day1_cut):
    """Engine exits from entry close ei; returns (pnl_pct, reason)."""
    entry = sc[ei]
    n = len(sc)
    pending = None
    for j in range(ei + 1, min(ei + 6, n)):
        gain = 100 * (entry - sc[j]) / entry
        if pending is not None:
            # a cut marked at the prior close executes at this close
            return gain, pending
        if gain >= 2.0:
            return gain, "BANK"
        if gain <= -20.0:
            return gain, "STOP"
        if quiet_cut and j >= ei + 2:
            if (ext_s[ei + 1:j + 1].sum() == 0
                    and dead_s[ei + 1:j + 1].sum() == 0
                    and sc[j] >= entry):
                return gain, "QUIET_CUT"
        if day1_cut and j == ei + 1 and sc[j] >= entry:
            pending = "DAY1_CUT"
    j = min(ei + 5, n - 1)
    gain = 100 * (entry - sc[j]) / entry
    if pending is not None:
        return gain, pending
    return gain, "CLOCK"


ARMS = (("TIGHT", False, False), ("TIGHT_QC", True, False),
        ("TIGHT_D1", True, True))


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
        jumps = [(j, 100 * (sc[j] / sc[j - 1] - 1))
                 for j in range(max(1, k - 8), k + 1)]
        big = [(j, g) for j, g in jumps if g >= 8]
        if big:
            j0, _ = max(big, key=lambda x: x[1])
            top = sc[j0]
            if (100 * (top / base - 1) >= 15
                    and ign_s[j0:k + 1].sum() == 0):
                for name, qc, d1 in ARMS:
                    pnl, reason = run_exit(sc, ext_s, dead_s, k + 1, qc, d1)
                    out.append((name, sym, date, round(pnl, 2), reason))
                k += 6
                continue
        k += 1
    return out


def summarise(g):
    return {
        "n": int(len(g)),
        "usd_per_2500": round(float(g.pnl_pct.mean()) * 25, 2),
        "usd_total_per_2500": round(float(g.pnl_pct.sum()) * 25, 2),
        "win_rate": round(float((g.pnl_pct > 0).mean()), 3),
        "exits": {kk: int(vv) for kk, vv in g.reason.value_counts().items()},
    }


if __name__ == "__main__":
    files = sorted(os.path.join(LANES, f) for f in os.listdir(LANES)
                   if f.endswith(".parquet"))
    rows = []
    with Pool(WORKERS) as p:
        for r in p.imap_unordered(one, files, chunksize=16):
            rows.extend(r)
    ev = pd.DataFrame(rows, columns=["pop", "sym", "date", "pnl_pct", "reason"])
    ev = ev.sort_values("date")
    ev["year"] = ev["date"].str[:4]
    res = {"trades_per_arm": int(len(ev) // len(ARMS)),
           "declared": "TIGHT_D1 > TIGHT_QC usd_per_2500 in BOTH halves and >= 7 years with n>=100"}
    for name, _, _ in ARMS:
        d = ev[ev["pop"] == name]
        if not len(d):
            continue
        mid = d["date"].iloc[len(d) // 2]
        entry = {"derive": summarise(d[d.date < mid]),
                 "confirm": summarise(d[d.date >= mid]),
                 "years": {y: summarise(g) for y, g in d.groupby("year")}}
        res[name] = entry
    # verdict against the declared bar
    qc, d1 = res.get("TIGHT_QC"), res.get("TIGHT_D1")
    if qc and d1:
        halves = all(d1[h]["usd_per_2500"] > qc[h]["usd_per_2500"]
                     for h in ("derive", "confirm"))
        years = [y for y in d1["years"]
                 if d1["years"][y]["n"] >= 100 and y in qc["years"]]
        wins = sum(1 for y in years
                   if d1["years"][y]["usd_per_2500"] > qc["years"][y]["usd_per_2500"])
        res["verdict"] = {"both_halves": bool(halves),
                          "years_scored": len(years), "years_won": wins,
                          "PASS": bool(halves and wins >= 7)}
    json.dump(res, open(OUT, "w"), indent=1)
    ev.to_parquet(OUT.replace(".json", "_trades.parquet"))
    print(json.dumps({k: v for k, v in res.items() if k != "years"}, indent=1)[:6000])
    print("filed:", OUT)
