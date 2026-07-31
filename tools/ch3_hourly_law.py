"""
ch3_hourly_law.py — does the species law hold one rung finer?
=============================================================

The established daily law: temporal-geometric species (mosaic-class
bigrams over the conformant v2 gate stream) predict their own
completions at 65.9% across 11 years, every year, both directions.

This is the SAME machinery — gate_stream, coarse context, schema
memory, causal global-date-order accumulation, imported unchanged from
tools/ch4_uf_spectrum.py — run on HOURLY session bars (2016-2026,
full-depth store, 5,016 symbols). Nothing re-tuned: the gate stream is
self-scaled, so the rung is the only change.

Question answered (declared before measurement): at the hourly rung,
do species with causal record n >= 20 and consistency >= 0.75 at issue
time predict the next gate's displacement sign at a rate comparable to
the daily law — per year, both alphabets? This is the existence test
for CH3's brain (quick-cash holding = one hourly gate), not a strategy.

Output: artifacts/ch4_uf/ch3_hourly_law.json
        artifacts/ch4_uf/ch3_hourly_band_preds.parquet (band >= 0.70
        causal predictions with issue/exit prices, for the harvest
        construction step)

Usage: python tools/ch3_hourly_law.py [N_SYMBOLS]
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from collections import defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.ch4_uf_spectrum import (  # noqa: E402
    gate_stream, coarse_context_map, life_fraction, W)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.environ.get("CH3_STORE") or os.path.join(
    ROOT, "ch4_hourly_universe_full.parquet")
OUT = os.path.join(ROOT, "artifacts", "ch4_uf", "ch3_hourly_law.json")
PREDS_OUT = os.path.join(ROOT, "artifacts", "ch4_uf",
                         "ch3_hourly_band_preds.parquet")
LIFE_MIN = 0.90
PRICE_FLOOR = 5.0
MIN_BARS = 3500            # ~2 years of session hours
BAND = 0.75
KEEP_BAND = 0.70           # persist predictions at >= this live band
ALPHAS = ("bigram", "bigram_ctx", "pooled_ctx")
# sharding: CH3_OBS_SHARD="k/K" collects observations for its slice of
# the universe and exits; CH3_OBS_MERGE=1 loads all shards and runs the
# (serial, cheap) causal ledger. Species are identified by a
# deterministic blake2b 64-bit id — never the salted builtin hash.
SHARD = os.environ.get("CH3_OBS_SHARD")
MERGE = os.environ.get("CH3_OBS_MERGE") == "1"
SHARD_DIR = os.path.join(ROOT, "artifacts", "ch4_uf", "law_obs_shards")


def sp_id(alpha: str, species) -> int:
    h = hashlib.blake2b(f"{alpha}|{species!r}".encode(), digest_size=8)
    return int.from_bytes(h.digest(), "big") >> 1


def universe(limit):
    g = pd.read_parquet(STORE, columns=["Symbol", "Close"]) \
        .groupby("Symbol")["Close"]
    stats = pd.DataFrame({"bars": g.size(), "med": g.median()})
    return sorted(stats[(stats["bars"] >= MIN_BARS)
                        & (stats["med"] >= PRICE_FLOOR)]
                  .index.tolist())[:limit]


def collect_obs(syms, t0, tag=""):
    df = pd.read_parquet(STORE, columns=["Date", "Symbol", "Close", "Volume"],
                         filters=[("Symbol", "in", list(syms))])
    ts = pd.to_datetime(df["Date"]).dt.tz_localize("UTC") \
        .dt.tz_convert("America/New_York")
    rth = (ts.dt.hour >= 9) & (ts.dt.hour <= 15) & (ts.dt.weekday <= 4)
    df = df[rth].copy()
    df["hkey"] = ts[rth].dt.strftime("%Y%m%d%H").to_numpy()
    print(f"{tag}session-hour rows: {len(df)} ({time.time()-t0:.0f}s)",
          flush=True)
    obs = []
    kept = 0
    for i, (sym, sub) in enumerate(df.groupby("Symbol", sort=True)):
        sub = sub.sort_values("hkey")
        dates = sub["hkey"].tolist()
        closes = sub["Close"].to_numpy(dtype=float)
        vols = sub["Volume"].to_numpy(dtype=float)
        lf = life_fraction(closes)
        if lf[-1] < LIFE_MIN:
            continue
        kept += 1
        try:
            gs = gate_stream(dates, closes, vols)
            ctx = coarse_context_map(dates, closes, vols)
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
            exit_px = float(closes[tb_n - 1])
            cx = ctx[tb_cur - 1]
            pool_prev = (cls_prev[0][2], cls_prev[1])
            pool_cur = (cls_cur[0][2], cls_cur[1])
            for ai, (alpha, species) in enumerate((
                ("bigram", (cls_prev, cls_cur)),
                ("bigram_ctx", (cls_prev, cls_cur, cx)),
                ("pooled_ctx", (pool_prev, pool_cur, cx)),
            )):
                obs.append((d_next, sp_id(alpha, species), ai, disp_next,
                            sym, issue_d, exit_d, issue_px, exit_px))
        if (i + 1) % 200 == 0:
            print(f"{tag}  [{i+1}/{len(syms)}] obs={len(obs)} "
                  f"{time.time()-t0:.0f}s", flush=True)
    return kept, pd.DataFrame(obs, columns=[
        "d_next", "sp", "alpha", "disp", "sym", "issue_d", "exit_d",
        "issue_px", "exit_px"])


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10 ** 9
    t0 = time.time()

    if SHARD:
        k, K = (int(x) for x in SHARD.split("/"))
        syms = [s for j, s in enumerate(universe(limit)) if j % K == k]
        kept, odf = collect_obs(syms, t0, tag=f"[s{k}] ")
        os.makedirs(SHARD_DIR, exist_ok=True)
        odf.to_parquet(os.path.join(SHARD_DIR, f"obs_{k}_{K}.parquet"),
                       index=False)
        print(f"[s{k}] shard filed: kept={kept} obs={len(odf)} "
              f"({time.time()-t0:.0f}s)")
        return

    if MERGE:
        parts = sorted(os.listdir(SHARD_DIR))
        odf = pd.concat([pd.read_parquet(os.path.join(SHARD_DIR, p))
                         for p in parts], ignore_index=True)
        kept = -1
        print(f"merged {len(parts)} shards: obs={len(odf)} "
              f"({time.time()-t0:.0f}s)", flush=True)
    else:
        kept, odf = collect_obs(universe(limit), t0)

    odf = odf.sort_values(["d_next", "sym"], kind="mergesort")
    obs = list(odf.itertuples(index=False, name=None))
    print(f"eligible: {kept} symbols; observations: {len(obs)} "
          f"({time.time()-t0:.0f}s)", flush=True)

    # causal schema accumulation, strict global completion order
    obs.sort(key=lambda x: (x[0], x[3]))
    pos = defaultdict(int)
    neg = defaultdict(int)
    agg = defaultdict(lambda: defaultdict(lambda: [0, 0]))   # alpha -> year -> [hit, n]
    keep_rows = []
    alpha0_ids = set()          # species ids seen under the bigram alphabet
    for d_next, sp, ai, disp, sym, issue_d, exit_d, ipx, epx in obs:
        p, q = pos[sp], neg[sp]
        n = p + q
        if n >= W:
            f = p / n
            band = max(f, 1 - f)
            pred = 1 if f >= 0.5 else -1
            if band >= BAND and disp != 0:
                y = issue_d[:4]
                a = agg[ALPHAS[ai]][y]
                a[0] += 1 if (disp > 0) == (pred > 0) else 0
                a[1] += 1
            if band >= KEEP_BAND:
                keep_rows.append((ALPHAS[ai], int(sp), issue_d, exit_d,
                                  sym, pred, band, n, ipx, epx,
                                  float(disp)))
        if disp > 0:
            pos[sp] += 1
        elif disp < 0:
            neg[sp] += 1
        if ai == 0:
            alpha0_ids.add(sp)

    # spectrum census vs null (existence check at the rung)
    species_n = {sp: (pos[sp] + neg[sp], pos[sp] / (pos[sp] + neg[sp]))
                 for sp in pos.keys() | neg.keys()
                 if pos[sp] + neg[sp] >= W and sp in alpha0_ids}
    cons = np.array([max(f, 1 - f) for _, f in species_n.values()])
    ns = np.array([n for n, _ in species_n.values()])
    base = (sum(v for k, v in pos.items() if k in alpha0_ids)
            / max(1, sum(v for k, v in pos.items() if k in alpha0_ids)
                  + sum(v for k, v in neg.items() if k in alpha0_ids)))
    rng = np.random.default_rng(20260731)
    null_cons = []
    for n in ns:
        draws = rng.binomial(n, base, size=20)
        null_cons.extend([max(d / n, 1 - d / n) for d in draws])
    null_cons = np.array(null_cons) if null_cons else np.array([0.5])
    edges = [0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0]
    hist_real = np.histogram(cons, bins=edges)[0].tolist()
    hist_null = (np.histogram(null_cons, bins=edges)[0] / 20.0).tolist()

    result = {
        "frame": "species law at the HOURLY rung — same machinery, "
                 "same constants, finer bars; band>=0.75 causal "
                 "aggregate per year",
        "store": os.path.basename(STORE),
        "eligible_symbols": kept,
        "observations": len(obs),
        "bigram_species_n_ge_W": len(species_n),
        "field_base_up_rate": round(base, 4),
        "spectrum_hist_edges": edges,
        "spectrum_real": hist_real,
        "spectrum_null_mean": hist_null,
        "band_aggregate_by_year": {
            alpha: {y: {"n": v[1],
                        "hit_pct": round(100 * v[0] / v[1], 1) if v[1] else None}
                    for y, v in sorted(years.items())}
            for alpha, years in agg.items()},
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(result, f, indent=1)
    if keep_rows:
        pd.DataFrame(keep_rows, columns=[
            "alpha", "species", "issue_d", "exit_d", "sym", "pred",
            "band", "n_at_issue", "issue_px", "exit_px", "disp_next"
        ]).to_parquet(PREDS_OUT, index=False)
    print(json.dumps({k: result[k] for k in
                      ("eligible_symbols", "observations",
                       "bigram_species_n_ge_W", "field_base_up_rate",
                       "spectrum_real", "spectrum_null_mean",
                       "band_aggregate_by_year")}, indent=1))
    print("filed:", OUT, "| preds:", PREDS_OUT if keep_rows else "none")


if __name__ == "__main__":
    main()
