"""
ch4_uf_cluster_layer.py — cross-structure resonance (the missing physics)
=========================================================================

Both specs define resonance as CROSS-structural — orig §5.0 "alignment of
interpretive features across structural regimes, mosaics, clusters, schema
memory, context"; §5.2 cluster coherence C(𝒢) = (1/|𝒢|)·Σ Res_k; merged
ch06 multi-view fusion with quorum and disagreement gates. Every prior
realization (deployed, preserved lineage, v1, v2 single-symbol chains)
computed resonance per symbol in isolation — the deepest remaining
unfaithfulness after the v2 conformance fixes.

This layer completes it, using the recovered lineage's OWN pre-declared
test (FRACTAL_GATE_COMPLETION T3 "MEADOW LINKAGE" — filed before any of
this work): a vertex event counts only when the FIELD supports it.

DECLARED (before measurement; registry constants only):
  Field coherence   C(t) = mean over symbols of the vertex resonance
                    R_res(t) (orig §5.2, cluster = the evaluated field).
  Field bands       C(t) vs its OWN trailing W=20 days at the pinned
                    0.25/0.75 bands (same convention as every other band
                    in this work). Trailing strictly (excludes today).
  MEADOW ACCUMULATE vertex ignition (URF admitted after ≥2 suppressed
                    gates — the L3-native emergence event) on a day when
                    C(t) ≥ its trailing p75 ("the meadow is coherent").
  MEADOW AVOID      vertex extinction on a day when C(t) ≤ trailing p25.
  Anti-signal       the same vertex events on the OPPOSITE field band —
                    measured and filed with equal weight (falsification).
  Book              identical declared mechanics ($100k, 10% slices, max
                    10, exit first vertex extinction or +20 bars).
  All horizons, per-year splits, price floor $5. Raw output, no tuning.

Causality: C(t) uses only day-t states of all symbols (each causal);
bands trail strictly. A portfolio-level quantity computed from
information available at every close — live-reproducible daily.

Usage: python tools/ch4_uf_cluster_layer.py artifacts/ch4_uf/v2_states_universe5016.npz
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict

import numpy as np

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "artifacts", "ch4_uf")
W = 20
BAND_LO, BAND_HI = 25, 75
HORIZONS = (5, 10, 20, 60)
PRICE_FLOOR = 5.0
CASH0, SLICE, MAX_POS, BOOK_H = 100_000.0, 0.10, 10, 20

COL_R, COL_URF, COL_IGN, COL_EXT, COL_FN, COL_SUF, COL_D, COL_CLOSE = range(8)


def load_states(npz_path):
    z = np.load(npz_path, allow_pickle=False)
    syms = sorted({k[:-7] for k in z.files if k.endswith("__dates")})
    frames = {}
    all_dates = set()
    for s in syms:
        dts = [str(x) for x in z[f"{s}__dates"]]
        frames[s] = (dts, z[f"{s}__mat"])
        all_dates.update(dts)
    dates = sorted(all_dates)
    d_index = {d: i for i, d in enumerate(dates)}
    return frames, dates, d_index


def field_coherence(frames, dates, d_index):
    n = len(dates)
    tot = np.zeros(n)
    cnt = np.zeros(n)
    for s, (dts, mat) in frames.items():
        for j, d in enumerate(dts):
            r = mat[j, COL_R]
            if np.isfinite(r):
                i = d_index[d]
                tot[i] += r
                cnt[i] += 1
    C = np.where(cnt > 0, tot / np.maximum(cnt, 1), np.nan)
    return C, cnt


def field_bands(C):
    n = len(C)
    lo = np.full(n, np.nan)
    hi = np.full(n, np.nan)
    for t in range(n):
        w0 = max(0, t - W)
        win = C[w0:t]
        win = win[np.isfinite(win)]
        if len(win) >= W // 2:
            lo[t] = np.percentile(win, BAND_LO)
            hi[t] = np.percentile(win, BAND_HI)
    return lo, hi


def collect_signals(frames, d_index, C, lo, hi):
    rows = []
    for s, (dts, mat) in frames.items():
        n = len(dts)
        for j in range(n):
            ign = mat[j, COL_IGN] == 1.0
            ext = mat[j, COL_EXT] == 1.0
            if not (ign or ext):
                continue
            px = float(mat[j, COL_CLOSE])
            if not np.isfinite(px) or px < PRICE_FLOOR:
                continue
            i = d_index[dts[j]]
            c, l, h = C[i], lo[i], hi[i]
            if not (np.isfinite(c) and np.isfinite(l) and np.isfinite(h)):
                continue
            meadow_hi = c >= h
            meadow_lo = c <= l
            if ign:
                channel = ("meadow" if meadow_hi else
                           ("anti" if meadow_lo else "mid"))
                side = "ACCUMULATE"
            else:
                channel = ("meadow" if meadow_lo else
                           ("anti" if meadow_hi else "mid"))
                side = "AVOID"
            row = {"symbol": s, "date": dts[j], "j": j, "channel": channel,
                   "side": side, "close": px}
            for hz in HORIZONS:
                row[f"ret_{hz}"] = (float(mat[j + hz, COL_CLOSE] / px - 1.0)
                                    if j + hz < n and np.isfinite(mat[j + hz, COL_CLOSE])
                                    else None)
            rows.append(row)
    return rows


def summarize(rows):
    out = {}
    for ch in ("meadow", "anti", "mid"):
        for side in ("ACCUMULATE", "AVOID"):
            sel = [r for r in rows if r["channel"] == ch and r["side"] == side]
            stats = {"signals": len(sel)}
            for hz in HORIZONS:
                vals = [r[f"ret_{hz}"] for r in sel if r[f"ret_{hz}"] is not None]
                if vals:
                    a = np.array(vals)
                    stats[f"h{hz}"] = {"n": len(vals),
                                       "wr_pct": round(100 * float((a > 0).mean()), 2),
                                       "mean_pct": round(100 * float(a.mean()), 3)}
            by_year = defaultdict(list)
            for r in sel:
                if r["ret_20"] is not None:
                    by_year[r["date"][:4]].append(r["ret_20"])
            stats["by_year_h20"] = {
                y: {"n": len(v),
                    "wr_pct": round(100 * float((np.array(v) > 0).mean()), 2),
                    "mean_pct": round(100 * float(np.mean(v)), 3)}
                for y, v in sorted(by_year.items())}
            out[f"{ch}:{side}"] = stats
    return out


def run_book(rows, frames):
    entries = sorted([r for r in rows if r["channel"] == "meadow"
                      and r["side"] == "ACCUMULATE"],
                     key=lambda r: (r["date"], r["symbol"]))
    ext_days = {}
    for s, (dts, mat) in frames.items():
        ext_days[s] = {dts[j] for j in range(len(dts)) if mat[j, COL_EXT] == 1.0}
    idx_maps = {s: {d: j for j, d in enumerate(dts)}
                for s, (dts, mat) in frames.items()}

    all_dates = sorted({d for s, (dts, _) in frames.items() for d in dts})
    ent_by_date = defaultdict(list)
    for r in entries:
        ent_by_date[r["date"]].append(r)

    cash = CASH0
    pos = {}
    closed = []
    eq_curve = []
    for d in all_dates:
        for s in sorted(list(pos.keys())):
            p = pos[s]
            j = idx_maps[s].get(d)
            if j is None:
                continue
            age = j - p["j_in"]
            px = float(frames[s][1][j, COL_CLOSE])
            if not np.isfinite(px):
                continue
            if d in ext_days[s] or age >= BOOK_H or j == len(frames[s][0]) - 1:
                cash += p["sh"] * px
                closed.append({"symbol": s, "in": p["d_in"], "out": d,
                               "ret_pct": round(100 * (px / p["px_in"] - 1), 3),
                               "reason": "EXT" if d in ext_days[s] else "HZN"})
                del pos[s]
        for r in ent_by_date.get(d, []):
            s = r["symbol"]
            if s in pos or len(pos) >= MAX_POS:
                continue
            eq = cash + sum(p2["sh"] * float(frames[s2][1][idx_maps[s2].get(d, p2["j_in"]), COL_CLOSE])
                            for s2, p2 in pos.items()
                            if np.isfinite(frames[s2][1][idx_maps[s2].get(d, p2["j_in"]), COL_CLOSE]))
            budget = min(cash, SLICE * eq)
            if budget <= 0:
                continue
            pos[s] = {"sh": budget / r["close"], "px_in": r["close"],
                      "d_in": d, "j_in": r["j"]}
            cash -= budget
        eq = cash + sum(p2["sh"] * float(frames[s2][1][idx_maps[s2].get(d, p2["j_in"]), COL_CLOSE])
                        for s2, p2 in pos.items()
                        if np.isfinite(frames[s2][1][idx_maps[s2].get(d, p2["j_in"]), COL_CLOSE]))
        eq_curve.append((d, eq))

    rets = [t["ret_pct"] for t in closed]
    by_year = {}
    if eq_curve:
        prev = CASH0
        ys = CASH0
        cy = eq_curve[0][0][:4]
        for d, e in eq_curve:
            if d[:4] != cy:
                by_year[cy] = round(100 * (prev / ys - 1), 2)
                cy = d[:4]
                ys = prev
            prev = e
        by_year[cy] = round(100 * (prev / ys - 1), 2)
    return {"closed_trades": len(closed),
            "wr_pct": round(100 * sum(1 for x in rets if x > 0) / len(rets), 2) if rets else None,
            "mean_trade_pct": round(float(np.mean(rets)), 3) if rets else None,
            "final_equity": round(eq_curve[-1][1], 2) if eq_curve else CASH0,
            "total_return_pct": round(100 * (eq_curve[-1][1] / CASH0 - 1), 2) if eq_curve else 0.0,
            "by_year": by_year,
            "trades": closed}


def main():
    npz = sys.argv[1]
    frames, dates, d_index = load_states(npz)
    print(f"{len(frames)} symbols, {len(dates)} field days")
    C, cnt = field_coherence(frames, dates, d_index)
    lo, hi = field_bands(C)
    rows = collect_signals(frames, d_index, C, lo, hi)
    summary = summarize(rows)
    book = run_book(rows, frames)
    result = {
        "layer": "cross-structure resonance (meadow linkage, orig §5.2 + lineage T3)",
        "declared": "vertex ignition/extinction admitted by field-coherence bands "
                    f"(trailing W={W} days, pinned {BAND_LO}/{BAND_HI} bands); "
                    "anti-band and mid-band filed with equal weight",
        "field_days": int(np.isfinite(C).sum()),
        "signals": summary,
        "book_meadow": {k: v for k, v in book.items() if k != "trades"},
    }
    out = os.path.join(OUT_DIR, "ch4_uf_cluster_layer.json")
    with open(out, "w") as f:
        json.dump({**result, "book_trades": book["trades"]}, f, indent=1)
    print(json.dumps(result, indent=1))
    print("filed:", out)


if __name__ == "__main__":
    main()
