"""Dense causal kernel lanes — the input every previous CH2 measurement lacked.

The production lane export covers a median of 13% of a body's sessions, because
CH2 calls the kernel once per ticker per day only for the names its scheduler
touched. Everything measured off that file was read from a gappy sample of a
series the kernel is meant to read continuously.

This runs the canonical production entry point, uf_structural_engine
.compute_uf_structural_state, once per bar per body on the prefix of closes up
to and including that bar. That is the only causal way to get the tuple: the
chain is NOT prefix-stable (M_k, U_star_k and B_k at index k change when later
bars are added), so reading a full-series run would be reading the future.

The kernel is not modified and not reimplemented. Nothing is filtered here;
filters belong to the measurement that consumes this.

Sample: SAMPLE_N tickers drawn with a blake2b-seeded generator (never the
builtin hash, which is salted per process).

Usage:
  PYTHONHASHSEED=0 python tools/ch2_dense_kernel_lanes.py ch4_live_store.parquet
"""
from __future__ import annotations

import hashlib
import os
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUTDIR = ROOT / "artifacts" / "ch4_uf" / "dense_lanes_20260919"
SAMPLE_N = 3000
WARMUP_BARS = 250          # agreed with Joseph; the kernel needs history first
MIN_BARS = 750             # so a sampled body has at least 500 usable readings
WORKERS = 19

def _load(path: str) -> dict[str, tuple]:
    df = pd.read_parquet(path, columns=["Date", "Symbol", "Close", "Volume"]).dropna()
    df = df.sort_values(["Symbol", "Date"])
    store = {}
    for sym, g in df.groupby("Symbol", sort=False):
        store[sym] = (g.Date.values.astype("datetime64[D]"),
                      g.Close.values.astype(float),
                      g.Volume.values.astype(float))
    return store


def run_body(task):
    # The parent holds the store and sends one body's arrays per task. Loading
    # the store inside each worker put 19 copies in memory and nearly OOMed.
    from uf_core.uf_structural_engine import compute_uf_structural_state
    sym, d, close, vol = task
    n = len(close)
    s = pd.Series(close)
    rows = []
    for k in range(WARMUP_BARS, n):
        st = compute_uf_structural_state(s.iloc[: k + 1])
        l5 = st.level5
        if l5.get("D_k") is None:
            continue
        rows.append((sym, d[k], close[k], vol[k],
                     float(st.level4["S_UF"]), float(st.level4["R_UF"]),
                     float(l5["D_k"]), float(l5["M_k"]), float(l5["R_rev_k"]),
                     float(l5["U_star_k"]), float(l5["C_k"]), float(l5["P_k"]),
                     float(l5["B_k"]), int(l5.get("gate_count") or 0), k))
    if not rows:
        return sym, 0
    out = pd.DataFrame(rows, columns=["ticker", "d", "close", "volume", "s_uf", "r_uf",
                                      "d_k", "m_k", "r_rev_k", "u_star_k", "c_k", "p_k",
                                      "b_k", "gate_count", "bar_idx"])
    OUTDIR.mkdir(parents=True, exist_ok=True)
    out.to_parquet(OUTDIR / f"{sym}.parquet", index=False)
    return sym, len(out)


def main() -> int:
    store_path = sys.argv[1]
    store = _load(store_path)
    universe = sorted(s for s, (d, c, v) in store.items() if len(c) >= MIN_BARS)
    print(f"[dense] bodies with >= {MIN_BARS} bars: {len(universe)}", flush=True)

    seed = int.from_bytes(hashlib.blake2b(b"ch2-dense-lanes-20260919", digest_size=8).digest(), "big")
    rng = np.random.default_rng(seed % (2**63))
    sample = sorted(rng.choice(universe, size=min(SAMPLE_N, len(universe)), replace=False).tolist())
    print(f"[dense] sample={len(sample)} seed={seed % (2**63)}", flush=True)
    (OUTDIR.parent / "dense_lanes_sample_20260919.txt").write_text("\n".join(sample))

    OUTDIR.mkdir(parents=True, exist_ok=True)
    todo = [s for s in sample if not (OUTDIR / f"{s}.parquet").exists()]
    print(f"[dense] to compute: {len(todo)}", flush=True)

    tasks = ((s, *store[s]) for s in todo)
    done = 0
    with Pool(WORKERS, maxtasksperchild=40) as pool:
        for sym, k in pool.imap_unordered(run_body, tasks, chunksize=1):
            done += 1
            if done % 50 == 0:
                print(f"[dense] {done}/{len(todo)} bodies  last={sym} rows={k}", flush=True)
    print(f"[dense] complete: {done} bodies written to {OUTDIR}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
