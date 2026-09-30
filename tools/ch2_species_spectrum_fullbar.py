"""The species spectrum on the full-bar canon kernel at herd resolution.
Declared 2026-09-30 before running. Joe: "let's see where it goes."

FRAME (Joe, 2026-07-30, unchanged): every gate is a geometric object with a
CLASS; consecutive classes form SPECIES; the field accumulates a causal
SCHEMA MEMORY of how each species completes; the SPECTRUM is the catalog
of species by completion consistency against the binomial null. Price
enters only afterwards, as the L5 translation. No conditional-return scan.

GATE STREAM   the canon kernel (tools/canon_kernel_causal.py) on the raw
              bar (O,H,L,C,V); boundaries at the HERD resolution
              (tools/ch2_herd_census.herd_state: 3.77 x the median bar of
              the stock's own cell that day). Closed gates only. Gate k =
              bars [t_a, t_b); its end is knowable at close t_b + 1.
GATE CLASS    the full projection signature of (T, V, R) — each component
              first self-scaled by its own trailing-20-gate median (the
              July self-audit fix, causal), then quantized on the pinned
              lattices (1,1,1),(2,2,2),(4,4,4) — together with the gate's
              displacement sign: close at its last bar vs the close before
              it began.
SPECIES       bigram (class_{k-1}, class_k); also "pooled" (coarsest
              lattice term + sign) so records fatten.
COMPLETION    the NEXT gate's displacement sign. Available at that gate's
              end (close t_b_next + 1). Schema memory accumulated field-wide
              in strict global order of availability; a species' stats at
              any moment contain only completions already available.
SPECTRUM      species with n >= 20 causal occurrences: consistency =
              share of the majority outcome, histogram vs the binomial
              null at the field base rate (20 draws per species, seed
              20260730). Per-year species-count census.
THE TEST      every causal prediction issued by a species with n >= 20
              and live consistency >= 0.75 at issue: hit rate vs the
              field base rate, PER YEAR (Joe's standard), both alphabets.
L5 LEDGER     enter long at a band-UP prediction (issue close = close at
              t_b_cur + 1, the first close after the gate's end is
              knowable); exit at the first later DOWN-majority prediction
              for that name (n >= 20) at ITS issue close; force-close at the
              last price. One position per name. Per year: trades, win
              rate, sum of returns on $1 per trade. Tradeable filter
              (tools/ch2_canon_census.tradeable_flags) at issue.
OUTPUT        artifacts/ch4_uf/ch2_species_spectrum_fullbar.json
Nothing tuned. Filed either way.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

W = 20
BAND = 0.75
LATTICES = ((1.0, 1.0, 1.0), (2.0, 2.0, 2.0), (4.0, 4.0, 4.0))
OUT = ROOT / "artifacts" / "ch4_uf" / "ch2_species_spectrum_fullbar.json"
_TAU = {}
_FIELD = "bar"
FIELDS = {"bar": ("Open", "High", "Low", "Close", "Volume"), "ohlc_r": ("Open", "High", "Low", "Close")}


def _init(tau_map, field):
    global _TAU, _FIELD
    _TAU, _FIELD = tau_map, field


def gate_stream(symbol, df):
    """Closed gates with class, displacement, causal issue price/date and tradeability at issue."""
    from canon_kernel_causal import readings
    from ch2_canon_census import tradeable_flags
    df = df.sort_values("Date").reset_index(drop=True)
    F = df[list(FIELDS[_FIELD])].values.astype(float)
    close = df.Close.values.astype(float); n = len(close)
    dates = df.Date.values
    rel = None
    if _FIELD == "ohlc_r":                     # what-if (MINE): volume enters as the canon's relevance, not the norm
        v = df.Volume.astype(float)
        med = v.rolling(W, min_periods=1).median()
        rel = np.where(med > 0, v / med.replace(0, np.nan), 1.0)
        rel = np.where(np.isfinite(rel), rel, 1.0)
    r = readings(F, tau_D=_TAU[symbol], r=rel)
    trad = tradeable_flags(df).tradeable.values
    out = []
    hT, hV, hR = [], [], []
    t_a = 0
    for t_b, T, V in zip(r.t.values, r.T_k.values, r.V_k.values):
        t_b = int(t_b)
        if t_b <= t_a:
            continue
        R = float(T)                               # r = 1 per bar
        ref = close[t_a - 1] if t_a >= 1 else close[t_a]
        disp = float(close[t_b - 1] / ref - 1.0) if ref > 0 else 0.0
        if len(hT) >= 3:
            mT, mV, mR = float(np.median(hT[-W:])), float(np.median(hV[-W:])), float(np.median(hR[-W:]))
            Th, Vh, Rh = (T / mT if mT > 0 else 0.0), (V / mV if mV > 0 else 0.0), (R / mR if mR > 0 else 0.0)
            P_sig = tuple((int(Th // h1), int(Vh // h2), int(Rh // h3)) for h1, h2, h3 in LATTICES)
            sign = 1 if disp > 0 else (-1 if disp < 0 else 0)
            issue_t = t_b + 1 if t_b + 1 < n else None   # first close after the gate's end is knowable
            out.append({"cls": (P_sig, sign), "disp": disp, "t_a": t_a, "t_b": t_b,
                        "issue_t": issue_t, "issue_d": str(dates[issue_t])[:10] if issue_t is not None else None,
                        "issue_px": float(close[issue_t]) if issue_t is not None else None,
                        "tradeable": bool(trad[issue_t]) if issue_t is not None else False})
        hT.append(T); hV.append(V); hR.append(R)
        t_a = t_b
    return symbol, out, [str(d)[:10] for d in dates[-1:]], float(close[-1])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--every", type=int, default=1)
    ap.add_argument("--field", choices=list(FIELDS), default="bar")
    a = ap.parse_args()
    global OUT
    OUT = OUT.with_name(f"ch2_species_spectrum_fullbar_{a.field}.json")
    from ch2_herd_census import herd_state
    t0 = time.time()
    bars = pd.read_parquet(ROOT / "artifacts" / "ch2_life" / "ohlcv_pool.parquet")
    symbols = sorted(bars.Symbol.unique())[:: a.every]
    bars = bars[bars.Symbol.isin(symbols)].sort_values(["Symbol", "Date"]).reset_index(drop=True)
    tau, cs, weather = herd_state(bars, cols=FIELDS[a.field])
    tau_map = {s: tau[s].reindex(g.Date.values).values for s, g in bars.groupby("Symbol", sort=False)}
    tasks = [(s, g) for s, g in bars.groupby("Symbol", sort=False)]
    del bars
    # 1) observations: (availability date of the completion, alphabet, species, next sign, sym, issue_d, issue_px, tradeable)
    obs, last_px, n_gates = [], {}, 0
    with Pool(a.workers, initializer=_init, initargs=(tau_map, a.field)) as pool:
        for i, (sym, gs, last_d, lpx) in enumerate(pool.imap_unordered(_gs, tasks, chunksize=4), 1):
            last_px[sym] = (last_d[0], lpx); n_gates += len(gs)
            for k in range(2, len(gs)):
                prev, cur, nxt = gs[k - 2], gs[k - 1], gs[k]
                if cur["issue_t"] is None or nxt["issue_t"] is None:
                    continue
                avail_d = nxt["issue_d"]                       # the completion is known at the next gate's issue
                sign_next = 1 if nxt["disp"] > 0 else (-1 if nxt["disp"] < 0 else 0)
                if sign_next == 0:
                    continue
                pooled = ((prev["cls"][0][2], prev["cls"][1]), (cur["cls"][0][2], cur["cls"][1]))
                for alpha, species in (("bigram", (prev["cls"], cur["cls"])), ("pooled", pooled)):
                    obs.append((avail_d, alpha, species, sign_next, sym, cur["issue_d"], cur["issue_px"], cur["tradeable"], nxt["issue_d"], nxt["issue_px"]))
            if i % 500 == 0:
                print(f"[species] {i}/{len(tasks)} gates {n_gates} obs {len(obs)} {time.time() - t0:.0f}s", flush=True)
    print(f"[species] symbols {len(tasks)}; gates {n_gates}; observations {len(obs)}; {time.time() - t0:.0f}s", flush=True)
    # 2) causal schema memory in global availability order; each observation sees only earlier completions
    obs.sort(key=lambda x: (x[0], x[4]))
    pos, neg = defaultdict(int), defaultdict(int)
    rows = []
    for avail_d, alpha, sp, sign_next, sym, issue_d, issue_px, trad, exit_d, exit_px in obs:
        key = (alpha, sp)
        p, q = pos[key], neg[key]
        rows.append((alpha, sp, p, q, sign_next, sym, issue_d, issue_px, trad, exit_d, exit_px))
        if sign_next > 0: pos[key] += 1
        else: neg[key] += 1
    # 3) spectrum vs binomial null, per alphabet
    res = {"declared": "frame, gate stream, class, species, completion, spectrum, test and ledger in the docstring before results", "field": a.field,
           "symbols": len(tasks), "gates": n_gates, "observations": len(obs), "alphabets": {}}
    edges = [0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0001]
    rng = np.random.default_rng(20260730)
    for alpha in ("bigram", "pooled"):
        keys = [k for k in set(pos) | set(neg) if k[0] == alpha]
        stats = {k: (pos[k] + neg[k], pos[k] / (pos[k] + neg[k])) for k in keys if pos[k] + neg[k] >= W}
        base = sum(pos[k] for k in keys) / max(1, sum(pos[k] + neg[k] for k in keys))
        cons = np.array([max(f, 1 - f) for n, f in stats.values()]); ns = np.array([n for n, f in stats.values()])
        null = []
        for n in ns:
            d = rng.binomial(n, base, size=20); null.extend(np.maximum(d / n, 1 - d / n))
        h_real = np.histogram(cons, bins=edges)[0]; h_null = np.histogram(np.array(null), bins=edges)[0] / 20.0
        # the causal test: predictions from species with n >= W and live consistency >= BAND, per year
        per_year = defaultdict(lambda: [0, 0]); per_year_all = defaultdict(lambda: [0, 0])
        ledger_open, trades = {}, []
        for al, sp, p, q, sign_next, sym, issue_d, issue_px, trad, exit_d, exit_px in rows:
            if al != alpha: continue
            yr = issue_d[:4]
            per_year_all[yr][0] += 1; per_year_all[yr][1] += int(sign_next > 0)
            n2 = p + q
            if n2 >= W:
                pred_up = p >= q
                live = max(p, q) / n2
                if live >= BAND:
                    per_year[yr][0] += 1; per_year[yr][1] += int((sign_next > 0) == pred_up)
                # L5 ledger: enter on band-UP at issue close; exit at first DOWN-majority prediction at its issue close
                oc = ledger_open.get(sym)
                if oc is None and pred_up and live >= BAND and trad and issue_px:
                    ledger_open[sym] = (issue_d, issue_px)
                elif oc is not None and not pred_up and issue_px and issue_d > oc[0]:
                    trades.append((oc[0], issue_d, sym, issue_px / oc[1] - 1.0)); ledger_open.pop(sym)
        for sym, (d0, px0) in ledger_open.items():
            d1, px1 = last_px[sym]
            if px0: trades.append((d0, d1, sym, px1 / px0 - 1.0))
        tr = pd.DataFrame(trades, columns=["in", "out", "sym", "ret"])
        tr["year"] = tr["in"].str[:4]
        ledger = {y: {"trades": int(len(g)), "win_rate": round(float((g.ret > 0).mean()), 4), "sum_ret_per_$1": round(float(g.ret.sum()), 3),
                      "mean_ret_pct": round(float(g.ret.mean() * 100), 3)} for y, g in tr.groupby("year")}
        res["alphabets"][alpha] = {
            "base_rate_up": round(float(base), 4), "species_n_ge_20": int(len(stats)),
            "spectrum_hist_edges": edges, "spectrum_real": [int(x) for x in h_real], "spectrum_null": [round(float(x), 2) for x in h_null],
            "species_ge_0.75": int((cons >= 0.75).sum()), "null_ge_0.75": round(float((np.array(null) >= 0.75).sum() / 20.0), 2),
            "species_ge_0.85": int((cons >= 0.85).sum()), "null_ge_0.85": round(float((np.array(null) >= 0.85).sum() / 20.0), 2),
            "band_predictions_per_year": {y: {"n": v[0], "hit_rate": round(v[1] / v[0], 4) if v[0] else None,
                                              "base_up_rate_that_year": round(per_year_all[y][1] / per_year_all[y][0], 4) if per_year_all[y][0] else None}
                                          for y, v in sorted(per_year.items())},
            "l5_ledger_per_year": ledger,
            "l5_ledger_total": {"trades": int(len(tr)), "win_rate": round(float((tr.ret > 0).mean()), 4) if len(tr) else None,
                                "sum_ret_per_$1": round(float(tr.ret.sum()), 3) if len(tr) else None}}
        print(f"\n== {alpha}: base up-rate {base:.4f}; species n>=20: {len(stats)}; consistency >= 0.75: {int((cons >= 0.75).sum())} real vs {float((np.array(null) >= 0.75).sum() / 20.0):.1f} null; >= 0.85: {int((cons >= 0.85).sum())} vs {float((np.array(null) >= 0.85).sum() / 20.0):.1f}")
        print("   spectrum real:", [int(x) for x in h_real]); print("   spectrum null:", [round(float(x), 1) for x in h_null])
        print("   band predictions per year (n, hit rate | base up-rate):")
        for y, v in sorted(per_year.items()):
            print(f"     {y}: n={v[0]:>6} hit={v[1] / v[0] if v[0] else float('nan'):.4f} | base={per_year_all[y][1] / per_year_all[y][0]:.4f}")
        print("   L5 ledger per year:", json.dumps(ledger)); print("   L5 ledger total:", res["alphabets"][alpha]["l5_ledger_total"])
    json.dump(res, open(OUT, "w"), indent=1)
    print("filed:", OUT)


def _gs(task):
    return gate_stream(*task)


if __name__ == "__main__":
    main()
