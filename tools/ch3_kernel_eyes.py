"""
ch3_kernel_eyes.py — point the DSF kernel at the fade's own trades
==================================================================

DECLARED 2026-08-17 BEFORE THE RUN (Joe: "you're not seeing the full
physics of those 3-in-10... look at ALL the data FROM THE DSF,
unflattened, not smooth"). In two weeks of fade construction the DSF
kernel — the project's structural perception — was never applied to
a single fade trade. This does that.

THE QUESTION: among uncovered-name spikes (the blind-spot class),
what distinguishes the ~3-in-10 that KEEP PUMPING (reach the -20%
cut line: close >= 1.20x entry within 5 sessions — the WETO class)
from the ~7-in-10 that snap back?

HYPOTHESIS, stated before looking: continuation follows COHERENT
SUSTAINED DRIVE — the kernel and the raw sequence show days of
building energy before the spike (monotone climb, growing attention,
rising kernel action/sigma). A spike on a quiet base is an impulse
with nothing behind it and snaps. The smoothed prerun scalar cannot
see this; the sequences can.

FEATURES per event, unflattened, all knowable at the event close:
  kernel (compute_l0_v2 on the full daily series):
    sig_t        kernel sigma at the event bar
    sig_slope    sigma change over the last 10 bars
    act_t        per-bar structural action at the event bar
    act_build    mean action last 5 bars / mean action prior 15
    r_t          attention at the event bar
    r_slope      attention change over last 10 bars
  raw sequence (no smoothing):
    up10         count of up-closes in the 10 bars before the event
    hi10         count of new 20-day-high closes in those 10 bars
    vtrend       volume slope sign count over those 10 bars

PROCEDURE (two stages, declared now):
  1. DERIVE on events dated <= 2021-12-31: report both classes'
     feature distributions; pick the single strongest separator and
     its midpoint threshold FROM THIS HALF ONLY.
  2. CONFIRM frozen on 2022+: does the derived rule separate
     grenades from winners in years it never saw? Ships only if yes.

Usage:  python tools/ch3_kernel_eyes.py
Output: artifacts/ch4_uf/ch3_kernel_eyes.json
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.ch4_uf_kernel_v2 import compute_l0_v2  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, "ch4_live_store.parquet")
HERD = os.path.join(ROOT, "artifacts", "ch4_uf", "herd_state_daily.parquet")
OUT = os.path.join(ROOT, "artifacts", "ch4_uf", "ch3_kernel_eyes.json")

EVENT_GAIN, VOL_MULT, PRICE_FLOOR, HOLD, HERD_END = 8.0, 3.0, 5.0, 5, 20260324
GRENADE_X = 1.20            # the -20% cut line: continuation class
DERIVE_END = 20211231

FEATS = ["sig_t", "sig_slope", "act_t", "act_build", "r_t", "r_slope",
         "up10", "hi10", "vtrend", "prerun"]


def main():
    df = pd.read_parquet(STORE, columns=["Date", "Symbol", "Close", "Volume"])
    df["Date"] = pd.to_datetime(df["Date"])
    df["day"] = df["Date"].dt.strftime("%Y%m%d").astype(int)
    herd = pd.read_parquet(HERD, columns=["sym", "date", "gband"])
    herd["date"] = herd["date"].astype(int)
    herd_keys = set(zip(herd["sym"], herd["date"]))

    rows = []
    n_sym = 0
    for sym, s in df.groupby("Symbol", sort=False):
        s = s.sort_values("Date")
        c = s["Close"].to_numpy(dtype=float)
        v = s["Volume"].to_numpy(dtype=float)
        d = s["day"].to_numpy()
        if len(c) < 60:
            continue
        sv = np.concatenate(([0.0], np.cumsum(v)))
        # find this symbol's candidate events first; run the kernel only
        # if it has any (kernel over every symbol is the slow part)
        evs = []
        for t in range(40, len(c) - HOLD):
            if d[t] > HERD_END:
                break
            if c[t] < PRICE_FLOOR or c[t - 1] <= 0:
                continue
            if 100 * (c[t] / c[t - 1] - 1) < EVENT_GAIN:
                continue
            va = (sv[t] - sv[t - 20]) / 20.0
            if va <= 0 or v[t] < VOL_MULT * va:
                continue
            if (sym, int(d[t])) in herd_keys:
                continue                     # covered — not the blind class
            evs.append(t)
        if not evs:
            continue
        try:
            l0 = compute_l0_v2(c, v)
        except Exception:
            continue
        sig, act, r = np.asarray(l0.sigma), np.asarray(l0.perV), np.asarray(l0.r)
        n_sym += 1
        for t in evs:
            entry = c[t]
            grenade = bool(np.any(c[t + 1: t + HOLD + 1] >= GRENADE_X * entry))
            win10 = c[t - 10: t]
            hi = 0
            for j in range(t - 10, t):
                if j >= 20 and c[j] >= np.max(c[j - 20: j]):
                    hi += 1
            vt = int(np.sum(np.diff(v[t - 10: t]) > 0))
            base = c[t - 21] if c[t - 21] > 0 else np.nan
            act_prior = float(np.nanmean(act[t - 20: t - 5]))
            rows.append({
                "sym": sym, "date": int(d[t]), "grenade": grenade,
                "sig_t": float(sig[t]) if np.isfinite(sig[t]) else np.nan,
                "sig_slope": float(sig[t] - sig[t - 10])
                if np.isfinite(sig[t]) and np.isfinite(sig[t - 10]) else np.nan,
                "act_t": float(act[t]) if np.isfinite(act[t]) else np.nan,
                "act_build": float(np.nanmean(act[t - 5: t]) / act_prior)
                if act_prior and np.isfinite(act_prior) and act_prior > 0 else np.nan,
                "r_t": float(r[t]) if np.isfinite(r[t]) else np.nan,
                "r_slope": float(r[t] - r[t - 10])
                if np.isfinite(r[t]) and np.isfinite(r[t - 10]) else np.nan,
                "up10": int(np.sum(np.diff(c[t - 11: t]) > 0)),
                "hi10": hi, "vtrend": vt,
                "prerun": float(100 * (c[t - 1] / base - 1))
                if np.isfinite(base) else np.nan,
            })
    ev = pd.DataFrame(rows)
    print(f"symbols with kernel run: {n_sym}; uncovered events: {len(ev)}; "
          f"grenades: {int(ev['grenade'].sum())} "
          f"({100 * ev['grenade'].mean():.1f}%)")

    derive = ev[ev["date"] <= DERIVE_END]
    confirm = ev[ev["date"] > DERIVE_END]

    def cls_stats(sub):
        g, w = sub[sub["grenade"]], sub[~sub["grenade"]]
        out = {}
        for f in FEATS:
            gm, wm = float(g[f].median()), float(w[f].median())
            gs = float(g[f].std()) or 1.0
            ws = float(w[f].std()) or 1.0
            sep = abs(gm - wm) / ((gs + ws) / 2)
            out[f] = {"grenade_med": round(gm, 4), "winner_med": round(wm, 4),
                      "separation": round(sep, 3)}
        return out

    d_stats = cls_stats(derive)
    best = max(d_stats, key=lambda f: d_stats[f]["separation"])
    thr = (d_stats[best]["grenade_med"] + d_stats[best]["winner_med"]) / 2
    hi_side = d_stats[best]["grenade_med"] > d_stats[best]["winner_med"]

    def rule_perf(sub):
        if len(sub) == 0:
            return {}
        flag = (sub[best] > thr) if hi_side else (sub[best] < thr)
        flagged, passed = sub[flag], sub[~flag]
        return {
            "flagged_n": int(len(flagged)),
            "flagged_grenade_rate_pct": round(
                100 * float(flagged["grenade"].mean()), 1) if len(flagged) else None,
            "passed_n": int(len(passed)),
            "passed_grenade_rate_pct": round(
                100 * float(passed["grenade"].mean()), 1) if len(passed) else None,
            "base_grenade_rate_pct": round(100 * float(sub["grenade"].mean()), 1),
        }

    result = {
        "declared": "exploration on <=2021, single best separator + midpoint "
                    "threshold frozen, confirmed on 2022+; procedure declared "
                    "in docstring before the run",
        "events": {"derive": int(len(derive)), "confirm": int(len(confirm))},
        "derive_feature_table": d_stats,
        "derived_rule": {"feature": best, "threshold": round(thr, 4),
                         "grenade_side": "above" if hi_side else "below"},
        "derive_half_performance": rule_perf(derive),
        "CONFIRM_frozen_2022_plus": rule_perf(confirm),
    }
    json.dump(result, open(OUT, "w"), indent=1)
    print(json.dumps(result, indent=1))
    print("filed:", OUT)


if __name__ == "__main__":
    main()
