"""
ch4_kgate_herd.py — HERD-conditioned species on K-gate tradable displacement
============================================================================

The last standing candidate from the campaign's own measurements: the
herd-conditioned tiers (completion-sign accuracy 73.6% at the deepest
real-volume tier) applied to the object that matters — the TRADABLE
displacement over the next K gates, reveal-slipped, strict as-of-issue.

Alphabets: bigram_H (species x herd energy band), bigram_HG (species x
herd energy x herd greed), against the unconditioned bigram control.
Herd state joined at the ISSUE day from the exported causal table.

Usage: CH4_K=5 python tools/ch4_kgate_herd.py
Output: artifacts/ch4_uf/ch4_kgate_herd_K<k>.json
"""

from __future__ import annotations

import hashlib
import json
import os
from collections import defaultdict

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREDS = os.environ.get("CH3_PREDS") or os.path.join(
    ROOT, "artifacts", "ch4_uf", "ch3_daily_preds_all.parquet")
HERD = os.path.join(ROOT, "artifacts", "ch4_uf", "herd_state_daily.parquet")
K = int(os.environ.get("CH4_K", "5"))
# HERD_LAG=1: join the PRIOR day's herd state (required for intraday
# issue instants — day D's herd state uses day-D closes and is only
# knowable at the daily close). 0 for daily streams (same instant).
HERD_LAG = int(os.environ.get("CH4_HERD_LAG", "0"))
OUT = os.environ.get("CH4_OUT") or os.path.join(
    ROOT, "artifacts", "ch4_uf", f"ch4_kgate_herd_K{K}.json")
W = 20
BAND = 0.75
CASH0, SLICE_PCT, MAX_OPEN = 100_000.0, 10.0, 10
ALPHAS = ("bigram", "bigram_H", "bigram_HG")


def hid(*parts) -> int:
    h = hashlib.blake2b("|".join(str(p) for p in parts).encode(),
                        digest_size=8)
    return int.from_bytes(h.digest(), "big") >> 1


