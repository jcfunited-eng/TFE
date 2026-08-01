"""
ch4_kgate_law.py — species structure on MULTI-GATE tradable displacement
========================================================================

The reveal-bar theorem killed one-gate harvests: the payout sits inside
the reveal bar. The patient frame (the big risers) asks a different
question: does a species predict the TRADABLE displacement over the
next K gates — where the move is large and the one-bar timing cost is
a small fraction?

Runs on the existing keep-all prediction streams (issue prices already
reveal-slipped). Per symbol, event i's K-gate outcome = sign of
issue_px[i+K]/issue_px[i]-1; availability = event i+K's issue instant;
records strictly as-of-issue (two-stream ledger). Spectrum vs binomial
null + band>=0.75 per-year aggregate + declared book (enter at event
i's issue price, exit at event i+K's issue price, 10% slices, max 10,
fresh $100k per entry-year).

Usage: CH3_PREDS=... CH4_K=5 python tools/ch4_kgate_law.py
Output: artifacts/ch4_uf/ch4_kgate_law_K<k>.json
"""

from __future__ import annotations

import json
import os
from collections import defaultdict

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREDS = os.environ.get("CH3_PREDS") or os.path.join(
    ROOT, "artifacts", "ch4_uf", "ch3_daily_preds_all.parquet")
K = int(os.environ.get("CH4_K", "5"))
OUT = os.path.join(ROOT, "artifacts", "ch4_uf", f"ch4_kgate_law_K{K}.json")
W = 20
BAND = 0.75
CASH0, SLICE_PCT, MAX_OPEN = 100_000.0, 10.0, 10


def main():
    df = pd.read_parquet(PREDS)
    df = df[df["alpha"] == "bigram"].sort_values(["sym", "issue_d"],
                                                 kind="mergesort")
    key_div = 10 ** 8 if df["issue_d"].max() > 10 ** 10 else 10 ** 6
    obs = []
    for sym, sub in df.groupby("sym", sort=False):
        idd = sub["issue_d"].to_numpy()
        px = sub["issue_px"].to_numpy()
        sp = sub["species"].to_numpy()
        n = len(sub)
        for i in range(n - K):
            if px[i] <= 0:
                continue
            disp = px[i + K] / px[i] - 1.0
            obs.append((int(idd[i + K]), int(sp[i]), disp, sym,
                        int(idd[i]), float(px[i]), float(px[i + K])))
    print(f"K={K} observations: {len(obs)}")

    obs.sort(key=lambda x: (x[4], x[3]))            # by issue
    comp = sorted(obs, key=lambda x: x[0])          # by availability
    pos, neg = defaultdict(int), defaultdict(int)
    agg = defaultdict(lambda: [0, 0])
    entries = []
    cp = 0
    for avail, sp, disp, sym, issue, ipx, epx in obs:
        while cp < len(comp) and comp[cp][0] < issue:
            c = comp[cp]
            if c[2] > 0:
                pos[c[1]] += 1
            elif c[2] < 0:
                neg[c[1]] += 1
            cp += 1
        p, q = pos[sp], neg[sp]
        n = p + q
        if n >= W:
            f = p / n
            band = max(f, 1 - f)
            pred = 1 if f >= 0.5 else -1
            if band >= BAND and disp != 0:
                y = str(issue // key_div)
                agg[y][0] += 1 if (disp > 0) == (pred > 0) else 0
                agg[y][1] += 1
                entries.append((issue, avail, sym, pred, ipx, epx))
    while cp < len(comp):
        c = comp[cp]
        if c[2] > 0:
            pos[c[1]] += 1
        elif c[2] < 0:
            neg[c[1]] += 1
        cp += 1

    species_n = {s: (pos[s] + neg[s], pos[s] / (pos[s] + neg[s]))
                 for s in pos.keys() | neg.keys() if pos[s] + neg[s] >= W}
    cons = np.array([max(f, 1 - f) for _, f in species_n.values()])
    ns = np.array([n for n, _ in species_n.values()])
    tp, tn = sum(pos.values()), sum(neg.values())
    base = tp / max(1, tp + tn)
    rng = np.random.default_rng(20260801)
    null_cons = []
    for n in ns:
        for d in rng.binomial(n, base, size=20):
            null_cons.append(max(d / n, 1 - d / n))
    edges = [0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0]

    entries.sort(key=lambda x: (x[0], x[2]))
    import heapq
    books = {}
    for issue, avail, sym, pred, ipx, epx in entries:
        y = str(issue // key_div)
        b = books.setdefault(y, {"cash": CASH0, "rets": [], "held": {},
                                 "heap": []})
        while b["heap"] and b["heap"][0][0] <= issue:
            _a, hsym, notl, ret = heapq.heappop(b["heap"])
            b["cash"] += notl * (1 + ret)
            b["rets"].append(100 * ret)
            b["held"].pop(hsym, None)
        if sym in b["held"] or len(b["held"]) >= MAX_OPEN:
            continue
        notl = min(b["cash"] * SLICE_PCT / 100, b["cash"])
        if notl <= 0:
            continue
        b["cash"] -= notl
        b["held"][sym] = notl
        heapq.heappush(b["heap"], (avail, sym, notl,
                                   (epx / ipx - 1.0) * pred))
    by_year = {}
    for y in sorted(books):
        b = books[y]
        while b["heap"]:
            _a, hsym, notl, ret = heapq.heappop(b["heap"])
            b["cash"] += notl * (1 + ret)
            b["rets"].append(100 * ret)
        rets = b["rets"]
        wins = sum(1 for r in rets if r > 0)
        by_year[y] = {"trades": len(rets),
                      "wr_pct": round(100 * wins / len(rets), 1) if rets else None,
                      "mean_ret_pct": round(float(np.mean(rets)), 3) if rets else None,
                      "made_usd": round(b["cash"] - CASH0, 2),
                      "ret_pct": round(100 * (b["cash"] / CASH0 - 1), 2)}

    result = {
        "frame": f"K={K}-gate tradable displacement, bigram species, "
                 "strict as-of-issue, reveal-slipped fills",
        "observations": len(obs),
        "species_n_ge_W": len(species_n),
        "base_up_rate": round(base, 4),
        "spectrum_real": np.histogram(cons, bins=edges)[0].tolist()
        if len(cons) else [],
        "spectrum_null_mean": (np.histogram(np.array(null_cons), bins=edges)[0]
                               / 20.0).tolist() if null_cons else [],
        "band_aggregate_by_year": {
            y: {"n": v[1], "hit_pct": round(100 * v[0] / v[1], 1)}
            for y, v in sorted(agg.items()) if v[1]},
        "book_by_year": by_year,
    }
    with open(OUT, "w") as f:
        json.dump(result, f, indent=1)
    print(json.dumps({k: result[k] for k in
                      ("observations", "species_n_ge_W", "base_up_rate",
                       "spectrum_real", "spectrum_null_mean")}, indent=1))
    print(json.dumps({"band": result["band_aggregate_by_year"],
                      "book": result["book_by_year"]}, indent=1))
    print("filed:", OUT)


if __name__ == "__main__":
    main()
