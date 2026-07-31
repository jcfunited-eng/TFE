"""
ch4_uf_reverse_census.py — reverse engineering: from profits to structures
==========================================================================

Joe's inversion (2026-07-31): stop defining structures and grading them
forward (quant). Take the actual RISES and FALLS across all tickers as
ground truth, point the kernel at those exact periods, and catalog the
structures present during birth, body, and death of each move. The
recognition table — which structural states are (near-)universal in
rises and (near-)absent in falls — IS the physics; harvesting follows
from recognizing the signature as it forms.

DECLARED:
  Segments   — zigzag decomposition of each ticker's close path into
               alternating rises and falls. Pivot significance is
               SELF-SCALED: a reversal counts when the countermove
               exceeds 4x the trailing-20-day median absolute daily move
               (4 = the coarsest pinned lattice constant, 20 = W; no
               hand-picked percentages). All segments kept; census
               reported by amplitude bucket so no size threshold exists.
  Phases     — BIRTH = first 3 bars of a segment, DEATH = last 3 bars,
               BODY = the rest (3 = the pinned lattice ladder length).
  Structures — per bar, the kernel state from the conformant v2 chain:
               (D sign, URF>0, regime, ignition, extinction, F_n band,
               S_UF band) with bands vs the vertex's trailing W=20
               events at the pinned 25/75 quantiles.
  Census     — P(state | rise-birth), P(state | fall-birth), etc. vs the
               all-days baseline: lift and coverage. Also the joint
               signature census (full state tuple occupancy).
  Universe   — eligible field (LIFE >= 0.90, $5 floor), decade store.

Pure description of realized moves. No prediction, no trading, no
thresholds tuned. Output: the recognition table, filed raw.

Usage: CH4_STORE=... python tools/ch4_uf_reverse_census.py [N]
"""

from __future__ import annotations

import json
import os
import sys
import time
from collections import defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.ch4_uf_kernel_v2 import replay_symbol_v2  # noqa: E402
from tools.ch4_uf_spectrum import life_fraction, W  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARQUET = os.environ.get("CH4_STORE") or os.path.join(ROOT, "quarantine_12k_universe_ext.parquet")
OUT_DIR = os.path.join(ROOT, "artifacts", "ch4_uf")
LIFE_MIN = 0.90
PRICE_FLOOR = 5.0
MIN_BARS = 1250
REV_MULT = 4          # coarsest pinned lattice constant
PHASE_LEN = 3         # pinned ladder length


def zigzag(closes):
    """Self-scaled zigzag: reversal when countermove > REV_MULT x
    trailing-W median |daily move|. Returns pivot index list."""
    n = len(closes)
    if n < W + 2:
        return []
    moves = np.abs(np.diff(closes))
    piv = [0]
    direction = 0
    ext_i = 0
    for t in range(1, n):
        w0 = max(0, t - W)
        med = float(np.median(moves[w0:t])) if t > w0 else 0.0
        thresh = REV_MULT * max(med, 1e-9)
        if direction >= 0 and closes[t] > closes[ext_i]:
            ext_i = t
            direction = 1
        elif direction <= 0 and closes[t] < closes[ext_i]:
            ext_i = t
            direction = -1 if direction != 0 else -1
        if direction == 1 and closes[ext_i] - closes[t] > thresh:
            piv.append(ext_i)
            direction = -1
            ext_i = t
        elif direction == -1 and closes[t] - closes[ext_i] > thresh:
            piv.append(ext_i)
            direction = 1
            ext_i = t
    if piv[-1] != n - 1:
        piv.append(n - 1)
    return sorted(set(piv))


def state_key(s, fn_band, suf_band):
    return (int(np.sign(s.D_k)), int(s.URF > 0), s.regime[:4],
            int(s.ignition), int(s.extinction), fn_band, suf_band)


