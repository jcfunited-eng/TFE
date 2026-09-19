"""The nine as a POSITION, not as five tests.

Joseph, 2026-09-19: "You are flattening it."

He is right about everything built before this. Every reading I made today had
this shape:

    viable   = g_k == 1                 one bit
    motion   = (D == 1) & (M > 0)       one bit
    geometry = Rev == 0                 one bit
    carry    = B >= prev_B              one bit
    burden   = not(C==3 and P==2)       one bit
    enter    = all five ANDed           ONE BIT

Nine fields, thousands of distinct values each, crushed to a single bit. That
cannot carry the momentum of a rise or say where the exit is, which is why
every one of them landed on a coin toss.

This does not compare any field to a constant. It compares whole tuples to
whole tuples: find the moments in history where the nine-value state sat
closest to where it sits now, and read what those structures actually did next.
Nothing is thresholded, weighted, scored, averaged or rounded.

DECLARED BEFORE RUNNING
-----------------------
The nine, at full precision, exactly as the kernel emits them:
    D_k  M_k  R_k  Rev_k  U_star_k  C_k  P_k  B_k  S_UF        HIS

Distance: plain Euclidean over those nine raw values.                  MINE
    No per-field weights are invented. No field is rescaled, so each enters
    at whatever spread the kernel gives it. The alternative -- normalising
    per field -- would require a statistic over the data, and every such
    statistic is a mean, a median or a range that Joseph has ruled out.

k = 25 nearest historical tuples.                                      MINE
Forward horizon N = 20 sessions for what a neighbour "did next".       MINE

Causality: the library is every tuple strictly BEFORE 2023-10-01; queries are
tuples on or after it. Every neighbour therefore predates every query, and each
neighbour's outcome was fully observable before the query existed.

Entry, two declared forms, both reported, neither chosen after the fact:
    UNANIMOUS      all 25 neighbours rose over their next 20 sessions
    SUPERMAJORITY  at least 20 of 25 did
These are counts, not averages.

Exit: hold 20 sessions. Fixed, so this measures the reading alone.

Bar: mean return per position must beat the 95th percentile of a matched-timing
null drawn inside the same body -- same count, same holding length, 200 seeds.

Usage:
  PYTHONHASHSEED=0 python tools/ch2_tuple_neighbours.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "quarantine_12k_governed_states_full.parquet"
OUT = ROOT / "artifacts" / "ch4_uf" / "ch2_tuple_neighbours_20260919.json"

NINE = ["D_k", "M_k", "R_k", "Rev_k", "U_star_k", "C_k", "P_k", "B_k", "S_UF"]
SPLIT = np.datetime64("2023-10-01", "D")
K = 25
HORIZON = 20
LIB_N = 1_000_000
QRY_N = 200_000
SEEDS = 200
BENCH = {"SPY", "QQQ", "DIA", "IWM"}


def main() -> int:
    cols = ["Date", "Symbol", "Close"] + NINE
    q = pd.read_parquet(SRC, columns=cols)
    for c in NINE:
        q[c] = pd.to_numeric(q[c], errors="coerce")
    q = q.dropna(subset=NINE).sort_values(["Symbol", "Date"]).reset_index(drop=True)
    print(f"[nb] {len(q)} daily tuples, {q.Symbol.nunique()} bodies", flush=True)

    # forward return over the declared horizon, within each body
    close = q.Close.values.astype(float)
    sym = q.Symbol.values
    fwd = np.full(len(q), np.nan)
    idx = np.arange(len(q))
    same = np.zeros(len(q), dtype=bool)
    same[: len(q) - HORIZON] = sym[HORIZON:] == sym[: len(q) - HORIZON]
    j = idx[same] + HORIZON
    fwd[idx[same]] = close[j] / close[idx[same]] - 1.0

    day = q.Date.values.astype("datetime64[D]")
    X = q[NINE].values.astype(np.float32)
    ok = np.isfinite(fwd)
    lib_m = ok & (day < SPLIT)
    qry_m = ok & (day >= SPLIT)
    print(f"[nb] library {int(lib_m.sum())} tuples before {SPLIT}; "
          f"queries {int(qry_m.sum())} on/after", flush=True)

    rng = np.random.default_rng(int.from_bytes(
        hashlib.blake2b(b"ch2-tuple-neighbours-20260919", digest_size=8).digest(), "big") % (2**63))
    li = np.flatnonzero(lib_m)
    if len(li) > LIB_N:
        li = np.sort(rng.choice(li, size=LIB_N, replace=False))
    qi = np.flatnonzero(qry_m)
    if len(qi) > QRY_N:
        qi = np.sort(rng.choice(qi, size=QRY_N, replace=False))
    print(f"[nb] sampled library {len(li)}, queries {len(qi)}", flush=True)

    from scipy.spatial import cKDTree
    tree = cKDTree(X[li].astype(np.float64))
    print("[nb] index built, querying...", flush=True)
    _, ind = tree.query(X[qi].astype(np.float64), k=K, workers=-1)
    lib_fwd = fwd[li]
    rose = (lib_fwd[ind] > 0.0)           # a count, never an average
    n_rose = rose.sum(axis=1)
    print(f"[nb] neighbours that rose: 25/25 on {np.mean(n_rose==K)*100:.3f}% of queries, "
          f">=20/25 on {np.mean(n_rose>=20)*100:.2f}%", flush=True)

    out = {"declaration": "docstring of tools/ch2_tuple_neighbours.py",
           "k": K, "horizon": HORIZON, "split": str(SPLIT),
           "library": int(len(li)), "queries": int(len(qi)), "forms": {}}

    qsym = sym[qi]; qfwd = fwd[qi]; qday = day[qi]
    closes = {s: g.Close.values.astype(float) for s, g in q.groupby("Symbol", sort=False)}
    pos_in_body = q.groupby("Symbol", sort=False).cumcount().values[qi]

    for name, mask in (("UNANIMOUS_25_of_25", n_rose == K),
                       ("SUPERMAJORITY_20_of_25", n_rose >= 20)):
        m = mask & ~np.isin(qsym, list(BENCH))
        if m.sum() < 50:
            out["forms"][name] = {"positions": int(m.sum()), "note": "too few to measure"}
            print(f"[nb] {name}: only {int(m.sum())} positions", flush=True)
            continue
        R = qfwd[m]; T = qsym[m]; P = pos_in_body[m]
        null = np.full((SEEDS, len(R)), np.nan)
        for t in np.unique(T):
            sel = np.flatnonzero(T == t)
            cl = closes[t]; hi = len(cl) - HORIZON - 1
            if hi <= 0:
                continue
            g = np.random.default_rng(int.from_bytes(
                hashlib.blake2b(str(t).encode(), digest_size=4).digest(), "big"))
            st = (g.random((SEEDS, len(sel))) * hi).astype(np.int64)
            null[:, sel] = cl[st + HORIZON] / cl[st] - 1.0
        nm = np.nanmean(null, axis=1) * 100
        p95 = float(np.nanpercentile(nm, 95))
        rec = {"positions": int(len(R)), "bodies": int(len(np.unique(T))),
               "mean_pct": float(R.mean() * 100), "win_rate_pct": float((R > 0).mean() * 100),
               "null_mean_pct": float(np.nanmean(nm)), "null_p95": p95,
               "beats_null": bool(R.mean() * 100 > p95)}
        h1 = qday[m] < np.datetime64("2025-01-01", "D")
        rec["first_half_mean_pct"] = float(R[h1].mean() * 100) if h1.any() else None
        rec["second_half_mean_pct"] = float(R[~h1].mean() * 100) if (~h1).any() else None
        out["forms"][name] = rec
        print(f"[nb] {name}: n={rec['positions']} mean={rec['mean_pct']:+.2f}% "
              f"win={rec['win_rate_pct']:.1f}% | null {rec['null_mean_pct']:+.2f}% "
              f"p95 {p95:+.2f}% BEATS={rec['beats_null']} | "
              f"h1 {rec['first_half_mean_pct']} h2 {rec['second_half_mean_pct']}", flush=True)

    # benchmarks reported separately, never in the pool
    bm = {}
    for b in sorted(BENCH):
        s = np.isin(qsym, [b])
        for name, mask in (("UNANIMOUS_25_of_25", n_rose == K), ("SUPERMAJORITY_20_of_25", n_rose >= 20)):
            mm = s & mask
            bm.setdefault(b, {})[name] = {
                "positions": int(mm.sum()),
                "mean_pct": float(qfwd[mm].mean() * 100) if mm.sum() else None}
    out["benchmarks"] = bm
    print(f"[nb] benchmarks: {json.dumps(bm)}", flush=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, default=str))
    print(f"[nb] written {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
