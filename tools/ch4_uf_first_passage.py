"""
ch4_uf_spectrum_herd.py — species conditioned on their OWN herd's weather
=========================================================================

Joe's refinement (2026-07-30): the herd = the stock's peer cohort — same
type and pedigree — NOT the whole market ("it doesn't matter what the
solar cycle is — the sun is always hot — what you're doing is predicting
the flares"). A flare (species event) completes when greed is spreading
through its OWN active region.

PEDIGREE (kernel-native, causal, no hand labels): each vertex each day
sits in a cell (σ-class, attention-class, price-class), each class the
cross-sectional {lo,mid,hi} band of, respectively: trailing-W variance
of the log field (the kernel's σ), trailing-W mean volume attention
(r), and log close. Bands at the pinned 25/75 quantiles of that DAY's
eligible cross-section — causal (uses only day-t values). 27 herds;
membership drifts slowly with the vertex's character.

HERD WEATHER: within each cell each day —
  herd ENERGY  E_c(t) = mean per-bar structural action of members
  herd GREED   G_c(t) = fraction of members whose close rose
each banded against the CELL's own trailing W=20 days (pinned 25/75)
→ herd state (E-band, G-band). Strictly trailing.

ALPHABETS: bigram (control), bigram_H (species × herd-E band),
bigram_HG (species × herd-E × herd-G). Same causal machinery, tier
curves, and harvest ledgers as the field tool. All raw; nothing tuned.

Usage: CH4_STORE=... python tools/ch4_uf_spectrum_herd.py [N]
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
TIERS = (0.75, 0.85, 0.90, 0.95)


def trailing_band3(series):
    n = len(series)
    out = np.full(n, -1, dtype=int)
    for t in range(n):
        w0 = max(0, t - W)
        win = series[w0:t]
        win = win[np.isfinite(win)]
        if len(win) < W // 2:
            continue
        v = series[t]
        if not np.isfinite(v):
            continue
        lo, hi = np.percentile(win, 25), np.percentile(win, 75)
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
    print(f"universe: {len(uni)} symbols, {nD} days")

    # ---- PASS 0: per-symbol daily character matrices (float32)
    S = len(uni)
    sym_ix = {s: i for i, s in enumerate(uni)}
    M_sig = np.full((S, nD), np.nan, dtype=np.float32)   # kernel sigma
    M_att = np.full((S, nD), np.nan, dtype=np.float32)   # trailing mean r
    M_px = np.full((S, nD), np.nan, dtype=np.float32)    # log close
    M_act = np.full((S, nD), np.nan, dtype=np.float32)   # per-bar action
    M_up = np.full((S, nD), np.nan, dtype=np.float32)    # up-move flag
    M_el = np.zeros((S, nD), dtype=bool)                 # eligibility
    frames = {}
    t0 = time.time()
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
        r_trail = np.copy(l0.r)
        for t in range(len(closes)):
            w0 = max(0, t - W + 1)
            r_trail[t] = float(np.mean(l0.r[w0: t + 1]))
        el = (lf >= LIFE_MIN) & (closes >= PRICE_FLOOR)
        si = sym_ix[sym]
        for t, d in enumerate(dates):
            di = d_index[d]
            if not el[t]:
                continue
            M_el[si, di] = True
            M_sig[si, di] = l0.sigma[t]
            M_att[si, di] = r_trail[t]
            M_px[si, di] = np.log(max(closes[t], 1e-8))
            M_act[si, di] = l0.perV[t]
            if t >= 1:
                M_up[si, di] = 1.0 if closes[t] > closes[t - 1] else 0.0
        if (i + 1) % 500 == 0:
            print(f"  pass0 [{i+1}/{len(uni)}] {time.time()-t0:.0f}s", flush=True)

    # ---- cells per day: cross-sectional 25/75 bands of (sigma, att, px)
    print("building pedigree cells + herd weather...")
    cell_of = np.full((S, nD), -1, dtype=np.int16)
    herd_E = defaultdict(lambda: np.full(nD, np.nan))
    herd_G = defaultdict(lambda: np.full(nD, np.nan))
    for di in range(nD):
        el = M_el[:, di]
        if el.sum() < 30:
            continue
        def bands(col):
            vals = col[el]
            lo, hi = np.percentile(vals, 25), np.percentile(vals, 75)
            b = np.full(S, -1, dtype=np.int8)
            b[el] = np.where(col[el] <= lo, 0, np.where(col[el] >= hi, 2, 1))
            return b
        b_sig = bands(M_sig[:, di])
        b_att = bands(M_att[:, di])
        b_px = bands(M_px[:, di])
        cells = b_sig.astype(np.int16) * 9 + b_att.astype(np.int16) * 3 + b_px.astype(np.int16)
        cells[~el] = -1
        cell_of[:, di] = cells
        for c in range(27):
            mask = cells == c
            if mask.sum() >= 5:
                herd_E[c][di] = float(np.nanmean(M_act[mask, di]))
                ups = M_up[mask, di]
                ups = ups[np.isfinite(ups)]
                if len(ups):
                    herd_G[c][di] = float(np.mean(ups))
    herd_E_band = {c: trailing_band3(herd_E[c]) for c in herd_E}
    herd_G_band = {c: trailing_band3(herd_G[c]) for c in herd_G}
    print("herd weather ready")

    # ---- PASS 2: observations with herd-state alphabets
    obs = []
    for i, (sym, (dates, closes, vols)) in enumerate(frames.items()):
        try:
            gs = gate_stream(dates, closes, vols)
        except Exception:
            continue
        si = sym_ix[sym]
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
            c = int(cell_of[si, di])
            if c < 0:
                continue
            eb = int(herd_E_band.get(c, np.full(nD, -1))[di])
            gb = int(herd_G_band.get(c, np.full(nD, -1))[di])
            if eb < 0 or gb < 0:
                continue
            big = (cls_prev, cls_cur)
            obs.append((str(d_next), big, eb, gb, disp_next, sym,
                        issue_d, exit_d, issue_px, tb_cur - 1))
        if (i + 1) % 500 == 0:
            print(f"  pass2 [{i+1}/{len(frames)}] obs={len(obs)}", flush=True)
    print(f"observations: {len(obs)}")

    # ---- causal accumulation: FIRST-PASSAGE HARVEST
    # Entry: band >= 0.75 UP prediction (most specific earned record wins
    # via backoff). Per-species causal PEAK-YIELD history from completed
    # cycles; targets at the pinned quantile family q in {25, 50, 75} of
    # prior peaks (>= 3 completed cycles). A trade at quantile q exits at
    # FIRST TOUCH of its target (win at target) scanning the symbol's
    # daily closes, else at the ordinary collapse exit. The CALIBRATION —
    # realized touch rate vs the rate the species' own peak distribution
    # predicts — is the deterministic-physics claim under test.
    obs.sort(key=lambda x: (x[0], x[5]))
    S0p, S0n = defaultdict(int), defaultdict(int)
    S1p, S1n = defaultdict(int), defaultdict(int)
    S2p, S2n = defaultdict(int), defaultdict(int)
    QUANTS = (5, 10, 15, 25)
    fp_open = {q: {} for q in QUANTS}        # sym -> position
    peak_store = defaultdict(list)           # species -> [peak_ret history]
    trough_store = defaultdict(list)         # species -> [adverse excursion history]
    shape_store = defaultdict(list)          # species -> [peak_gate history]
    fp_trades = {q: [] for q in QUANTS}
    plain_open = {}
    plain_trades = []

    def sym_closes(sym):
        dts, cls, vols = frames[sym]
        return cls

    for d_next, big, eb, gb, disp, sym, issue_d, exit_d, issue_px, issue_ix in obs:
        k0, k1, k2s = big, (big, eb), (big, eb, gb)
        cand = None
        for lvl, (kp, P, Q) in enumerate((
                (k2s, S2p, S2n), (k1, S1p, S1n), (k0, S0p, S0n))):
            p, q = P[kp], Q[kp]
            if p + q >= W:
                cand = (lvl, p, q)
                break
        if cand is not None:
            lvl, p, q = cand
            n = p + q
            pred_up = p >= q
            live = max(p, q) / n

            # ---- plain morphology ledger (control; also feeds stores)
            mo = plain_open.get(sym)
            if mo is not None and issue_px > 0 and issue_d > mo["issue_d"]:
                mo["gates"] += 1
                ret_now = 100 * (issue_px / mo["px"] - 1.0)
                if ret_now > mo["peak_ret"]:
                    mo["peak_ret"] = ret_now
                    mo["peak_gate"] = mo["gates"]
                cls_all = sym_closes(sym)
                seg_lo = cls_all[mo["ix"] + 1: issue_ix + 1]
                if len(seg_lo):
                    lo_ret = 100 * (float(np.min(seg_lo)) / mo["px"] - 1.0)
                    if lo_ret < mo["trough_ret"]:
                        mo["trough_ret"] = lo_ret
                hist = shape_store.get(mo["species"], [])
                target_g = (int(np.median(hist[-50:])) if len(hist) >= 3 else None)
                ripe = target_g is not None and mo["gates"] >= max(1, target_g)
                collapse = not pred_up
                if ripe or collapse:
                    plain_trades.append(
                        {"symbol": sym, "in": mo["issue_d"], "out": issue_d,
                         "ret_pct": round(ret_now, 3),
                         "reason": "RIPE" if ripe else "COLLAPSE"})
                    shape_store[mo["species"]].append(mo["peak_gate"])
                    peak_store[mo["species"]].append(mo["peak_ret"])
                    trough_store[mo["species"]].append(mo["trough_ret"])
                    plain_open.pop(sym, None)
            if plain_open.get(sym) is None and pred_up and live >= BAND and issue_px > 0:
                plain_open[sym] = {"species": k0, "issue_d": issue_d,
                                   "px": issue_px, "gates": 0, "ix": issue_ix,
                                   "peak_ret": 0.0, "peak_gate": 0,
                                   "trough_ret": 0.0}

            # ---- first-passage ledgers, one per declared quantile
            for qq in QUANTS:
                fo = fp_open[qq].get(sym)
                if fo is not None and issue_px > 0 and issue_d > fo["issue_d"]:
                    cls = sym_closes(sym)
                    seg = cls[fo["last_ix"] + 1: issue_ix + 1]
                    tgt_px = fo["px"] * (1.0 + fo["target"] / 100.0)
                    stp_px = fo["px"] * (1.0 + fo["stop"] / 100.0)
                    hit_t = -1
                    hit_s = -1
                    for jj, pxv in enumerate(seg):
                        if hit_t < 0 and pxv >= tgt_px:
                            hit_t = jj
                        if hit_s < 0 and pxv <= stp_px:
                            hit_s = jj
                        if hit_t >= 0 or hit_s >= 0:
                            break
                    if hit_t >= 0 and (hit_s < 0 or hit_t <= hit_s):
                        fp_trades[qq].append(
                            {"symbol": sym, "in": fo["issue_d"], "out": issue_d,
                             "ret_pct": round(fo["target"], 3),
                             "reason": "TARGET"})
                        fp_open[qq].pop(sym, None)
                    elif hit_s >= 0:
                        fp_trades[qq].append(
                            {"symbol": sym, "in": fo["issue_d"], "out": issue_d,
                             "ret_pct": round(fo["stop"], 3),
                             "reason": "STOP"})
                        fp_open[qq].pop(sym, None)
                    else:
                        collapse = not pred_up
                        if collapse:
                            ret_now = 100 * (issue_px / fo["px"] - 1.0)
                            fp_trades[qq].append(
                                {"symbol": sym, "in": fo["issue_d"], "out": issue_d,
                                 "ret_pct": round(ret_now, 3),
                                 "reason": "COLLAPSE"})
                            fp_open[qq].pop(sym, None)
                        else:
                            fo["last_ix"] = issue_ix
                if fp_open[qq].get(sym) is None and pred_up and live >= BAND and issue_px > 0:
                    hist = peak_store.get(k0, [])
                    thist = trough_store.get(k0, [])
                    if len(hist) >= 3 and len(thist) >= 3:
                        tgt = float(np.percentile(np.array(hist[-50:]), qq))
                        stop = float(np.percentile(np.array(thist[-50:]), 25))
                        # stop = the species' deep adverse band (25th pct of
                        # trough history = worse than 75% of its cycles)
                        # ENERGY-POSITIVE GATE: collect only flares whose
                        # typical yield covers their typical adverse
                        # excursion (target >= |stop|, ratio 1 — the
                        # natural boundary, no invented constant)
                        if tgt > 0 and stop < 0 and tgt >= abs(stop):
                            fp_open[qq][sym] = {"species": k0, "issue_d": issue_d,
                                                "px": issue_px, "target": tgt,
                                                "stop": stop, "last_ix": issue_ix}
        if disp > 0:
            S2p[k2s] += 1; S1p[k1] += 1; S0p[k0] += 1
        elif disp < 0:
            S2n[k2s] += 1; S1n[k1] += 1; S0n[k0] += 1

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
        reason_split = {}
        for rn in ("RIPE", "COLLAPSE", "TARGET", "STOP"):
            rr = np.array([t["ret_pct"] for t in trades if t.get("reason") == rn])
            if len(rr):
                reason_split[rn] = {"n": int(len(rr)),
                                    "wr": round(100 * float((rr > 0).mean()), 2),
                                    "mean": round(float(rr.mean()), 2)}
        return {"trades": len(trades),
                "reason_split": reason_split,
                "wr_pct": round(100 * float((rets > 0).mean()), 2),
                "mean_pct": round(float(rets.mean()), 2),
                "median_pct": round(float(np.median(rets)), 2),
                "by_year_wr": {y: {"n": len(v), "wr": round(100 * float((np.array(v) > 0).mean()), 1)}
                               for y, v in sorted(by.items())},
                "book_total_pct": round(100 * (cash / 100_000.0 - 1), 2),
                "book_by_year": byy}

    result = {"frame": "first-passage harvest (species peak-quantile targets)",
              "expected_touch_note": "target at peak-quantile q predicts a "
                  "touch rate near (100-q)% of completed cycles, path bonus on top",
              "plain_morphology_control": harvest_summary(plain_trades)}
    for qq in QUANTS:
        result[f"fp_q{qq}"] = harvest_summary(fp_trades[qq])
    out = os.path.join(OUT_DIR, "ch4_uf_first_passage.json")
    with open(out, "w") as f:
        json.dump(result, f, indent=1)
    print(json.dumps(result, indent=1)[:2500])
    print("filed:", out)


if __name__ == "__main__":
    main()