def band_of(x, lo, hi):
    if not (np.isfinite(lo) and np.isfinite(hi) and np.isfinite(x)):
        return "?"
    return "L" if x <= lo else ("H" if x >= hi else "M")


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10 ** 9
    df = pd.read_parquet(PARQUET, columns=["Date", "Symbol", "Close", "Volume"])
    df["Date"] = pd.to_datetime(df["Date"])
    g = df.groupby("Symbol")["Close"]
    stats = pd.DataFrame({"bars": g.size(), "med": g.median()})
    uni = sorted(stats[(stats["bars"] >= MIN_BARS)
                       & (stats["med"] >= PRICE_FLOOR)].index.tolist())[:limit]
    print(f"universe: {len(uni)}")

    census = defaultdict(lambda: defaultdict(int))   # context -> state -> n
    seg_counts = defaultdict(int)
    amp_buckets = defaultdict(int)
    t0 = time.time()
    done = 0
    for i, sym in enumerate(uni):
        sub = df[df["Symbol"] == sym].sort_values("Date")
        dates = sub["Date"].dt.date.tolist()
        closes = sub["Close"].to_numpy(dtype=float)
        vols = sub["Volume"].to_numpy(dtype=float)
        lf = life_fraction(closes)
        if lf[-1] < LIFE_MIN:
            continue
        try:
            states = replay_symbol_v2(dates, closes, vols, warmup=60)
        except Exception:
            continue
        done += 1
        # trailing bands for F_n / S_UF per bar
        fn_series = np.array([s.F_n if s else np.nan for s in states])
        suf_series = np.array([s.S_UF if s else np.nan for s in states])

        def tail_bands(series, t):
            w0 = max(0, t - W)
            win = series[w0:t]
            win = win[np.isfinite(win)]
            if len(win) < W // 2:
                return (np.nan, np.nan)
            return (np.percentile(win, 25), np.percentile(win, 75))

        piv = zigzag(closes)
        for a, b in zip(piv[:-1], piv[1:]):
            if b <= a or closes[a] <= 0:
                continue
            amp = 100 * (closes[b] / closes[a] - 1.0)
            kind = "rise" if amp > 0 else "fall"
            bucket = ("xl" if abs(amp) >= 20 else
                      "lg" if abs(amp) >= 10 else
                      "md" if abs(amp) >= 5 else "sm")
            seg_counts[kind] += 1
            amp_buckets[f"{kind}_{bucket}"] += 1
            span = b - a
            for t in range(a, b + 1):
                s = states[t]
                if s is None or closes[t] < PRICE_FLOOR:
                    continue
                lo_f, hi_f = tail_bands(fn_series, t)
                lo_s, hi_s = tail_bands(suf_series, t)
                key = state_key(s, band_of(s.F_n, lo_f, hi_f),
                                band_of(s.S_UF, lo_s, hi_s))
                phase = ("birth" if t - a < PHASE_LEN else
                         ("death" if b - t < PHASE_LEN else "body"))
                census[f"{kind}_{bucket}_{phase}"][key] += 1
                census[f"{kind}_all_{phase}"][key] += 1
                census["baseline_all"][key] += 1
        if (i + 1) % 500 == 0:
            print(f"  [{i+1}/{len(uni)}] segs={dict(seg_counts)} {time.time()-t0:.0f}s",
                  flush=True)

    # recognition table: for the decisive contexts, top states by lift
    base_tot = sum(census["baseline_all"].values())
    base_p = {k: v / base_tot for k, v in census["baseline_all"].items()}
    out = {"universe_done": done, "segments": dict(seg_counts),
           "amplitude_buckets": dict(amp_buckets), "contexts": {}}
    for ctx in sorted(census.keys()):
        if ctx == "baseline_all":
            continue
        tot = sum(census[ctx].values())
        if tot < 500:
            continue
        rows = []
        for k, v in sorted(census[ctx].items(), key=lambda kv: -kv[1])[:12]:
            p = v / tot
            lift = p / max(base_p.get(k, 1e-12), 1e-12)
            rows.append({"state(D,URF,reg,ign,ext,Fn,SUF)": str(k),
                         "share_pct": round(100 * p, 2),
                         "lift_vs_baseline": round(lift, 2)})
        out["contexts"][ctx] = {"n_bar_days": tot, "top_states": rows}

    path = os.path.join(OUT_DIR, "ch4_uf_reverse_census.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps({k: out[k] for k in ["universe_done", "segments", "amplitude_buckets"]}, indent=1))
    print("filed:", path)


if __name__ == "__main__":
    main()
