"""
ch4_uf_multiscale.py — fractal resolution ladder over the conformant kernel
===========================================================================

Joe's directive (2026-07-30): resolution must scale with structure size —
large, stable structures are invisible at native resolution ("they'll
look like glass"); change resolution and the prominent positive
structures appear. The spec is fractal by design (Fractal Mosaic Model;
multi-resolution partition signatures; operational fractal gating) — this
pass runs the SAME conformant v2 chain, unmodified, at three field
resolutions and takes their structural conjunction.

DECLARED (before measurement; registry constants only; the ladder is the
two pinned windows):
  Resolutions  k ∈ {1 (native), 5 (NEIGH), 20 (W)} — fixed-phase block
               sampling anchored at series start: block j = bars
               [j·k, (j+1)·k); close = block-end close, volume = block
               sum. Only COMPLETE blocks exist for the chain (the forming
               block is the coarse forming bar — excluded, closed-bar
               rule). Fixed phase ⇒ block content never changes as
               history grows ⇒ causal.
  Coarse state at day t = the k-chain through the last complete block
               ending at or before t.
  DIAMOND CONJUNCTION (the structure visible across the ladder):
    ACCUMULATE — native ignition at t (emergence event) while BOTH
               coarse scales (5, 20) show an admitted, building arc:
               URF > 0 ∧ D = +1 at each; vertex ELIGIBLE (LIFE ≥ 0.90,
               in-repo principle) and close ≥ $5.
    AVOID      — native extinction at t while both coarse scales show
               URF = 0 ∨ D = −1 (mirror), same eligibility.
  Controls filed with equal weight: native ignition WITHOUT coarse
               support ("glass" — the same event when the big arc is
               absent), and coarse support WITHOUT any native event
               (arc-only days, sampled at each coarse block close).
  Book       — identical declared mechanics ($100k, 10% slices, max 10,
               exit first native extinction or +20 bars, force-close at
               end). Whole-span + per-year.

Raw output. No thresholds tuned. Diligence checks: the coarse chains are
the SAME engine (no re-implementation); a causality assertion re-derives
sampled conjunction days from truncated inputs.

Usage:
  python tools/ch4_uf_multiscale.py            # full eligible universe
  python tools/ch4_uf_multiscale.py TEST       # 12-symbol smoke + causality
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.ch4_uf_kernel_v2 import replay_symbol_v2  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARQUET = os.path.join(ROOT, "quarantine_12k_universe.parquet")
OUT_DIR = os.path.join(ROOT, "artifacts", "ch4_uf")
SCALES = (5, 20)
LIFE_MIN = 0.90
PRICE_FLOOR = 5.0
MIN_BARS = 1250
HORIZONS = (5, 10, 20, 60)
WARMUP = 60
CASH0, SLICE, MAX_POS, BOOK_H = 100_000.0, 0.10, 10, 20


def life_fraction(closes: np.ndarray) -> np.ndarray:
    n = len(closes)
    moved = np.zeros(n)
    if n > 1:
        moved[1:] = (np.abs(np.diff(closes)) > 0).astype(float)
    return np.cumsum(moved) / np.maximum(np.arange(n), 1)


def coarse_series(dates, closes, vols, k):
    """Fixed-phase complete blocks: end-close, summed volume, end-date."""
    n = len(closes)
    m = n // k
    idx_end = [(j + 1) * k - 1 for j in range(m)]
    c = np.array([closes[i] for i in idx_end])
    v = None
    if vols is not None:
        v = np.array([float(np.sum(vols[j * k:(j + 1) * k])) for j in range(m)])
    d = [dates[i] for i in idx_end]
    return d, c, v, np.array(idx_end)


def coarse_flags(dates, closes, vols, k):
    """Per NATIVE day t: (URF>0 ∧ D=+1) and (URF==0 ∨ D=−1) of the
    k-chain through the last complete block ending ≤ t."""
    d, c, v, idx_end = coarse_series(dates, closes, vols, k)
    n = len(closes)
    up = np.zeros(n, dtype=bool)
    down = np.zeros(n, dtype=bool)
    if len(c) < 30:
        return up, down
    states = replay_symbol_v2(d, c, v, warmup=min(25, len(c) - 2))
    # per coarse block j: flags from its state
    blk_up = np.zeros(len(c), dtype=bool)
    blk_dn = np.zeros(len(c), dtype=bool)
    for j, s in enumerate(states):
        if s is not None:
            blk_up[j] = (s.URF > 0.0) and (s.D_k == 1)
            blk_dn[j] = (s.URF == 0.0) or (s.D_k == -1)
    # map to native days — FINALIZED blocks only: block j's curvature
    # (and hence its chain state) needs block j+1, so j is usable at
    # native day t only once idx_end[j+1] <= t. Never uses a state that
    # could change later; up-to-2k publication lag is the honest price
    # of block physics. (Fixes a look-ahead leak caught in self-audit.)
    j = -1
    for t in range(n):
        while j + 1 < len(idx_end) - 1 and idx_end[j + 2] <= t:
            j += 1
        # invariant: block j is usable iff its successor j+1 is complete
        if j >= 0 and idx_end[j + 1] <= t:
            up[t] = blk_up[j]
            down[t] = blk_dn[j]
    return up, down


def process_symbol(sym, dates, closes, vols, native_ign, native_ext):
    lf = life_fraction(closes)
    ups, dns = {}, {}
    for k in SCALES:
        ups[k], dns[k] = coarse_flags(dates, closes, vols, k)
    n = len(closes)
    rows = []
    for t in range(WARMUP, n):
        if lf[t] < LIFE_MIN or closes[t] < PRICE_FLOOR:
            continue
        coarse_up = all(ups[k][t] for k in SCALES)
        coarse_dn = all(dns[k][t] for k in SCALES)
        side = None
        channel = None
        if native_ign[t]:
            side = "ACCUMULATE"
            channel = "diamond" if coarse_up else ("glass" if coarse_dn else "mid")
        elif native_ext[t]:
            side = "AVOID"
            channel = "diamond" if coarse_dn else ("glass" if coarse_up else "mid")
        if side is None:
            continue
        row = {"symbol": sym, "date": str(dates[t]), "t": t,
               "side": side, "channel": channel, "close": float(closes[t])}
        for h in HORIZONS:
            row[f"ret_{h}"] = (float(closes[t + h] / closes[t] - 1.0)
                               if t + h < n else None)
        rows.append(row)
    return rows


def summarize(rows):
    out = {}
    for ch in ("diamond", "glass", "mid"):
        for side in ("ACCUMULATE", "AVOID"):
            sel = [r for r in rows if r["channel"] == ch and r["side"] == side]
            stats = {"signals": len(sel)}
            for h in HORIZONS:
                vals = [r[f"ret_{h}"] for r in sel if r[f"ret_{h}"] is not None]
                if vals:
                    a = np.array(vals)
                    stats[f"h{h}"] = {"n": len(vals),
                                      "wr_pct": round(100 * float((a > 0).mean()), 2),
                                      "mean_pct": round(100 * float(a.mean()), 3)}
            by = defaultdict(list)
            for r in sel:
                if r["ret_20"] is not None:
                    by[r["date"][:4]].append(r["ret_20"])
            stats["by_year_h20"] = {y: {"n": len(v),
                                        "wr_pct": round(100 * float((np.array(v) > 0).mean()), 2),
                                        "mean_pct": round(100 * float(np.mean(v)), 3)}
                                    for y, v in sorted(by.items())}
            out[f"{ch}:{side}"] = stats
    return out


def run_book(rows, frames):
    entries = sorted([r for r in rows if r["channel"] == "diamond"
                      and r["side"] == "ACCUMULATE"],
                     key=lambda r: (r["date"], r["symbol"]))
    idx_maps = {s: {str(d): j for j, d in enumerate(f[0])} for s, f in frames.items()}
    ext_sets = {s: f[3] for s, f in frames.items()}
    all_dates = sorted({str(d) for s, f in frames.items() for d in f[0]})
    ent_by = defaultdict(list)
    for r in entries:
        ent_by[r["date"]].append(r)
    cash, pos, closed, curve = CASH0, {}, [], []
    for d in all_dates:
        for s in sorted(list(pos.keys())):
            p = pos[s]
            j = idx_maps[s].get(d)
            if j is None:
                continue
            closes = frames[s][1]
            age = j - p["j_in"]
            px = float(closes[j])
            if j in ext_sets[s] or age >= BOOK_H or j == len(closes) - 1:
                cash += p["sh"] * px
                closed.append({"symbol": s, "in": p["d_in"], "out": d,
                               "ret_pct": round(100 * (px / p["px_in"] - 1), 3),
                               "reason": "EXT" if j in ext_sets[s] else "HZN"})
                del pos[s]
        for r in ent_by.get(d, []):
            s = r["symbol"]
            if s in pos or len(pos) >= MAX_POS:
                continue
            eq = cash + sum(p2["sh"] * float(frames[s2][1][idx_maps[s2].get(d, p2["j_in"])])
                            for s2, p2 in pos.items())
            budget = min(cash, SLICE * eq)
            if budget <= 0:
                continue
            pos[s] = {"sh": budget / r["close"], "px_in": r["close"],
                      "d_in": d, "j_in": r["t"]}
            cash -= budget
        eq = cash + sum(p2["sh"] * float(frames[s2][1][idx_maps[s2].get(d, p2["j_in"])])
                        for s2, p2 in pos.items())
        curve.append((d, eq))
    rets = [t["ret_pct"] for t in closed]
    by_year = {}
    if curve:
        prev, ys, cy = CASH0, CASH0, curve[0][0][:4]
        for d, e in curve:
            if d[:4] != cy:
                by_year[cy] = round(100 * (prev / ys - 1), 2)
                cy, ys = d[:4], prev
            prev = e
        by_year[cy] = round(100 * (prev / ys - 1), 2)
    return {"closed_trades": len(closed),
            "wr_pct": round(100 * sum(1 for x in rets if x > 0) / len(rets), 2) if rets else None,
            "mean_trade_pct": round(float(np.mean(rets)), 3) if rets else None,
            "final_equity": round(curve[-1][1], 2) if curve else CASH0,
            "total_return_pct": round(100 * (curve[-1][1] / CASH0 - 1), 2) if curve else 0.0,
            "by_year": by_year, "trades": closed}


def main():
    test = len(sys.argv) > 1 and sys.argv[1].upper() == "TEST"
    df = pd.read_parquet(PARQUET, columns=["Date", "Symbol", "Close", "Volume"])
    df["Date"] = pd.to_datetime(df["Date"])
    g = df.groupby("Symbol")["Close"]
    stats = pd.DataFrame({"bars": g.size(), "med": g.median()})
    universe = sorted(stats[(stats["bars"] >= MIN_BARS)
                            & (stats["med"] >= PRICE_FLOOR)].index.tolist())
    if test:
        universe = universe[:12]
    print(f"universe: {len(universe)} symbols")

    all_rows = []
    frames = {}
    import time
    t0 = time.time()
    for i, sym in enumerate(universe):
        sub = df[df["Symbol"] == sym].sort_values("Date")
        dates = sub["Date"].dt.date.tolist()
        closes = sub["Close"].to_numpy(dtype=float)
        vols = sub["Volume"].to_numpy(dtype=float)
        try:
            states = replay_symbol_v2(dates, closes, vols, warmup=WARMUP)
            ign = np.array([1.0 if (s and s.ignition) else 0.0 for s in states])
            ext = np.array([1.0 if (s and s.extinction) else 0.0 for s in states])
            rows = process_symbol(sym, dates, closes, vols, ign, ext)
        except Exception as e:
            print(f"  {sym}: FAILED {e}")
            continue
        all_rows.extend(rows)
        frames[sym] = (dates, closes, vols,
                       {j for j in range(len(ext)) if ext[j] == 1.0})
        if (i + 1) % 100 == 0 or i == len(universe) - 1:
            print(f"  [{i+1}/{len(universe)}] {sym} rows={len(all_rows)} "
                  f"elapsed={time.time()-t0:.0f}s", flush=True)

    if test:
        # causality: re-derive sampled diamond days from truncated inputs
        checked = 0
        for r in all_rows[:200]:
            if r["channel"] != "diamond":
                continue
            sym, t = r["symbol"], r["t"]
            dates, closes, vols, _ = frames[sym]
            states_tr = replay_symbol_v2(dates[: t + 1], closes[: t + 1],
                                         vols[: t + 1], warmup=t)
            ign_tr = bool(states_tr[t] and states_tr[t].ignition)
            ext_tr = bool(states_tr[t] and states_tr[t].extinction)
            ups = {}
            dns = {}
            for k in SCALES:
                u, dn = coarse_flags(dates[: t + 1], closes[: t + 1], vols[: t + 1], k)
                ups[k], dns[k] = u[t], dn[t]
            side_tr = "ACCUMULATE" if ign_tr else ("AVOID" if ext_tr else None)
            cu = all(ups[k] for k in SCALES)
            cd = all(dns[k] for k in SCALES)
            ch_tr = None
            if side_tr == "ACCUMULATE":
                ch_tr = "diamond" if cu else ("glass" if cd else "mid")
            elif side_tr == "AVOID":
                ch_tr = "diamond" if cd else ("glass" if cu else "mid")
            assert side_tr == r["side"] and ch_tr == r["channel"], \
                f"MULTISCALE CAUSALITY VIOLATION {sym}@{t}: {side_tr}/{ch_tr} vs {r['side']}/{r['channel']}"
            checked += 1
            if checked >= 30:
                break
        # also check non-diamond channels (leak shows up as channel drift)
        others = [r for r in all_rows if r["channel"] != "diamond"][:10]
        for r in others:
            sym, t = r["symbol"], r["t"]
            dates, closes, vols, _ = frames[sym]
            ups = {}
            dns = {}
            for k in SCALES:
                u, dn = coarse_flags(dates[: t + 1], closes[: t + 1], vols[: t + 1], k)
                ups[k], dns[k] = u[t], dn[t]
            cu = all(ups[k] for k in SCALES)
            cd = all(dns[k] for k in SCALES)
            if r["side"] == "ACCUMULATE":
                ch_tr = "diamond" if cu else ("glass" if cd else "mid")
            else:
                ch_tr = "diamond" if cd else ("glass" if cu else "mid")
            assert ch_tr == r["channel"], \
                f"MULTISCALE CAUSALITY VIOLATION {sym}@{t}: {ch_tr} vs {r['channel']}"
            checked += 1
        print(f"causality on {checked} sampled days (all channels): OK")

    summary = summarize(all_rows)
    book = run_book(all_rows, frames)
    result = {
        "layer": "fractal resolution ladder (native + 5 + 20) over conformant v2",
        "declared": "diamond = native emergence inside a coarse-admitted building "
                    "arc at BOTH pinned scales; glass/mid controls filed equally; "
                    "LIFE >= 0.90 eligibility; $5 floor; no tuned constants",
        "symbols": len(frames),
        "signals": summary,
        "book_diamond": {k: v for k, v in book.items() if k != "trades"},
    }
    tag = "test" if test else "full"
    out = os.path.join(OUT_DIR, f"ch4_uf_multiscale_{tag}.json")
    with open(out, "w") as f:
        json.dump({**result, "book_trades": book["trades"]}, f, indent=1)
    print(json.dumps({k: v for k, v in result.items() if k != "signals"}, indent=1))
    print(json.dumps(summary, indent=1)[:3000])
    print("filed:", out)


if __name__ == "__main__":
    main()
