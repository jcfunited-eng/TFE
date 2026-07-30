"""
ch4_uf_spectrum_field.py — species schema memory conditioned on the field
=========================================================================

Joe's clue (2026-07-30): the remaining hurdle is "the energy present in
the whole system and the distributed greed of the herd." The species
records to date pool across all market weather; the same temporal
geometry completes differently depending on the state of the WHOLE
field. This conditions the schema memory on two causal, kernel-native
field series:

  ENERGY  E(t) — cross-vertex mean of the kernel's per-bar structural
          action (‖ΔF‖+σ+κ, the same integrand V is built from) over
          eligible vertices: the system's total excitation level.
  GREED   G(t) — the herd's distributed reach: the fraction of eligible
          vertices whose close rose that day (breadth of buying).

  STATE   each series banded against its own trailing W=20 days at the
          pinned 0.25/0.75 quantiles → {lo, mid, hi}; field state =
          (E-band, G-band), 9 weather cells. Strictly trailing.

ALPHABETS (declared): bigram (control, unchanged), bigram_E (species ×
E-band), bigram_EG (species × both bands). Same causal machinery as the
main spectrum: global date order, records earn n ≥ W before speaking,
band ≥ 0.75 aggregate, tier curves, and both harvest ledgers (ordinary
collapse exit; per-species morphology exit). All raw; nothing tuned.

Usage: CH4_STORE=... python tools/ch4_uf_spectrum_field.py [N]
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

from tools.ch4_uf_kernel_v2 import compute_l0_v2  # noqa: E402
from tools.ch4_uf_spectrum import gate_stream, life_fraction, W  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARQUET = os.environ.get("CH4_STORE") or os.path.join(ROOT, "quarantine_12k_universe.parquet")
OUT_DIR = os.path.join(ROOT, "artifacts", "ch4_uf")
LIFE_MIN = 0.90
PRICE_FLOOR = 5.0
MIN_BARS = 1250
BAND = 0.75


def band3(series, dates_index):
    """Trailing-W {0,1,2} banding at pinned 25/75, strictly before t."""
    n = len(series)
    out = np.full(n, -1, dtype=int)
    for t in range(n):
        w0 = max(0, t - W)
        win = series[w0:t]
        win = win[np.isfinite(win)]
        if len(win) < W // 2:
            continue
        lo, hi = np.percentile(win, 25), np.percentile(win, 75)
        v = series[t]
        if not np.isfinite(v):
            continue
        out[t] = 0 if v <= lo else (2 if v >= hi else 1)
    return out


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10 ** 9
    df = pd.read_parquet(PARQUET, columns=["Date", "Symbol", "Close", "Volume"])
    df["Date"] = pd.to_datetime(df["Date"])
    g = df.groupby("Symbol")["Close"]
    stats = pd.DataFrame({"bars": g.size(), "med": g.median()})
    uni = sorted(stats[(stats["bars"] >= MIN_BARS)
                       & (stats["med"] >= PRICE_FLOOR)].index.tolist())[:limit]
    all_dates = sorted(df["Date"].dt.strftime("%Y-%m-%d").unique())
    d_index = {d: i for i, d in enumerate(all_dates)}
    nD = len(all_dates)
    print(f"universe: {len(uni)} symbols, {nD} field days")

    # ---- PASS 1: field energy + greed breadth over eligible vertices
    E_sum = np.zeros(nD)
    E_cnt = np.zeros(nD)
    G_up = np.zeros(nD)
    G_cnt = np.zeros(nD)
    t0 = time.time()
    frames = {}
    for i, sym in enumerate(uni):
        sub = df[df["Symbol"] == sym].sort_values("Date")
        dates = sub["Date"].dt.strftime("%Y-%m-%d").tolist()
        closes = sub["Close"].to_numpy(dtype=float)
        vols = sub["Volume"].to_numpy(dtype=float)
        lf = life_fraction(closes)
        if lf[-1] < LIFE_MIN:
            continue
        frames[sym] = (dates, closes, vols)
        l0 = compute_l0_v2(closes, vols)
        el = (lf >= LIFE_MIN) & (closes >= PRICE_FLOOR)
        idxs = np.array([d_index[d] for d in dates])
        for t in np.flatnonzero(el):
            di = idxs[t]
            E_sum[di] += l0.perV[t]
            E_cnt[di] += 1
            if t >= 1:
                G_cnt[di] += 1
                if closes[t] > closes[t - 1]:
                    G_up[di] += 1
        if (i + 1) % 500 == 0:
            print(f"  pass1 [{i+1}/{len(uni)}] {time.time()-t0:.0f}s", flush=True)

    E = np.where(E_cnt > 0, E_sum / np.maximum(E_cnt, 1), np.nan)
    G = np.where(G_cnt > 0, G_up / np.maximum(G_cnt, 1), np.nan)
    E_band = band3(E, d_index)
    G_band = band3(G, d_index)
    print(f"field series ready: E finite {int(np.isfinite(E).sum())}, "
          f"G finite {int(np.isfinite(G).sum())}")

    # ---- PASS 2: observations with field-state alphabets
    obs = []
    for i, (sym, (dates, closes, vols)) in enumerate(frames.items()):
        try:
            gs = gate_stream(dates, closes, vols)
        except Exception:
            continue
        for k in range(2, len(gs)):
            d_prev, cls_prev, _, _, _ = gs[k - 2]
            d_cur, cls_cur, _, ta_cur, tb_cur = gs[k - 1]
            d_next, cls_next, disp_next, ta_n, tb_n = gs[k]
            if closes[tb_cur - 1] < PRICE_FLOOR:
                continue
            issue_d = dates[tb_cur - 1]
            exit_d = dates[tb_n - 1]
            issue_px = float(closes[tb_cur - 1])
            di = d_index[issue_d]
            eb, gb = int(E_band[di]), int(G_band[di])
            if eb < 0 or gb < 0:
                continue
            big = (cls_prev, cls_cur)
            for alpha, species in (
                ("bigram", big),
                ("bigram_E", (big, eb)),
                ("bigram_EG", (big, eb, gb)),
            ):
                obs.append((str(d_next), (alpha, species), disp_next, sym,
                            issue_d, exit_d, issue_px))
        if (i + 1) % 500 == 0:
            print(f"  pass2 [{i+1}/{len(frames)}] obs={len(obs)}", flush=True)
    print(f"observations: {len(obs)}")

    # ---- causal accumulation + tier curves + harvest ledgers
    obs.sort(key=lambda x: (x[0], x[3]))
    store_pos = defaultdict(int)
    store_neg = defaultdict(int)
    band_stats = defaultdict(lambda: defaultdict(lambda: [0, 0]))  # alpha -> tier -> [hit, n]
    band_year = defaultdict(lambda: defaultdict(lambda: [0, 0]))   # (alpha,tier) -> yr
    cycle_open = {}
    cycle_last = {}
    cycle_trades = defaultdict(list)
    morph_open = {}
    morph_store = defaultdict(list)
    morph_trades = defaultdict(list)
    TIERS = (0.75, 0.85, 0.90, 0.95)

    for d_next, sp, disp, sym, issue_d, exit_d, issue_px in obs:
        p, q = store_pos[sp], store_neg[sp]
        n = p + q
        alpha = sp[0]
        k2 = (alpha, sym)
        cycle_last[k2] = (issue_d, issue_px)
        if n >= W:
            pred_up = p >= q
            live = max(p, q) / n
            hit = (disp > 0) == pred_up if disp != 0 else False
            for tier in TIERS:
                if live >= tier:
                    band_stats[alpha][tier][0] += 1 if hit else 0
                    band_stats[alpha][tier][1] += 1
                    band_year[(alpha, tier)][d_next[:4]][0] += 1 if hit else 0
                    band_year[(alpha, tier)][d_next[:4]][1] += 1
            # cycle ledger
            oc = cycle_open.get(k2)
            if oc is None and pred_up and live >= BAND and issue_px > 0:
                cycle_open[k2] = (issue_d, issue_px)
            elif oc is not None and not pred_up and issue_px > 0 and issue_d > oc[0]:
                cycle_trades[alpha].append(
                    {"symbol": sym, "in": oc[0], "out": issue_d,
                     "ret_pct": round(100 * (issue_px / oc[1] - 1.0), 3)})
                cycle_open.pop(k2, None)
            # morphology ledger
            mo = morph_open.get(k2)
            if mo is not None and issue_px > 0 and issue_d > mo["issue_d"]:
                mo["gates"] += 1
                ret_now = 100 * (issue_px / mo["px"] - 1.0)
                if ret_now > mo["peak_ret"]:
                    mo["peak_ret"] = ret_now
                    mo["peak_gate"] = mo["gates"]
                hist = morph_store.get(mo["species"], [])
                target = (int(np.median(hist[-50:])) if len(hist) >= 3 else None)
                ripe = target is not None and mo["gates"] >= max(1, target)
                collapse = not pred_up
                if ripe or collapse:
                    morph_trades[alpha].append(
                        {"symbol": sym, "in": mo["issue_d"], "out": issue_d,
                         "ret_pct": round(ret_now, 3),
                         "reason": "RIPE" if ripe else "COLLAPSE"})
                    morph_store[mo["species"]].append(mo["peak_gate"])
                    morph_open.pop(k2, None)
            if morph_open.get(k2) is None and pred_up and live >= BAND and issue_px > 0:
                morph_open[k2] = {"species": sp, "issue_d": issue_d,
                                  "px": issue_px, "gates": 0,
                                  "peak_ret": 0.0, "peak_gate": 0}
        if disp > 0:
            store_pos[sp] += 1
        elif disp < 0:
            store_neg[sp] += 1

    def harvest_summary(trades):
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
                    cash += open_pos.pop(i) * (1 + evs[i]["ret_pct"] / 100)
                    held.discard(evs[i]["symbol"])
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
        return {"trades": len(trades),
                "wr_pct": round(100 * float((rets > 0).mean()), 2),
                "mean_pct": round(float(rets.mean()), 2),
                "median_pct": round(float(np.median(rets)), 2),
                "by_year_wr": {y: {"n": len(v), "wr": round(100 * float((np.array(v) > 0).mean()), 1)}
                               for y, v in sorted(by.items())},
                "book_total_pct": round(100 * (cash / 100_000.0 - 1), 2),
                "book_by_year": byy}

    result = {"frame": "field-state conditioned schema memory (energy + herd breadth)",
              "tiers": {}, "cycle_harvest": {}, "morphology_harvest": {}}
    for alpha in ("bigram", "bigram_E", "bigram_EG"):
        tier_out = {}
        for tier in TIERS:
            h, n = band_stats[alpha][tier]
            yr = {y: f"{v[0]}/{v[1]}" for y, v in sorted(band_year[(alpha, tier)].items())}
            tier_out[str(tier)] = {"n": n, "hit_pct": round(100 * h / n, 2) if n else None,
                                   "by_year": yr}
        result["tiers"][alpha] = tier_out
        result["cycle_harvest"][alpha] = harvest_summary(cycle_trades.get(alpha, []))
        result["morphology_harvest"][alpha] = harvest_summary(morph_trades.get(alpha, []))

    out = os.path.join(OUT_DIR, "ch4_uf_spectrum_field.json")
    with open(out, "w") as f:
        json.dump(result, f, indent=1)
    print(json.dumps(result["tiers"], indent=1)[:2500])
    print("filed:", out)


if __name__ == "__main__":
    main()
