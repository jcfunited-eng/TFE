"""
ch3_early_capture.py — species structure on the EARLY-CAPTURABLE window
=======================================================================

Provisional detection is ~100% precise at the first 15-min close of the
reveal bar (ch3_early_reveal.json). The earliest honest fill therefore
exists 15 minutes into the reveal bar. This asks the last open
existence question: does the species sign predict the displacement from
that instant to the SAME instant of the next gate — the window a live
CH3 can actually hold?

Same machinery: hourly gates (gate_stream unchanged), bigram species,
strict as-of-issue records (availability = the entry instant of the
NEXT observation's gate, i.e. when its completion is knowable), 60-name
m15 store. Spectrum vs binomial null + band>=0.75 per-year aggregate +
the declared book (10% slices, max-10, fresh $100k/yr).

Usage: python tools/ch3_early_capture.py
Output: artifacts/ch4_uf/ch3_early_capture.json
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

from tools.ch4_uf_spectrum import gate_stream, life_fraction, W  # noqa: E402
from tools.ch3_hourly_law import sp_id  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, "ch3_m15_watchlist.parquet")
OUT = os.path.join(ROOT, "artifacts", "ch4_uf", "ch3_early_capture.json")
PRICE_FLOOR = 5.0
BAND = 0.75
CASH0, SLICE_PCT, MAX_OPEN = 100_000.0, 10.0, 10


def main():
    t0 = time.time()
    df = pd.read_parquet(STORE, columns=["Date", "Symbol", "Close", "Volume"])
    ts = pd.to_datetime(df["Date"]).dt.tz_localize("UTC") \
        .dt.tz_convert("America/New_York")
    mod = ts.dt.hour * 60 + ts.dt.minute
    rth = (mod >= 570) & (mod <= 945) & (ts.dt.weekday <= 4)
    df = df[rth].copy()
    tsr = ts[rth]
    df["hour_key"] = tsr.dt.strftime("%Y%m%d%H").to_numpy()
    df["hkey"] = tsr.dt.strftime("%Y%m%d%H%M").to_numpy()

    obs = []
    for sym, sub in df.groupby("Symbol", sort=True):
        sub = sub.sort_values("hkey")
        hb = sub.groupby("hour_key").agg(
            Close=("Close", "last"), Volume=("Volume", "sum")).reset_index()
        closes = hb["Close"].to_numpy(dtype=float)
        vols = hb["Volume"].to_numpy(dtype=float)
        hkeys = hb["hour_key"].tolist()
        if len(closes) < 5 * W or np.median(closes) < PRICE_FLOOR:
            continue
        if life_fraction(closes)[-1] < 0.90:
            continue
        # first 15-min close (and its minute key) of each hourly bar
        firsts = sub.groupby("hour_key").agg(
            px=("Close", "first"), mk=("hkey", "first"))
        f_px = {k: float(v) for k, v in firsts["px"].items()}
        f_mk = {k: v for k, v in firsts["mk"].items()}
        try:
            gs = gate_stream(hkeys, closes, vols)
        except Exception:
            continue
        for k in range(2, len(gs)):
            _, cls_prev, _, _, _ = gs[k - 2]
            _, cls_cur, _, _, tb_cur = gs[k - 1]
            _, _, _, _, tb_n = gs[k]
            # earliest honest instants: first 15-min close of bar tb+1
            if tb_cur + 1 >= len(hkeys) or tb_n + 1 >= len(hkeys):
                continue
            ek, xk = hkeys[tb_cur + 1], hkeys[tb_n + 1]
            if ek not in f_px or xk not in f_px:
                continue
            ipx, epx = f_px[ek], f_px[xk]
            if ipx < PRICE_FLOOR or ipx <= 0:
                continue
            disp = epx / ipx - 1.0
            obs.append((int(f_mk[xk]), sp_id("bigram", (cls_prev, cls_cur)),
                        disp, sym, int(f_mk[ek]), ipx, epx))
    print(f"observations: {len(obs)} ({time.time()-t0:.0f}s)", flush=True)

    # strict as-of-issue two-stream ledger
    obs.sort(key=lambda x: (x[4], x[3]))            # by issue instant
    comp = sorted(obs, key=lambda x: x[0])          # by availability
    pos, neg = defaultdict(int), defaultdict(int)
    agg = defaultdict(lambda: [0, 0])
    entries = []
    cp = 0
    for avail, sp, disp, sym, issue, ipx, epx in obs:
        while cp < len(comp) and comp[cp][0] < issue:
            csp, cd = comp[cp][1], comp[cp][2]
            if cd > 0:
                pos[csp] += 1
            elif cd < 0:
                neg[csp] += 1
            cp += 1
        p, q = pos[sp], neg[sp]
        n = p + q
        if n >= W:
            f = p / n
            band = max(f, 1 - f)
            pred = 1 if f >= 0.5 else -1
            if band >= BAND and disp != 0:
                y = str(issue // 10 ** 8)
                a = agg[y]
                a[0] += 1 if (disp > 0) == (pred > 0) else 0
                a[1] += 1
                entries.append((issue, avail, sym, pred, ipx, epx))
    while cp < len(comp):
        csp, cd = comp[cp][1], comp[cp][2]
        if cd > 0:
            pos[csp] += 1
        elif cd < 0:
            neg[csp] += 1
        cp += 1

    # spectrum vs null
    species_n = {sp: (pos[sp] + neg[sp], pos[sp] / (pos[sp] + neg[sp]))
                 for sp in pos.keys() | neg.keys() if pos[sp] + neg[sp] >= W}
    cons = np.array([max(f, 1 - f) for _, f in species_n.values()])
    ns = np.array([n for n, _ in species_n.values()])
    tot_p, tot_n = sum(pos.values()), sum(neg.values())
    base = tot_p / max(1, tot_p + tot_n)
    rng = np.random.default_rng(20260731)
    null_cons = []
    for n in ns:
        for d in rng.binomial(n, base, size=20):
            null_cons.append(max(d / n, 1 - d / n))
    edges = [0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0]

    # the declared book on the banded entries
    entries.sort(key=lambda x: (x[0], x[2]))
    import heapq
    books = {}
    for issue, avail, sym, pred, ipx, epx in entries:
        y = str(issue // 10 ** 8)
        b = books.setdefault(y, {"cash": CASH0, "rets": [],
                                 "held": {}, "heap": []})
        while b["heap"] and b["heap"][0][0] <= issue:
            _a, hsym, notl, ret = heapq.heappop(b["heap"])
            b["cash"] += notl * (1 + ret)
            b["rets"].append(100 * ret)
            b["held"].pop(hsym, None)
        if sym in b["held"] or len(b["held"]) >= MAX_OPEN:
            continue
        notl = min(b["cash"] * SLICE_PCT / 100, b["cash"])
        if notl <= 0:
            continue
        ret = (epx / ipx - 1.0) * pred
        b["cash"] -= notl
        b["held"][sym] = notl
        heapq.heappush(b["heap"], (avail, sym, notl, ret))
    by_year_book = {}
    for y in sorted(books):
        b = books[y]
        while b["heap"]:
            _a, hsym, notl, ret = heapq.heappop(b["heap"])
            b["cash"] += notl * (1 + ret)
            b["rets"].append(100 * ret)
        rets = b["rets"]
        wins = sum(1 for r in rets if r > 0)
        by_year_book[y] = {
            "trades": len(rets),
            "wr_pct": round(100 * wins / len(rets), 1) if rets else None,
            "made_usd": round(b["cash"] - CASH0, 2),
            "ret_pct": round(100 * (b["cash"] / CASH0 - 1), 2)}

    result = {
        "frame": "species structure on the early-capturable window "
                 "(first 15-min close of reveal bar -> same instant of "
                 "next gate), hourly gates, strict as-of-issue",
        "observations": len(obs),
        "species_n_ge_W": len(species_n),
        "base_up_rate": round(base, 4),
        "spectrum_real": np.histogram(cons, bins=edges)[0].tolist()
        if len(cons) else [],
        "spectrum_null_mean": (np.histogram(np.array(null_cons),
                                            bins=edges)[0] / 20.0).tolist()
        if null_cons else [],
        "band_aggregate_by_year": {
            y: {"n": v[1], "hit_pct": round(100 * v[0] / v[1], 1)}
            for y, v in sorted(agg.items()) if v[1]},
        "book_by_year": by_year_book,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(result, f, indent=1)
    print(json.dumps(result, indent=1))
    print("filed:", OUT)


if __name__ == "__main__":
    main()
