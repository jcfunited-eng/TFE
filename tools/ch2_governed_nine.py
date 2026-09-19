"""The nine values on the governed daily states — the data Joseph pointed at.

"this is all you need to be feeding it" + a screenshot of raw OHLCV.

I had been feeding a close-only Series to uf_core's adapter, which returns ONE
tuple per gate and finds 6 gates in SPY's decade. quarantine_historical_kernel
.py runs the same physics with a rolling window and emits one governed state
PER DAY. Its output is already on disk:

    quarantine_12k_governed_states.parquet
    8,343,139 rows | 11,882 symbols | 2021-03-29 .. 2026-03-24 | daily

Granularity there, for SPY: R_k and s_n change every day, U_star_k on 50.6%,
M_k 9.9%, P_k 9.4%, D_k 7.0%, Rev_k 4.6%. Against D_k changing 4 times in a
decade from the path I was using.

The nine, mapped with no average anywhere:
    S_UF := s_n     (psi_s, per day)        R_UF := R_k   (per day)
    D_k  M_k  Rev_k  U_star_k  C_k  P_k  B_k            (per day)
    prev_B_k is a column, so carry is read natively -- nothing invented.

No mean, no median, no rounding, no truncation, no bucketing. Every field
enters at its exact stored value. Clauses are marked HIS or MINE.

Usage:
  PYTHONHASHSEED=0 python tools/ch2_governed_nine.py
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
OUT = ROOT / "artifacts" / "ch4_uf" / "ch2_governed_nine_20260919.json"
BENCH = ["SPY", "QQQ", "DIA", "IWM"]
SEEDS = 200
COLS = ["Date", "Symbol", "Close", "D_k", "M_k", "R_k", "Rev_k",
        "U_star_k", "C_k", "P_k", "B_k", "prev_B_k",
        "S_UF", "g_k", "URF_k", "Hyst_k", "IAS_k", "U_k"]


def clauses(g: pd.DataFrame) -> dict:
    # S_UF is NOT in this file. s_n is "surprise" (params.lambda_s * surprise),
    # not the support floor -- mapping it to S_UF was my error. psi_s computes
    # S inside quarantine_historical_kernel and never writes it, the same
    # discard pattern one layer over. The viability clause therefore reads
    # U_star_k against RESONANCE ONLY, which is half of what Joseph specified.
    R = g.R_k.values            # resonance confirmation HIS
    U = g.U_star_k.values       # penalized uncertainty  HIS
    D = g.D_k.values            # directional sign       HIS
    M = g.M_k.values            # local bend             HIS
    RV = g.Rev_k.values         # reversal               HIS
    C = g.C_k.values            # conflict burden        HIS
    P = g.P_k.values            # persistence stress     HIS
    B = g.B_k.values            # accumulated carry      HIS
    Bp = g.prev_B_k.values      # the kernel's own previous carry -- not my lookback
    cmax, pmax = 3.0, 2.0       # native maxima
    return {
        # HIS: U_star_k read against support and resonance, never alone.
        # HIS: U_star_k "tells whether the field remains trustworthy" and
        # "should be read against support and resonance, not alone". The kernel
        # answers exactly that question itself: g_k = 1 iff U_k <= U_max AND
        # IAS_k == 0 AND Hyst_k == 0. Using the kernel's own verdict instead of
        # a raw S_UF > U_star_k comparison, which CANNOT fire in this
        # implementation: psi_s = 1/(1+C+delta_g) caps support at 1/3 and falls
        # with C, while psi_u rises with the same C. They are built on opposite
        # sides of one term. That is a fact about the code, not a rule of mine.
        "viable": g.g_k.values == 1,
        # HIS: D_k not enough alone; M_k says continuing or bending back.
        "motion": (D == 1.0) & (M > 0.0),
        # HIS: reversal is a first-class state, not a penalty.
        "geometry": RV == 0.0,
        # HIS: carrying stable potential, or exhausting it.
        "carry": B >= Bp,
        # HIS: C_k no standalone veto, P_k must not dominate alone -> only
        #      both at their native maxima together.
        "burden": ~((C >= cmax) & (P >= pmax)),
    }


def state_end(g: pd.DataFrame) -> np.ndarray:
    # HIS: R_rev_k "marks a major geometry break ... a first-class change in
    # state". The exit is that break. My previous version made the exit the
    # negation of the entry, which forces one-session holds by construction --
    # the position ends the moment the entry stops holding. That was my error,
    # not a reading of the field.
    return g.Rev_k.values == 1.0


def main() -> int:
    q = pd.read_parquet(SRC, columns=COLS)
    for c in COLS[3:]:
        q[c] = pd.to_numeric(q[c], errors="coerce")
    q = q.dropna(subset=COLS[3:]).sort_values(["Symbol", "Date"])
    print(f"[gn] {len(q)} daily governed states, {q.Symbol.nunique()} symbols, "
          f"{pd.to_datetime(q.Date).min().date()} .. {pd.to_datetime(q.Date).max().date()}", flush=True)

    rates = {k: [] for k in ["viable", "motion", "geometry", "carry", "burden", "enter"]}
    rets, lens, tks = [], [], []
    closes, bench = {}, {}

    for sym, g in q.groupby("Symbol", sort=False):
        if len(g) < 250:
            continue
        g = g.reset_index(drop=True)
        cl = g.Close.values.astype(float)
        cc = clauses(g)
        enter = np.logical_and.reduce(list(cc.values()))
        end = state_end(g)
        for k, v in cc.items():
            rates[k].append(float(v.mean()))
        rates["enter"].append(float(enter.mean()))
        closes[sym] = cl
        n = len(cl); i = 0; taken = []
        while i < n:
            if not enter[i]:
                i += 1
                continue
            x = i + 1
            while x < n and not end[x]:
                x += 1
            xj = min(x, n - 1)
            if xj <= i:
                break
            taken.append((i, xj))
            i = x + 1
        if sym in BENCH:
            r = [cl[b] / cl[a] - 1.0 for a, b in taken]
            bench[sym] = {"positions": len(taken), "enter_rate_pct": float(enter.mean() * 100),
                          "mean_pct": float(np.mean(r) * 100) if r else None,
                          "buy_and_hold_pct": float(cl[-1] / cl[0] - 1.0) * 100,
                          "mean_hold": float(np.mean([b - a for a, b in taken])) if taken else None}
        else:
            for a, b in taken:
                rets.append(cl[b] / cl[a] - 1.0); lens.append(b - a); tks.append(sym)

    print("\nclause firing rates (each body's own rate, listed not averaged):")
    for k, v in rates.items():
        a = np.array(v)
        print(f"  {k:9s} p05 {np.percentile(a,5)*100:5.1f}%  p50 {np.percentile(a,50)*100:5.1f}%  "
              f"p95 {np.percentile(a,95)*100:5.1f}%   never fires in {(a==0).sum()} of {len(a)} bodies", flush=True)

    R = np.array(rets); L = np.array(lens); T = np.array(tks)
    print(f"\n[gn] positions={len(R)} across {len(set(tks))} bodies (benchmarks held out)", flush=True)
    out = {"source": str(SRC.name), "clause_rates": rates, "benchmarks": bench}
    if len(R):
        null = np.full((SEEDS, len(R)), np.nan)
        for t in np.unique(T):
            sel = np.flatnonzero(T == t)
            cl = closes[t]; nb = len(cl)
            hi = nb - L[sel] - 1
            g2 = hi > 0
            if not g2.any():
                continue
            sg = sel[g2]; Lg = L[sel][g2]; hg = hi[g2]
            rng = np.random.default_rng(int.from_bytes(
                hashlib.blake2b(str(t).encode(), digest_size=4).digest(), "big"))
            st = (rng.random((SEEDS, len(sg))) * hg).astype(np.int64)
            null[:, sg] = cl[st + Lg] / cl[st] - 1.0
        nm = np.nanmean(null, axis=1) * 100
        out["result"] = {"positions": int(len(R)), "bodies": int(len(set(tks))),
                         "mean_pct": float(R.mean() * 100),
                         "median_pct": float(np.median(R) * 100),
                         "win_rate_pct": float((R > 0).mean() * 100),
                         "mean_hold_sessions": float(L.mean()),
                         "null_mean_pct": float(np.nanmean(nm)),
                         "null_p95": float(np.nanpercentile(nm, 95)),
                         "beats_null": bool(R.mean() * 100 > np.nanpercentile(nm, 95))}
        r = out["result"]
        print(f"[gn] reading {r['mean_pct']:+.2f}% win {r['win_rate_pct']:.1f}% "
              f"hold {r['mean_hold_sessions']:.0f} sessions", flush=True)
        print(f"[gn] matched-timing null in the same body {r['null_mean_pct']:+.2f}% "
              f"p95 {r['null_p95']:+.2f}%   BEATS={r['beats_null']}", flush=True)
    print("\n[gn] benchmarks, kept in the comparison:")
    for b, v in sorted(bench.items()):
        print(f"  {b:4s} fired on {v['enter_rate_pct']:5.2f}% of days, {v['positions']:4d} positions, "
              f"mean {v['mean_pct'] if v['mean_pct'] is None else round(v['mean_pct'],2)}%, "
              f"hold {v['mean_hold']} | buy & hold {v['buy_and_hold_pct']:+.1f}%", flush=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, default=str))
    print(f"\n[gn] written {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
