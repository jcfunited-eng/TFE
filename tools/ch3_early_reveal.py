"""
ch3_early_reveal.py — provisional boundary detection inside the reveal bar
==========================================================================

The reveal-bar theorem (docs/CH4_LIVE_TIMING_AUDIT_20260731.md) proved
the species law's payout lives inside the reveal bar. This measures the
only physically available capture: during the reveal bar, all
quantities of the closing hourly gate are final EXCEPT kappa(t)/N(t),
which need the reveal bar's close — replaced here by its running
15-minute partial close. Exact kernel math, one provisional term.

For every final hourly boundary(t): at which 15-min sub-bar of the
reveal bar does the provisional flag first fire, how reliable is it
(hit = final boundary confirmed; false = fired but final says no), and
how much of the reveal bar's displacement remains capturable from that
sub-close?

Store: ch3_m15_watchlist.parquet (60 names, 2016-2026).
Output: artifacts/ch4_uf/ch3_early_reveal.json
Usage:  python tools/ch3_early_reveal.py
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.ch4_uf_kernel_v2 import compute_l0_v2, EPS_LOG, W  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, "ch3_m15_watchlist.parquet")
OUT = os.path.join(ROOT, "artifacts", "ch4_uf", "ch3_early_reveal.json")
PRICE_FLOOR = 5.0


def provisional_fire(l0, step2, t, f_part):
    """boundary(t) with kappa(t)/N(t) evaluated from a PARTIAL close of
    the reveal bar t+1 (log price f_part). Exact kernel math."""
    F, dF, sig, kap, r, N = l0.F, l0.dF, l0.sigma, l0.kappa, l0.r, l0.N
    kap_p = abs(f_part - 2.0 * F[t] + F[t - 1])
    n_p = 1 if (sig[t] < 1e-6 and abs(dF[t]) < 1e-6 and kap_p < 1e-6) else 0
    d = (F[t] - F[t - 1], dF[t] - dF[t - 1], sig[t] - sig[t - 1],
         kap_p - kap[t - 1], r[t] - r[t - 1], float(n_p - N[t - 1]))
    step2_p = sum(x * x for x in d)
    w0 = max(1, t - W)
    trail = step2[w0:t]
    thresh = float(np.mean(trail)) if len(trail) else 0.0
    return (step2_p > thresh) or (n_p != N[t - 1])


def main():
    df = pd.read_parquet(STORE, columns=["Date", "Symbol", "Close", "Volume"])
    ts = pd.to_datetime(df["Date"]).dt.tz_localize("UTC") \
        .dt.tz_convert("America/New_York")
    mod = ts.dt.hour * 60 + ts.dt.minute
    rth = (mod >= 570) & (mod <= 945) & (ts.dt.weekday <= 4)
    df = df[rth].copy()
    tsr = ts[rth]
    df["hour_key"] = tsr.dt.strftime("%Y%m%d%H").to_numpy()
    df["sub"] = tsr.dt.minute.to_numpy()

    first_fire = defaultdict(int)      # sub-bar index of first true fire
    confirm = [0, 0]                   # provisional fired anywhere: confirmed / not
    missed = 0                         # final boundary never provisionally fired
    capture = defaultdict(list)       # sub index -> remaining reveal-bar disp (%)
    false_by_sub = defaultdict(int)
    checked = 0

    for sym, sub in df.groupby("Symbol", sort=True):
        sub = sub.sort_values(["hour_key", "sub"])
        # final hourly bars
        hb = sub.groupby("hour_key").agg(
            Close=("Close", "last"), Volume=("Volume", "sum")).reset_index()
        closes = hb["Close"].to_numpy(dtype=float)
        vols = hb["Volume"].to_numpy(dtype=float)
        if len(closes) < 5 * W or np.median(closes) < PRICE_FLOOR:
            continue
        l0 = compute_l0_v2(closes, vols)
        # recover step2 exactly as the kernel builds it
        F, dF, sig, kap, r, N = l0.F, l0.dF, l0.sigma, l0.kappa, l0.r, l0.N
        n = len(F)
        step2 = np.zeros(n)
        for t in range(1, n):
            d = (F[t] - F[t - 1], dF[t] - dF[t - 1], sig[t] - sig[t - 1],
                 kap[t] - kap[t - 1], r[t] - r[t - 1], float(N[t] - N[t - 1]))
            step2[t] = sum(x * x for x in d)
        # per-hour sub-bar closes
        subs_by_hour = {k: g["Close"].to_numpy(dtype=float)
                        for k, g in sub.groupby("hour_key")}
        hour_keys = hb["hour_key"].tolist()
        for t in range(W + 1, n - 2):
            reveal_key = hour_keys[t + 1]
            parts = subs_by_hour.get(reveal_key)
            if parts is None or len(parts) < 2:
                continue
            final = bool(l0.boundary[t])
            checked += 1
            fired_at = None
            for k in range(len(parts) - 1):     # partial closes only
                f_part = float(np.log(parts[k] + EPS_LOG))
                if provisional_fire(l0, step2, t, f_part):
                    fired_at = k
                    break
            if fired_at is not None:
                if final:
                    confirm[0] += 1
                    first_fire[fired_at] += 1
                    reveal_close = closes[t + 1]
                    cap = 100 * (reveal_close / parts[fired_at] - 1.0)
                    capture[fired_at].append(cap)
                else:
                    confirm[1] += 1
                    false_by_sub[fired_at] += 1
            elif final:
                missed += 1

    fires = confirm[0] + confirm[1]
    result = {
        "frame": "provisional hourly-boundary detection from 15-min "
                 "partials inside the (true) reveal bar; exact kernel "
                 "math, one provisional kappa/N term",
        "hours_checked": checked,
        "provisional_fires": fires,
        "precision_pct": round(100 * confirm[0] / fires, 1) if fires else None,
        "boundaries_caught_early": confirm[0],
        "boundaries_missed_by_provisional": missed,
        "recall_pct": round(100 * confirm[0] / (confirm[0] + missed), 1)
        if confirm[0] + missed else None,
        "first_fire_sub_histogram": dict(sorted(first_fire.items())),
        "false_fire_sub_histogram": dict(sorted(false_by_sub.items())),
        "mean_abs_remaining_reveal_disp_pct_by_sub": {
            str(k): round(float(np.mean(np.abs(v))), 3)
            for k, v in sorted(capture.items())},
        "mean_remaining_reveal_disp_pct_by_sub": {
            str(k): round(float(np.mean(v)), 3)
            for k, v in sorted(capture.items())},
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(result, f, indent=1)
    print(json.dumps(result, indent=1))
    print("filed:", OUT)


if __name__ == "__main__":
    main()
