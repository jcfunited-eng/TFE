"""
ch4_canon_law.py — the species law on the CANONICAL kernel's gates
==================================================================

The question this answers (my own, chosen freely): is the species law —
gate-class bigrams predicting the next gate's direction, 58-69% every
year on my divergent machinery — a property of the PHYSICS, or an
artifact of my gate construction?

Machinery: uf_core (the production kernel, UF-Spec v1.4.0, pinned
constants). Gates are canonical quiet intervals (D(t) <= tau_D
interior). Species = bigram of (mosaic projection signature, direction
sign). Ledger strictly as-of-issue. Reveal discipline: a gate ending
at index e is knowable at bar e+2 (the boundary bar e+1 needs kappa,
which needs e+2); issue price = close[e+2].

Usage: CH4_SHARD=k/K CH4_MERGE=1 like the other law tools.
Output: artifacts/ch4_uf/ch4_canon_law.json
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from collections import defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from uf_core.layer0 import compute_sev_series  # noqa: E402
from uf_core.layer1 import (  # noqa: E402
    segment_gates, compute_gate_tvr, compute_mosaic_projections)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, "ch4_live_store.parquet")
OUT = os.path.join(ROOT, "artifacts", "ch4_uf", "ch4_canon_law.json")
SHARD_DIR = os.path.join(ROOT, "artifacts", "ch4_uf", "canon_shards")
SHARD = os.environ.get("CH4_SHARD")
MERGE = os.environ.get("CH4_MERGE") == "1"
W = 20
BAND = 0.75
MIN_BARS = 1200
PRICE_FLOOR = 5.0
REVEAL = 2                      # bars until a gate's end is knowable


def hid(*parts) -> int:
    h = hashlib.blake2b("|".join(str(p) for p in parts).encode(),
                        digest_size=8)
    return int.from_bytes(h.digest(), "big") >> 1


def universe(df):
    g = df.groupby("Symbol")["Close"]
    stats = pd.DataFrame({"bars": g.size(), "med": g.median()})
    return sorted(stats[(stats["bars"] >= MIN_BARS)
                        & (stats["med"] >= PRICE_FLOOR)].index)


def collect(symbols, t0):
    df = pd.read_parquet(STORE, columns=["Date", "Symbol", "Close", "Volume"],
                         filters=[("Symbol", "in", list(symbols))])
    df["Date"] = pd.to_datetime(df["Date"])
    obs = []
    for i, (sym, sub) in enumerate(df.groupby("Symbol", sort=True)):
        sub = sub.sort_values("Date").reset_index(drop=True)
        closes = sub["Close"].to_numpy(dtype=float)
        dates = sub["Date"].dt.strftime("%Y%m%d").astype(int).to_numpy()
        if len(closes) < MIN_BARS:
            continue
        try:
            sev = compute_sev_series(sub.rename(columns={"Close": "Close"}))
            gates = segment_gates(sev)
            tvrs = compute_gate_tvr(sev, gates)
            projs = compute_mosaic_projections(tvrs)
        except Exception:
            continue
        # per-gate class: (projection signature, direction sign of the
        # gate's displacement close[end]/close[start-1]-1)
        classes = []
        for g, pr in zip(gates, projs):
            a, e = g.start_idx, g.end_idx
            ref = closes[a - 1] if a >= 1 else closes[a]
            disp = closes[e] / ref - 1.0 if ref > 0 else 0.0
            sign = 1 if disp > 0 else (-1 if disp < 0 else 0)
            classes.append((tuple(map(tuple, pr)), sign, e, disp))
        for k in range(2, len(classes)):
            (pp, sp_, _, _), (pc, sc, e_cur, _), (pn, sn, e_n, disp_n) = \
                classes[k - 2], classes[k - 1], classes[k]
            issue_i = e_cur + REVEAL
            avail_i = e_n + REVEAL
            if avail_i >= len(closes):
                continue
            if closes[issue_i] < PRICE_FLOOR:
                continue
            species = hid("canon", (pp, sp_), (pc, sc))
            obs.append((int(dates[avail_i]), species, disp_n,
                        int(dates[issue_i]), float(closes[issue_i]),
                        float(closes[avail_i]), sym))
        if (i + 1) % 100 == 0:
            print(f"  [{i+1}/{len(symbols)}] obs={len(obs)} "
                  f"{time.time()-t0:.0f}s", flush=True)
    return pd.DataFrame(obs, columns=["avail", "sp", "disp", "issue",
                                      "ipx", "epx", "sym"])


def main():
    t0 = time.time()
    df_syms = universe(pd.read_parquet(STORE, columns=["Symbol", "Close"]))
    if SHARD:
        k, K = (int(x) for x in SHARD.split("/"))
        mine = [s for j, s in enumerate(df_syms) if j % K == k]
        odf = collect(mine, t0)
        os.makedirs(SHARD_DIR, exist_ok=True)
        odf.to_parquet(os.path.join(SHARD_DIR, f"obs_{k}_{K}.parquet"),
                       index=False)
        print(f"[s{k}] {len(odf)} obs filed ({time.time()-t0:.0f}s)")
        return
    if MERGE:
        odf = pd.concat([pd.read_parquet(os.path.join(SHARD_DIR, p))
                         for p in sorted(os.listdir(SHARD_DIR))],
                        ignore_index=True)
    else:
        odf = collect(df_syms, t0)
    print(f"observations: {len(odf)} ({time.time()-t0:.0f}s)", flush=True)

    odf = odf.sort_values(["issue", "sym"], kind="mergesort")
    arrs = [odf[c].to_numpy() for c in
            ("avail", "sp", "disp", "issue", "ipx", "epx")]
    c_order = np.argsort(arrs[0], kind="stable")
    c_avail, c_sp, c_disp = (arrs[0][c_order], arrs[1][c_order],
                             arrs[2][c_order])
    n = len(odf)
    pos, neg = defaultdict(int), defaultdict(int)
    agg = defaultdict(lambda: [0, 0])          # year -> [hit, n] (gate law)
    tagg = defaultdict(lambda: [0.0, 0, 0])    # year -> [trad ret sum, hits, n]
    cp = 0
    for j in range(n):
        avail, sp, disp, issue, ipx, epx = (a[j] for a in arrs)
        while cp < n and c_avail[cp] < issue:
            s2 = int(c_sp[cp])
            d2 = c_disp[cp]
            if d2 > 0:
                pos[s2] += 1
            elif d2 < 0:
                neg[s2] += 1
            cp += 1
        p, q = pos[int(sp)], neg[int(sp)]
        m = p + q
        if m >= W:
            f = p / m
            if max(f, 1 - f) >= BAND and disp != 0:
                pred = 1 if f >= 0.5 else -1
                y = int(issue) // 10 ** 4
                a = agg[y]
                a[0] += 1 if (disp > 0) == (pred > 0) else 0
                a[1] += 1
                tr = 100 * (epx / ipx - 1.0) * pred    # tradable, reveal→reveal
                t_ = tagg[y]
                t_[0] += tr
                t_[1] += 1 if tr > 0 else 0
                t_[2] += 1
    result = {
        "frame": "species law on CANONICAL uf_core gates (quiet-interval, "
                 "pinned tau_D) — band>=0.75, n>=20, strict as-of-issue, "
                 "reveal=+2 bars; plus the TRADABLE (reveal-to-reveal) read",
        "observations": int(n),
        "law_by_year": {str(y): {"n": v[1],
                                 "hit_pct": round(100 * v[0] / v[1], 1)}
                        for y, v in sorted(agg.items()) if v[1]},
        "tradable_by_year": {str(y): {
            "n": v[2], "mean_ret_pct": round(v[0] / v[2], 3),
            "wr_pct": round(100 * v[1] / v[2], 1)}
            for y, v in sorted(tagg.items()) if v[2]},
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(result, f, indent=1)
    print(json.dumps(result, indent=1))
    print("filed:", OUT)


if __name__ == "__main__":
    main()
