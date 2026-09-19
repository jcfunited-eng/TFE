"""The nine values, at full precision — no averages, no medians, no rounding,
no buckets.

Joseph, 2026-09-19: "can you now just do it on these values alone".

The nine, sourced so that none of them is an average:

    D_k, M_k, R_rev_k, U_star_k, C_k, P_k, B_k   L4, per reading   HIS
    S_UF  := l2_S_k    the per-reading support    (NOT the adapter's
    R_UF  := l3_R_k    the per-reading resonance   lifetime means)

uf_structural_engine reports S_UF and R_UF as means over a body's entire life.
Those are adapter constructions. This file never touches them.

Every field enters at its exact float value. Nothing is rounded, bucketed,
ranked, averaged or smoothed. Where a decision needs a comparison, the
comparison is between two kernel values, or against a value the field itself
takes (0, +/-1, its native maximum).

Provenance of each clause is marked HIS or MINE.

Usage:
  PYTHONHASHSEED=0 python tools/ch2_nine_values_full.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "artifacts" / "ch4_uf" / "full_gate_20260919"
OUT = ROOT / "artifacts" / "ch4_uf" / "ch2_nine_values_full_20260919.json"
BENCH = ["SPY", "QQQ", "DIA", "IWM"]
SEEDS = 200


# --- D_k at resolution per market cap -------------------------------------
# Joseph authorized adjusting epsilon_D: it is the resolution value, and a
# single absolute number applied to every security is why D_k is frozen for
# years in large names (4 changes in SPY's decade).
#
# HIS:  the threshold must scale with the security's size.
# MINE: the size proxy is the day's own dollar volume (close * volume). This
#       repository stores no market cap and no shares outstanding, and the
#       fundamental fetcher would need external API calls. Dollar volume is
#       per-day and exact -- no average, no median, no rounding.
# MINE: DV_REF = $10M/day, the band where D_k resolution was measured highest
#       (28.4% neutral, against 35.4% in the largest band and 45.4% in the
#       smallest). The kernel file is NOT modified; the scaling is applied
#       outside it.
EPSILON_D_BASE = 0.00073          # uf_core/config.py, unchanged on disk
DV_REF = 1.0e7


def scaled_D_k(df: pd.DataFrame) -> np.ndarray:
    """D_k recomputed from the exact per-reading resonance, with the threshold
    scaled per security. Same rule as layer4, one threshold per name."""
    R = df.l3_R_k.values
    dv = df.close.values * df.volume.values
    eps = EPSILON_D_BASE * (DV_REF / np.where(dv > 0, dv, np.nan))
    dR = np.empty_like(R); dR[0] = 0.0; dR[1:] = R[1:] - R[:-1]
    out = np.zeros_like(R)
    out[dR > eps] = 1.0
    out[dR < -eps] = -1.0
    return out


def reading(df: pd.DataFrame, scaled: bool = True):
    """The nine values, his semantics, exact floats."""
    S = df.l2_S_k.values          # support floor        (per reading, not a mean)
    R = df.l3_R_k.values          # resonance            (per reading, not a mean)
    U = df.U_star_k.values        # penalized uncertainty
    D = scaled_D_k(df) if scaled else df.D_k.values   # directional sign
    M = df.M_k.values             # local bend
    RV = df.R_rev_k.values        # reversal
    C = df.C_k.values             # conflict burden
    P = df.P_k.values             # persistence stress
    B = df.B_k.values             # accumulated carry

    # HIS: "U_star_k should be read against support and resonance, not alone."
    viable = (S > U) & (R > U)
    # HIS: "D_k not enough by itself"; "M_k tells whether motion is continuing
    #      or bending back" -- its own zero, no magnitude read as strength.
    motion = (D == 1.0) & (M > 0.0)
    # HIS: "R_rev_k ... a first-class change in state, not a side penalty."
    geometry = RV == 0.0
    # HIS: B_k "carrying stable potential or exhausting it", never collapsed
    #      into a score. MINE: "exhausting" read as the kernel's own previous
    #      reading being higher -- the previous step, not a chosen window.
    Bprev = np.empty_like(B); Bprev[0] = B[0]; Bprev[1:] = B[:-1]
    carry = B >= Bprev
    # HIS: C_k "not a standalone veto", P_k "should not dominate by itself" --
    #      so neither acts alone; only both at their native maxima act.
    burden = ~((C == 3.0) & (P == 2.0))

    enter = viable & motion & geometry & carry & burden

    # The state's end, same semantics, same exact values.
    end = (RV == 1.0) | ((S <= U) & (R <= U)) | (D == -1.0) | (B < Bprev)
    return enter, end, {"viable": viable, "motion": motion, "geometry": geometry,
                        "carry": carry, "burden": burden}


def main() -> int:
    files = sorted(GATE.glob("*.parquet"))
    print(f"[9v] bodies available: {len(files)}", flush=True)
    rets, lens, tks, days = [], [], [], []
    closes, ok_starts = {}, {}
    rates = {k: [] for k in ["viable", "motion", "geometry", "carry", "burden", "enter"]}
    per_bench = {}

    for f in files:
        sym = f.stem
        df = pd.read_parquet(f).reset_index(drop=True)
        if len(df) < 250:
            continue
        enter, end, parts = reading(df)
        for k, v in parts.items():
            rates[k].append(float(v.mean()))
        rates["enter"].append(float(enter.mean()))
        cl = df.close.values
        closes[sym] = cl
        ok_starts[sym] = np.arange(len(cl))
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
            if sym not in BENCH:
                rets.append(cl[xj] / cl[i] - 1.0); lens.append(xj - i)
                tks.append(sym); days.append(df.d.values[i])
            i = x + 1
        if sym in BENCH:
            r = [cl[b] / cl[a] - 1.0 for a, b in taken]
            per_bench[sym] = {
                "positions": len(taken),
                "mean_pct": float(np.mean(r) * 100) if r else None,
                "buy_and_hold_pct": float(cl[-1] / cl[0] - 1.0) * 100,
                "enter_rate_pct": float(enter.mean() * 100),
                "mean_hold": float(np.mean([b - a for a, b in taken])) if taken else None}

    print("\nD_k resolution — Joseph: the only way it stays the same is if the price is flat")
    for sym in BENCH + ["MAN"]:
        p = GATE / f"{sym}.parquet"
        if not p.exists():
            continue
        df = pd.read_parquet(p).reset_index(drop=True)
        old, new = df.D_k.values, scaled_D_k(df)
        px = df.close.values
        print(f"  {sym:4s} {len(df)} sessions, price moved on "
              f"{int((np.diff(px)!=0).sum())} of them | D_k changes: "
              f"kernel-as-shipped {int((np.diff(old)!=0).sum()):4d}  "
              f"scaled-per-size {int((np.diff(new)!=0).sum()):4d}   "
              f"(scaled: {np.mean(new==1)*100:.0f}% +1, {np.mean(new==0)*100:.0f}% 0, "
              f"{np.mean(new==-1)*100:.0f}% -1)", flush=True)

    print("\ncondition firing rates across all bodies (each body's own rate, listed not averaged):")
    for k, v in rates.items():
        a = np.array(v)
        print(f"  {k:9s} fires on: p05 {np.percentile(a,5)*100:5.1f}%  p50 {np.percentile(a,50)*100:5.1f}%  "
              f"p95 {np.percentile(a,95)*100:5.1f}%   bodies where it never fires: {(a==0).sum()}", flush=True)

    R = np.array(rets); L = np.array(lens); T = np.array(tks)
    print(f"\n[9v] positions={len(R)} across {len(set(tks))} bodies "
          f"(benchmarks held out of the pool)", flush=True)
    if not len(R):
        print("[9v] the reading never fired", flush=True)
        return 0

    null = np.full((SEEDS, len(R)), np.nan)
    for t in np.unique(T):
        sel = np.flatnonzero(T == t)
        cl = closes[t]; vs = ok_starts[t]
        cut = np.searchsorted(vs, len(cl) - L[sel] - 1, side="right")
        g = cut > 0
        if not g.any():
            continue
        sg = sel[g]; Lg = L[sel][g]; cg = cut[g]
        rng = np.random.default_rng(int.from_bytes(
            hashlib.blake2b(t.encode(), digest_size=4).digest(), "big"))
        st = vs[(rng.random((SEEDS, len(sg))) * cg).astype(np.int64)]
        null[:, sg] = cl[st + Lg] / cl[st] - 1.0
    nm = np.nanmean(null, axis=1) * 100

    res = {"positions": int(len(R)), "bodies": int(len(set(tks))),
           "mean_pct": float(R.mean() * 100), "median_pct": float(np.median(R) * 100),
           "win_rate_pct": float((R > 0).mean() * 100),
           "mean_hold_sessions": float(L.mean()),
           "null_mean_pct": float(np.nanmean(nm)), "null_p95": float(np.nanpercentile(nm, 95)),
           "beats_null": bool(R.mean() * 100 > np.nanpercentile(nm, 95)),
           "benchmarks": per_bench}
    print(f"[9v] reading {res['mean_pct']:+.2f}% win {res['win_rate_pct']:.1f}% "
          f"hold {res['mean_hold_sessions']:.0f} sessions", flush=True)
    print(f"[9v] matched-timing null inside the same body: {res['null_mean_pct']:+.2f}% "
          f"p95 {res['null_p95']:+.2f}%  BEATS={res['beats_null']}", flush=True)
    print("\n[9v] the benchmarks, kept in the comparison as Joseph asked:")
    for b, v in sorted(per_bench.items()):
        print(f"  {b:4s} reading fired {v['enter_rate_pct']:5.2f}% of sessions, {v['positions']:3d} positions, "
              f"mean {v['mean_pct'] if v['mean_pct'] is None else round(v['mean_pct'],2)}%  "
              f"| buy & hold {v['buy_and_hold_pct']:+.1f}%", flush=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"reading": res, "condition_rates": rates}, indent=2, default=str))
    print(f"\n[9v] written {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
