"""
population_reading_backfill.py — the standing perception layer
==============================================================

2026-08-19, Joseph's frame: cheap investing basics remove the trash;
the kernel reads every REAL life; herd context and governance sit
above. This tool builds the reading layer: every validated life
through the canonical v2 chain at one reading per completed daily
close — the whole stored history — filed per symbol and appendable
nightly (the chain is strictly recursive; a nightly append costs one
gate step per stock).

Input:  a validated universe CSV (symbol index) + ch4_live_store
Output: artifacts/ch4_uf/population_lanes/<SYM>.parquet with the
        chain's own day-state fields — no derived extras, no
        thresholds, no classes. Perception only.

Resumable: symbols with an existing file whose last date matches the
store's latest close are skipped, so reruns cost nothing and the
same command is tonight's (and every night's) refresh.

Usage:  python tools/population_reading_backfill.py <universe.csv> [workers]
"""

from __future__ import annotations

import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
STORE = os.path.join(ROOT, "ch4_live_store.parquet")
OUT_DIR = os.path.join(ROOT, "artifacts", "ch4_uf", "population_lanes")

FIELDS = ("D_k", "B_k", "Rev_k", "U_star_k", "URF", "R_res", "S_UF",
          "F_n", "rho_n", "s_n", "regime", "ignition", "extinction",
          "gate_count", "action")


def read_life(args) -> str:
    sym, dates, closes, volumes, latest_s = args
    out_path = os.path.join(OUT_DIR, f"{sym}.parquet")
    try:
        if os.path.exists(out_path):
            prior = pd.read_parquet(out_path, columns=["date"])
            if len(prior) and str(prior["date"].iloc[-1]) == latest_s:
                return f"{sym}: current"
        from tools.ch4_uf_kernel_v2 import replay_symbol_v2
        states = replay_symbol_v2(dates, closes, volumes, warmup=60)
        rows = []
        for d, c, s in zip(dates, closes, states):
            if s is None:
                continue
            row = {"date": str(d)[:10], "close": float(c)}
            for f in FIELDS:
                row[f] = getattr(s, f)
            rows.append(row)
        if not rows:
            return f"{sym}: EMPTY"
        tmp = out_path + f".tmp{os.getpid()}"
        pd.DataFrame(rows).to_parquet(tmp)
        os.replace(tmp, out_path)
        return f"{sym}: {len(rows)} readings"
    except Exception as err:  # noqa: BLE001 — one life must never kill the pass
        return f"{sym}: FAILED {type(err).__name__}: {err}"


def main() -> None:
    universe_csv = sys.argv[1]
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    os.makedirs(OUT_DIR, exist_ok=True)
    symbols = pd.read_csv(universe_csv)["Symbol"].astype(str).tolist()
    store = pd.read_parquet(STORE, columns=["Date", "Symbol", "Close", "Volume"])
    store["Date"] = pd.to_datetime(store["Date"])
    latest_s = str(store["Date"].max())[:10]
    print(f"universe {len(symbols):,} lives; store latest {latest_s}; "
          f"{workers} workers", flush=True)
    jobs = []
    for sym, sub in store[store["Symbol"].isin(symbols)].groupby("Symbol"):
        sub = sub.sort_values("Date")
        jobs.append((sym, sub["Date"].to_numpy(),
                     sub["Close"].to_numpy(dtype=float),
                     sub["Volume"].to_numpy(dtype=float), latest_s))
    del store
    t0 = time.time()
    done = failed = 0
    with Pool(workers) as pool:
        for i, msg in enumerate(pool.imap_unordered(read_life, jobs, chunksize=8)):
            if "FAILED" in msg or "EMPTY" in msg:
                failed += 1
                print(f"  {msg}", flush=True)
            done += 1
            if done % 200 == 0:
                rate = done / (time.time() - t0)
                print(f"[{done}/{len(jobs)}] {rate:.1f} lives/s, "
                      f"eta {(len(jobs) - done) / max(rate, 0.01) / 60:.0f} min, "
                      f"failures {failed}", flush=True)
    print(f"DONE {done} lives, {failed} failures/empties, "
          f"{(time.time() - t0) / 60:.1f} min", flush=True)


if __name__ == "__main__":
    main()
