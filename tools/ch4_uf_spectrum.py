"""
ch4_uf_spectrum.py — the full spectrum of temporal geometric structures
=======================================================================

Frame shift (Joe, 2026-07-30): stop scanning for conditional return
signals — there are none. Compute the STRUCTURES: every gate is a
geometric object with a CLASS (its multi-lattice mosaic projection
signature, §3.3/§11.3 — computed by every realization here and then
discarded down to a count); consecutive classes form temporal-geometric
SPECIES (motifs); the field accumulates a SCHEMA MEMORY (§UF memory
architecture) of how each species completes. The spectrum = the catalog
of species with their completion consistency. If the physics is real,
the spectrum contains species whose completions are far more consistent
than chance — visible BEFORE any trade rule exists.

DECLARED (before measurement):
  Gate stream    v2 conformant L0/L1 (adaptive ‖ΔSEV‖ boundaries,
                 normalized field, volume relevance) — closed gates only.
  Gate class     the full projection signature P = ((⌊T/h⌋,⌊V/h⌋,⌊R/h⌋)
                 per lattice, 3 pinned lattices) TOGETHER WITH the gate's
                 displacement sign (its direction is part of its
                 geometry): class = (P_signature, sign(Δclose over gate)).
  Species        bigram of consecutive gate classes (class_{k-1}, class_k).
  Completion     the NEXT gate's displacement sign (and magnitude).
  Schema memory  accumulated field-wide in strict GLOBAL DATE ORDER:
                 a species' statistics at any moment contain only gate
                 completions that finished strictly earlier (causal;
                 live-reproducible).
  Spectrum       for every species reaching n ≥ W = 20 causal
                 occurrences: its completion consistency (share of the
                 majority outcome). Reported as a distribution AGAINST
                 THE BINOMIAL NULL (what maximum-consistency spread
                 chance alone produces at each n) — the existence test
                 for structural species, not a strategy.
  Eligibility    LIFE ≥ 0.90 vertices, $5 floor (structural weed rule).

Output: spectrum histogram, null comparison, top species (by causal
consistency at n ≥ 20 with their per-year completion record), and the
species-count census. Raw. No thresholds tuned, nothing traded.

Usage: python tools/ch4_uf_spectrum.py [N_SYMBOLS]
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

from tools.ch4_uf_kernel_v2 import compute_l0_v2, LATTICES  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARQUET = os.environ.get("CH4_STORE") or os.path.join(ROOT, "quarantine_12k_universe.parquet")
OUT_DIR = os.path.join(ROOT, "artifacts", "ch4_uf")
W = 20
LIFE_MIN = 0.90
PRICE_FLOOR = 5.0
MIN_BARS = 1250


def life_fraction(closes):
    n = len(closes)
    moved = np.zeros(n)
    if n > 1:
        moved[1:] = (np.abs(np.diff(closes)) > 0).astype(float)
    return np.cumsum(moved) / np.maximum(np.arange(n), 1)


def gate_stream(dates, closes, vols):
    """Closed gates of the v2 L0/L1: (end_date, class_tuple, disp_sign,
    disp, t_a, t_b). Class = full projection signature + direction.

    Lattice scale fix (caught in self-audit): the pinned 1/2/4 grid was
    calibrated for raw-dollar fields; on the normalized field the V axis
    floored to zero in every class (species degenerated to duration
    bins). Spec-native cure with no new constants: each TVR component is
    first self-scaled by its own trailing-W-gate median (the in-repo
    precedented self-scaling form, causal), then quantized by the pinned
    ladder — all three axes visible at all three resolutions."""
    l0 = compute_l0_v2(closes, vols)
    bounds = np.flatnonzero(l0.boundary)
    raw = []
    prev = 0
    for b in bounds:
        t_a, t_b = prev, int(b)
        if t_b > t_a:
            ln = t_b - t_a
            T = float(ln)
            V = float(l0.cs_perV[t_b] - l0.cs_perV[t_a])
            R = float(l0.cs_r[t_b] - l0.cs_r[t_a])
            # displacement the gate's days produced: last close of the
            # gate vs the close before it began (1-bar gates get that
            # day's true move — fixes the disp==0 degeneracy caught in
            # self-audit)
            ref = closes[t_a - 1] if t_a >= 1 else closes[t_a]
            disp = float(closes[t_b - 1] / ref - 1.0) if ref > 0 else 0.0
            raw.append([dates[t_b], T, V, R, disp, t_a, t_b])
        prev = int(b)

    out = []
    hist_T, hist_V, hist_R = [], [], []
    for rec in raw:
        d_end, T, V, R, disp, t_a, t_b = rec
        if len(hist_T) >= 3:      # need some trailing mass to scale
            mT = float(np.median(hist_T[-W:]))
            mV = float(np.median(hist_V[-W:]))
            mR = float(np.median(hist_R[-W:]))
            Th = T / mT if mT > 0 else 0.0
            Vh = V / mV if mV > 0 else 0.0
            Rh = R / mR if mR > 0 else 0.0
            P_sig = tuple((int(Th // h1), int(Vh // h2), int(Rh // h3))
                          for h1, h2, h3 in LATTICES)
            sign = 1 if disp > 0 else (-1 if disp < 0 else 0)
            out.append((d_end, (P_sig, sign), disp, t_a, t_b))
        hist_T.append(T)
        hist_V.append(V)
        hist_R.append(R)
    return out


def coarse_context_map(dates, closes, vols):
    """Per native day: displacement sign of the last FINALIZED k=20
    coarse gate (finalized = its successor block complete; same causal
    rule as the fixed ladder). Context alphabet {-1, 0, +1, None}."""
    k = 20
    n = len(closes)
    m = n // k
    if m < 30:
        return [None] * n
    idx_end = [(j + 1) * k - 1 for j in range(m)]
    c2 = np.array([closes[i] for i in idx_end])
    v2 = np.array([float(np.sum(vols[j * k:(j + 1) * k])) for j in range(m)]) if vols is not None else None
    d2 = [dates[i] for i in idx_end]
    gs2 = gate_stream(d2, c2, v2)
    # per coarse gate: sign, END BLOCK index; finalized when the NEXT
    # block after its end exists
    ctx = [None] * n
    if not gs2:
        return ctx
    # map: for each native day t, last coarse gate whose end-block's
    # successor block is complete at t
    gate_ends = []
    for (d_end, cls, disp, ta, tb) in gs2:
        # tb is an index into the COARSE series; its end block is tb-1
        end_block = tb - 1
        final_day = idx_end[end_block + 1] if end_block + 1 < m else None
        if final_day is not None:
            gate_ends.append((final_day, 1 if disp > 0 else (-1 if disp < 0 else 0)))
    gi = -1
    for t in range(n):
        while gi + 1 < len(gate_ends) and gate_ends[gi + 1][0] <= t:
            gi += 1
        ctx[t] = gate_ends[gi][1] if gi >= 0 else None
    return ctx


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10 ** 9
    df = pd.read_parquet(PARQUET, columns=["Date", "Symbol", "Close", "Volume"])
    df["Date"] = pd.to_datetime(df["Date"])
    g = df.groupby("Symbol")["Close"]
    stats = pd.DataFrame({"bars": g.size(), "med": g.median()})
    uni = sorted(stats[(stats["bars"] >= MIN_BARS)
                       & (stats["med"] >= PRICE_FLOOR)].index.tolist())[:limit]
    print(f"universe: {len(uni)} symbols")

    # 1) collect every species OBSERVATION as (completion_date, species,
    #    next_disp) — completion_date = the date the NEXT gate closed
    #    (when the outcome becomes known; the causal availability time).
    obs = []
    t0 = time.time()
    kept = 0
    for i, sym in enumerate(uni):
        sub = df[df["Symbol"] == sym].sort_values("Date")
        dates = sub["Date"].dt.date.tolist()
        closes = sub["Close"].to_numpy(dtype=float)
        vols = sub["Volume"].to_numpy(dtype=float)
        lf = life_fraction(closes)
        if lf[-1] < LIFE_MIN:
            continue
        kept += 1
        try:
            gs = gate_stream(dates, closes, vols)
        except Exception:
            continue
        ctx = coarse_context_map(dates, closes, vols)
        for k in range(3, len(gs)):
            d_p2, cls_p2, _, _, _ = gs[k - 3]
            d_prev, cls_prev, _, _, _ = gs[k - 2]
            d_cur, cls_cur, _, ta_cur, tb_cur = gs[k - 1]
            d_next, cls_next, disp_next, ta_n, tb_n = gs[k]
            if closes[tb_cur - 1] < PRICE_FLOOR:
                continue
            issue_d = str(dates[tb_cur - 1])
            exit_d = str(dates[tb_n - 1])
            issue_px = float(closes[tb_cur - 1])
            cx = ctx[tb_cur - 1]
            # pooled spelling: coarsest-lattice term only (h=4) — merges
            # near-identical species so records fatten (deep tiers need n)
            pool_prev = (cls_prev[0][2], cls_prev[1])
            pool_cur = (cls_cur[0][2], cls_cur[1])
            for alpha, species in (
                ("bigram", (cls_prev, cls_cur)),
                ("bigram_ctx", (cls_prev, cls_cur, cx)),
                ("trigram", (cls_p2, cls_prev, cls_cur)),
                ("pooled", (pool_prev, pool_cur)),
                ("pooled_ctx", (pool_prev, pool_cur, cx)),
            ):
                obs.append((str(d_next), (alpha, species), disp_next, sym, issue_d, exit_d, issue_px))
        if (i + 1) % 500 == 0:
            print(f"  [{i+1}/{len(uni)}] obs={len(obs)} {time.time()-t0:.0f}s",
                  flush=True)
    print(f"eligible symbols: {kept}; observations: {len(obs)}")

    # 2) causal field-wide schema accumulation in global date order
    obs.sort(key=lambda x: (x[0], x[3]))  # by completion date (causal availability)
    store_pos = defaultdict(int)
    store_neg = defaultdict(int)
    # snapshot the FINAL spectrum (for the census) and also record each
    # observation's PRE-observation species stats (causal view)
    causal_rows = []
    for d_next, sp, disp, sym, issue_d, exit_d, issue_px in obs:
        p, q = store_pos[sp], store_neg[sp]
        causal_rows.append((sp, p, q, disp, d_next, sym, issue_d, exit_d, issue_px))
        if disp > 0:
            store_pos[sp] += 1
        elif disp < 0:
            store_neg[sp] += 1

    # 3) the spectrum: final species census + consistency vs binomial null
    species_stats = {}
    for sp in store_pos.keys() | store_neg.keys():
        p, q = store_pos[sp], store_neg[sp]
        n = p + q
        if n >= W:
            species_stats[sp] = (n, p / n)
    print(f"species with n>= {W}: {len(species_stats)}")

    cons = np.array([max(f, 1 - f) for _, (n, f) in species_stats.items()])
    ns = np.array([n for _, (n, f) in species_stats.items()])

    # binomial null: for each species' n, draw the max-consistency under
    # p=field base rate; deterministic seed (audit-reproducible)
    base = sum(store_pos.values()) / max(1, sum(store_pos.values()) + sum(store_neg.values()))
    rng = np.random.default_rng(20260730)
    null_cons = []
    for n in ns:
        draws = rng.binomial(n, base, size=20)
        null_cons.extend([max(d / n, 1 - d / n) for d in draws])
    null_cons = np.array(null_cons)

    hist_edges = [0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0]
    hist_real = np.histogram(cons, bins=hist_edges)[0]
    hist_null = np.histogram(null_cons, bins=hist_edges)[0] / 20.0

    # 4) top species by CAUSAL consistency: evaluate each observation
    #    against its own pre-observation stats (n>=W at observation time)
    causal_by_sp = defaultdict(lambda: [0, 0])
    sym_div = defaultdict(set)
    year_hits = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    # THE AGGREGATE TEST: every causal prediction issued by a species
    # whose live (pre-observation) record had n >= W and consistency >=
    # the pinned upper band (0.75) at issue time. Persisted in full.
    band_preds = []
    # CYCLE LEDGER (declared): per alphabet — enter long at a band-UP
    # prediction's issue close (live_cons >= 0.75, n >= W); exit at the
    # FIRST subsequent established DOWN-majority prediction (n >= W, any
    # consistency — the field's ordinary collapse reading) at ITS issue
    # close; force-close at the last seen price. Causal on both ends.
    cycle_open = {}          # (alpha, sym) -> (issue_d, px)
    cycle_last_px = {}       # (alpha, sym) -> (date, px)
    cycle_trades = defaultdict(list)   # alpha -> trades
    # MORPHOLOGY HARVEST (declared): each species' exit comes from its
    # OWN causally-accumulated cycle shape — the median gates-to-peak of
    # its prior completed cycles (>= 3 completed cycles required; before
    # that, morphology entries fall back to the ordinary-collapse exit).
    # Peak = the best return seen at any prediction event during the
    # cycle. All stores strictly causal.
    morph_open = {}          # (alpha, sym) -> dict(species, issue_d, px, gates, peak_ret, peak_gate)
    morph_store = defaultdict(list)    # species -> [peak_gate history]
    morph_trades = defaultdict(list)   # alpha -> trades
    for sp, p, q, disp, d_next, sym, issue_d, exit_d, issue_px in causal_rows:
        sym_div[sp].add(sym)
        alpha_key = sp[0]
        k2 = (alpha_key, sym)
        cycle_last_px[k2] = (issue_d, issue_px)
        n2 = p + q
        if n2 >= W:
            pred_up2 = p >= q
            oc = cycle_open.get(k2)
            if oc is None and pred_up2 and (max(p, q) / n2) >= 0.75 and issue_px > 0:
                cycle_open[k2] = (issue_d, issue_px)
            elif oc is not None and not pred_up2 and issue_px > 0 and issue_d > oc[0]:
                cycle_trades[alpha_key].append(
                    {"symbol": sym, "in": oc[0], "out": issue_d,
                     "ret_pct": round(100 * (issue_px / oc[1] - 1.0), 3)})
                cycle_open.pop(k2, None)

            # --- morphology ledger (same entries; species-shaped exits)
            mo = morph_open.get(k2)
            if mo is not None and issue_px > 0 and issue_d > mo["issue_d"]:
                mo["gates"] += 1
                ret_now = 100 * (issue_px / mo["px"] - 1.0)
                if ret_now > mo["peak_ret"]:
                    mo["peak_ret"] = ret_now
                    mo["peak_gate"] = mo["gates"]
                hist = morph_store.get(mo["species"], [])
                target = (int(np.median(hist[-50:])) if len(hist) >= 3 else None)
                collapse = not pred_up2
                ripe = target is not None and mo["gates"] >= max(1, target)
                if ripe or collapse:
                    morph_trades[alpha_key].append(
                        {"symbol": sym, "in": mo["issue_d"], "out": issue_d,
                         "ret_pct": round(ret_now, 3),
                         "reason": "RIPE" if ripe else "COLLAPSE"})
                    morph_store[mo["species"]].append(mo["peak_gate"])
                    morph_open.pop(k2, None)
            if morph_open.get(k2) is None and pred_up2 and (max(p, q) / n2) >= 0.75 and issue_px > 0:
                sp_key = sp
                if morph_open.get(k2) is None and (k2 not in morph_open):
                    morph_open[k2] = {"species": sp_key, "issue_d": issue_d,
                                      "px": issue_px, "gates": 0,
                                      "peak_ret": 0.0, "peak_gate": 0}
    for (alpha_key, sym), oc in cycle_open.items():
        lp = cycle_last_px.get((alpha_key, sym))
        if lp and lp[1] > 0 and lp[0] > oc[0]:
            cycle_trades[alpha_key].append(
                {"symbol": sym, "in": oc[0], "out": lp[0],
                 "ret_pct": round(100 * (lp[1] / oc[1] - 1.0), 3),
                 "eod": True})

    for sp, p, q, disp, d_next, sym, issue_d, exit_d, issue_px in causal_rows:
        n = p + q
        if n < W:
            continue
        pred_up = p >= q
        hit = (disp > 0) == pred_up if disp != 0 else False
        causal_by_sp[sp][0] += 1 if hit else 0
        causal_by_sp[sp][1] += 1
        yh = year_hits[sp][d_next[:4]]
        yh[0] += 1 if hit else 0
        yh[1] += 1
        live_cons = max(p, q) / n
        if live_cons >= 0.75:
            band_preds.append({
                "date": d_next, "symbol": sym, "alpha": sp[0],
                "issue_date": issue_d, "exit_date": exit_d,
                "dir": "UP" if pred_up else "DOWN",
                "live_n": n, "live_cons": round(live_cons, 4),
                "disp_pct": round(100 * disp, 3),
                "hit": bool(hit),
            })

    causal_hits = sum(v[0] for v in causal_by_sp.values())
    causal_tot = sum(v[1] for v in causal_by_sp.values())

    top = sorted(species_stats.items(), key=lambda kv: (max(kv[1][1], 1 - kv[1][1]), kv[1][0]),
                 reverse=True)[:15]
    top_rows = []
    for sp, (n, f) in top:
        ch = causal_by_sp.get(sp)
        yh = year_hits.get(sp, {})
        top_rows.append({
            "species": str(sp), "n": int(n),
            "consistency_pct": round(100 * max(f, 1 - f), 1),
            "direction": "UP" if f >= 0.5 else "DOWN",
            "distinct_symbols": len(sym_div.get(sp, ())),
            "causal_pred_n": int(ch[1]) if ch else 0,
            "causal_pred_hit_pct": round(100 * ch[0] / ch[1], 1) if ch and ch[1] else None,
            "causal_by_year": {y: f"{v[0]}/{v[1]}" for y, v in sorted(yh.items())},
        })

    # aggregate band-prediction record (per year, per direction)
    def agg(preds):
        if not preds:
            return {}
        hits = sum(1 for r in preds if r["hit"])
        disps = [r["disp_pct"] for r in preds]
        signed = [r["disp_pct"] if r["dir"] == "UP" else -r["disp_pct"] for r in preds]
        return {"n": len(preds),
                "hit_pct": round(100 * hits / len(preds), 2),
                "mean_signed_disp_pct": round(float(np.mean(signed)), 3),
                "median_abs_disp_pct": round(float(np.median(np.abs(disps))), 3)}

    band_by_year = {}
    for r in band_preds:
        band_by_year.setdefault(r["date"][:4], []).append(r)
    band_summary = {
        "all": agg(band_preds),
        "UP": agg([r for r in band_preds if r["dir"] == "UP"]),
        "DOWN": agg([r for r in band_preds if r["dir"] == "DOWN"]),
        "by_year": {y: agg(v) for y, v in sorted(band_by_year.items())},
    }

    # cycle-harvest summaries + declared book per alphabet
    def cycle_summary(trades):
        if not trades:
            return {}
        rets = np.array([t["ret_pct"] for t in trades])
        by = defaultdict(list)
        for t in trades:
            by[t["in"][:4]].append(t["ret_pct"])
        evs = sorted(trades, key=lambda t: (t["in"], t["symbol"]))
        cal = defaultdict(lambda: {"i": [], "o": []})
        for i, t in enumerate(evs):
            cal[t["in"]]["i"].append(i)
            cal[t["out"]]["o"].append(i)
        cash, open_pos, held = 100_000.0, {}, set()
        curve = []
        for day in sorted(cal.keys()):
            for i in sorted(cal[day]["o"]):
                if i in open_pos:
                    amt = open_pos.pop(i)
                    held.discard(evs[i]["symbol"])
                    cash += amt * (1 + evs[i]["ret_pct"] / 100)
            for i in sorted(cal[day]["i"], key=lambda j: evs[j]["symbol"]):
                t = evs[i]
                if t["symbol"] in held or len(open_pos) >= 10:
                    continue
                eq = cash + sum(open_pos.values())
                b = min(cash, 0.10 * eq)
                if b <= 0:
                    continue
                open_pos[i] = b
                held.add(t["symbol"])
                cash -= b
            curve.append((day, cash + sum(open_pos.values())))
        for i in list(open_pos):
            cash += open_pos.pop(i) * (1 + evs[i]["ret_pct"] / 100)
        byy = {}
        prev = ys = 100_000.0
        cy = curve[0][0][:4] if curve else None
        for day, eq in curve:
            if day[:4] != cy:
                byy[cy] = round(100 * (prev / ys - 1), 2)
                cy, ys = day[:4], prev
            prev = eq
        if cy:
            byy[cy] = round(100 * (cash / ys - 1), 2)
        return {
            "trades": len(trades),
            "wr_pct": round(100 * float((rets > 0).mean()), 2),
            "mean_pct": round(float(rets.mean()), 2),
            "median_pct": round(float(np.median(rets)), 2),
            "by_year_wr": {y: {"n": len(v),
                               "wr": round(100 * float((np.array(v) > 0).mean()), 1)}
                           for y, v in sorted(by.items())},
            "book_total_pct": round(100 * (cash / 100_000.0 - 1), 2),
            "book_by_year": byy,
        }

    cycles_out = {a: cycle_summary(tr) for a, tr in cycle_trades.items()}
    morph_out = {a: cycle_summary(tr) for a, tr in morph_trades.items()}

    result = {
        "frame": "temporal geometric species spectrum (mosaic-class bigrams, "
                 "field schema memory, causal)",
        "cycle_harvest": cycles_out,
        "morphology_harvest": morph_out,
        "band_predictions": band_summary,
        "eligible_symbols": kept,
        "observations": len(obs),
        "field_up_base_rate_pct": round(100 * base, 2),
        "species_n_ge_20": len(species_stats),
        "consistency_hist_edges": hist_edges,
        "consistency_hist_real": hist_real.tolist(),
        "consistency_hist_null_expected": [round(x, 1) for x in hist_null.tolist()],
        "causal_prediction_overall": {
            "n": int(causal_tot),
            "hit_pct": round(100 * causal_hits / causal_tot, 2) if causal_tot else None,
        },
        "top_species": top_rows,
    }
    out = os.path.join(OUT_DIR, "ch4_uf_spectrum.json")
    with open(out, "w") as f:
        json.dump({**result, "band_prediction_rows": band_preds}, f, indent=1)
    print(json.dumps(result, indent=1))
    print("filed:", out)


if __name__ == "__main__":
    main()