def main():
    df = pd.read_parquet(PREDS)
    df = df[df["alpha"] == "bigram"].sort_values(["sym", "issue_d"],
                                                 kind="mergesort")
    mx = int(df["issue_d"].max())
    if mx > 10 ** 10:              # 12-digit YYYYMMDDHHMM
        key_div, day_div = 10 ** 8, 10 ** 4
    elif mx > 10 ** 9:             # 10-digit YYYYMMDDHH (early hourly)
        key_div, day_div = 10 ** 6, 10 ** 2
    else:                          # 8-digit YYYYMMDD
        key_div, day_div = 10 ** 4, 1
    herd = pd.read_parquet(HERD)
    hmap = {(s, d): (c, e, g) for s, d, c, e, g in zip(
        herd["sym"], herd["date"].astype(int), herd["cell"],
        herd["eband"], herd["gband"])}
    herd_days = sorted(herd["date"].astype(int).unique())
    prev_day = {d: (herd_days[i - 1] if i > 0 else None)
                for i, d in enumerate(herd_days)}
    day_pos = {d: i for i, d in enumerate(herd_days)}

    def herd_at(sym, day):
        if HERD_LAG == 0:
            return hmap.get((sym, day))
        # prior trading day's state (day may not be in herd_days if the
        # issue day is intraday-only; walk back to the latest earlier)
        if day in day_pos:
            d = prev_day[day]
        else:
            import bisect
            i = bisect.bisect_left(herd_days, day) - 1
            d = herd_days[i] if i >= 0 else None
        return hmap.get((sym, d)) if d is not None else None
    print(f"preds {len(df)} | herd states {len(hmap)} | lag={HERD_LAG}")

    obs = []          # (avail, sp_id, alpha_idx, disp, sym, issue, ipx, epx)
    for sym, sub in df.groupby("sym", sort=False):
        idd = sub["issue_d"].to_numpy()
        px = sub["issue_px"].to_numpy()
        sp = sub["species"].to_numpy()
        n = len(sub)
        for i in range(n - K):
            if px[i] <= 0:
                continue
            st = herd_at(sym, int(idd[i] // day_div))
            if st is None:
                continue
            c, e, g = st
            disp = px[i + K] / px[i] - 1.0
            row = (int(idd[i + K]), int(idd[i]), sym,
                   float(px[i]), float(px[i + K]), disp)
            obs.append((row[0], int(sp[i]), 0, disp, sym, row[1],
                        row[3], row[4]))
            obs.append((row[0], hid(sp[i], "H", e), 1, disp, sym, row[1],
                        row[3], row[4]))
            obs.append((row[0], hid(sp[i], "HG", e, g), 2, disp, sym,
                        row[1], row[3], row[4]))
    print(f"K={K} conditioned observations: {len(obs)}")

    obs.sort(key=lambda x: (x[5], x[4]))
    comp = sorted(obs, key=lambda x: x[0])
    pos, neg = defaultdict(int), defaultdict(int)
    agg = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    entries = defaultdict(list)
    a0 = [set(), set(), set()]
    cp = 0
    for avail, sp, ai, disp, sym, issue, ipx, epx in obs:
        while cp < len(comp) and comp[cp][0] < issue:
            c = comp[cp]
            if c[3] > 0:
                pos[c[1]] += 1
            elif c[3] < 0:
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
                a = agg[ALPHAS[ai]][y]
                a[0] += 1 if (disp > 0) == (pred > 0) else 0
                a[1] += 1
                entries[ALPHAS[ai]].append((issue, avail, sym, pred,
                                            ipx, epx))
        a0[ai].add(sp)
    while cp < len(comp):
        c = comp[cp]
        if c[3] > 0:
            pos[c[1]] += 1
        elif c[3] < 0:
            neg[c[1]] += 1
        cp += 1

    edges = [0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0]
    spectra = {}
    rng = np.random.default_rng(20260801)
    for ai, name in enumerate(ALPHAS):
        ids = a0[ai]
        sn = {s: (pos[s] + neg[s], pos[s] / (pos[s] + neg[s]))
              for s in ids if pos[s] + neg[s] >= W}
        cons = np.array([max(f, 1 - f) for _, f in sn.values()])
        ns = np.array([n for n, _ in sn.values()])
        tp = sum(pos[s] for s in sn)
        tn = sum(neg[s] for s in sn)
        base = tp / max(1, tp + tn)
        null_cons = []
        for n in ns:
            for d in rng.binomial(n, base, size=20):
                null_cons.append(max(d / n, 1 - d / n))
        spectra[name] = {
            "species_n_ge_W": len(sn), "base_up": round(base, 4),
            "real": np.histogram(cons, bins=edges)[0].tolist()
            if len(cons) else [],
            "null": (np.histogram(np.array(null_cons), bins=edges)[0]
                     / 20.0).tolist() if null_cons else []}

    import heapq
    books = {}
    for name, evs in entries.items():
        evs.sort(key=lambda x: (x[0], x[2]))
        yb = {}
        for issue, avail, sym, pred, ipx, epx in evs:
            y = str(issue // key_div)
            b = yb.setdefault(y, {"cash": CASH0, "rets": [], "held": {},
                                  "heap": []})
            while b["heap"] and b["heap"][0][0] <= issue:
                _a, hs, notl, ret = heapq.heappop(b["heap"])
                b["cash"] += notl * (1 + ret)
                b["rets"].append(100 * ret)
                b["held"].pop(hs, None)
            if sym in b["held"] or len(b["held"]) >= MAX_OPEN:
                continue
            notl = min(b["cash"] * SLICE_PCT / 100, b["cash"])
            if notl <= 0:
                continue
            b["cash"] -= notl
            b["held"][sym] = notl
            heapq.heappush(b["heap"], (avail, sym, notl,
                                       (epx / ipx - 1.0) * pred))
        out = {}
        for y in sorted(yb):
            b = yb[y]
            while b["heap"]:
                _a, hs, notl, ret = heapq.heappop(b["heap"])
                b["cash"] += notl * (1 + ret)
                b["rets"].append(100 * ret)
            rets = b["rets"]
            wins = sum(1 for r in rets if r > 0)
            out[y] = {"trades": len(rets),
                      "wr_pct": round(100 * wins / len(rets), 1) if rets else None,
                      "made_usd": round(b["cash"] - CASH0, 2),
                      "ret_pct": round(100 * (b["cash"] / CASH0 - 1), 2)}
        books[name] = out

    result = {
        "frame": f"K={K}-gate tradable displacement, herd-conditioned "
                 "(H = energy band, HG = energy x greed), strict "
                 "as-of-issue, reveal-slipped fills",
        "spectra": spectra,
        "band_aggregate_by_year": {
            a: {y: {"n": v[1], "hit_pct": round(100 * v[0] / v[1], 1)}
                for y, v in sorted(ys.items()) if v[1]}
            for a, ys in agg.items()},
        "book_by_year": books,
    }
    with open(OUT, "w") as f:
        json.dump(result, f, indent=1)
    print(json.dumps(result, indent=1))
    print("filed:", OUT)


if __name__ == "__main__":
    main()
