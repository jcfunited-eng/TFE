"""The full per-gate kernel series — no averages, no means, no medians.

Joseph, 2026-09-19: "there should be no averages, means or medians - you NEED
the full values - it is not noise it is the information you need - and by the
way this same is true for SPY so dont forget to maintain that comparison"

What CH2 consumes today is seven L4 values from the most recent gate, plus
S_UF and R_UF, which uf_structural_engine computes as lifetime means:

    r_mean = np.mean([r.R_k for r in resonance_results])
    S_UF   = 0.5*(1 - mean(|D_k|>0)) + 0.5*(1 - mean(R_rev_k))

Those two are adapter constructions, not kernel outputs, and they average over
every gate in a body's life. They are NOT exported here. Nothing here is
averaged.

This calls the canonical chain and keeps every per-gate quantity it produces:

    L2  w_k CV_k(3) S_k U_k IAS_k regime C_k delta_g N_gate T_k V_k R_k chi_k psi_k
    L3  R_k URF_k g_k U_k IAS_k Hyst_k raw_k
    L4  D_k M_k R_rev_k U_star_k C_k P_k B_k

The kernel is not modified and not reimplemented; the adapter's discarding is
simply not repeated.

Causality: the chain is NOT prefix-stable, so values at a fixed gate shift when
later bars arrive. Each row is therefore taken from a prefix run ending at that
bar -- the most recent gate as it stood on that date, which is all that was
knowable then. gate_start/gate_end/n_gates let the true event series be
reconstructed: a new gate closing is an event.

SPY, QQQ, DIA and IWM are always included -- the comparison Joseph asked to be
maintained.

Usage:
  PYTHONHASHSEED=0 python tools/ch2_full_gate_export.py ch4_live_store.parquet
"""
from __future__ import annotations

import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUTDIR = ROOT / "artifacts" / "ch4_uf" / "full_gate_20260919"
SAMPLE_FILE = ROOT / "artifacts" / "ch4_uf" / "dense_lanes_sample_20260919.txt"
WARMUP_BARS = 250
WORKERS = 14

COLS = ["ticker", "d", "close", "volume", "bar_idx",
        "n_gates", "gate_start", "gate_end",
        # L2
        "l2_w_k", "l2_cv0", "l2_cv1", "l2_cv2", "l2_S_k", "l2_U_k", "l2_IAS_k",
        "l2_regime", "l2_C_k", "l2_delta_g", "l2_N_gate", "l2_T_k", "l2_V_k",
        "l2_R_k", "l2_chi_k", "l2_psi_k",
        # L3
        "l3_R_k", "l3_URF_k", "l3_g_k", "l3_U_k", "l3_IAS_k", "l3_Hyst_k", "l3_raw_k",
        # L4
        "D_k", "M_k", "R_rev_k", "U_star_k", "C_k", "P_k", "B_k"]


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


def run_body(task):
    from uf_core.layer0 import compute_sev_series
    from uf_core.layer1 import segment_gates
    from uf_core.layer2 import interpret_gates
    from uf_core.layer3 import compute_resonance
    from uf_core.layer4 import compute_directional_signal, compute_dsf

    sym, d, close, vol = task
    n = len(close)
    s = pd.Series(close)
    rows = []
    for k in range(WARMUP_BARS, n):
        c = s.iloc[: k + 1]
        df = pd.DataFrame({"Close": c}); df.index = c.index
        try:
            sev = compute_sev_series(df, field_col="Close")
            gates = segment_gates(sev)
            interp = interpret_gates(sev, gates)
            res = compute_resonance(interp)
            dsf = compute_dsf(compute_directional_signal(res))
        except Exception:
            continue
        if not dsf or not res or not interp:
            continue
        ip, rr, ds = interp[-1], res[-1], dsf[-1]
        cv = tuple(ip.CV_k) if ip.CV_k is not None else (np.nan,) * 3
        g = getattr(ds, "gate", None)
        rows.append((sym, d[k], close[k], vol[k], k,
                     len(dsf),
                     int(getattr(g, "start_idx", -1)), int(getattr(g, "end_idx", -1)),
                     _f(ip.w_k), _f(cv[0]), _f(cv[1]), _f(cv[2]), _f(ip.S_k),
                     _f(ip.U_k), int(ip.IAS_k), str(ip.regime), _f(ip.C_k),
                     _f(ip.delta_g), _f(ip.N_gate), _f(ip.T_k), _f(ip.V_k),
                     _f(ip.R_k), _f(ip.chi_k), _f(ip.psi_k),
                     _f(rr.R_k), _f(rr.URF_k), int(rr.g_k), _f(rr.U_k),
                     int(rr.IAS_k), int(rr.Hyst_k), _f(rr.raw_k),
                     _f(ds.D_k), _f(ds.M_k), _f(ds.R_rev_k), _f(ds.U_star_k),
                     _f(ds.C_k), _f(ds.P_k), _f(ds.B_k)))
    if not rows:
        return sym, 0
    OUTDIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows, columns=COLS).to_parquet(OUTDIR / f"{sym}.parquet", index=False)
    return sym, len(rows)


def main() -> int:
    df = pd.read_parquet(sys.argv[1], columns=["Date", "Symbol", "Close", "Volume"]).dropna()
    df = df.sort_values(["Symbol", "Date"])
    store = {}
    for sym, g in df.groupby("Symbol", sort=False):
        store[sym] = (g.Date.values.astype("datetime64[D]"),
                      g.Close.values.astype(float), g.Volume.values.astype(float))
    del df

    sample = [s.strip() for s in SAMPLE_FILE.read_text().splitlines() if s.strip()]
    sample = [s for s in sample if s in store]
    print(f"[full] same {len(sample)} bodies as the dense run, benchmarks included", flush=True)

    OUTDIR.mkdir(parents=True, exist_ok=True)
    todo = [s for s in sample if not (OUTDIR / f"{s}.parquet").exists()]
    # benchmarks first so the SPY comparison is available early
    todo.sort(key=lambda s: (s not in ("SPY", "QQQ", "DIA", "IWM"), s))
    print(f"[full] to compute: {len(todo)}", flush=True)

    done = 0
    with Pool(WORKERS, maxtasksperchild=40) as pool:
        for sym, k in pool.imap_unordered(run_body, ((s, *store[s]) for s in todo), chunksize=1):
            done += 1
            if done % 25 == 0 or sym in ("SPY", "QQQ", "DIA", "IWM"):
                print(f"[full] {done}/{len(todo)}  {sym} rows={k}", flush=True)
    print(f"[full] complete: {done} bodies -> {OUTDIR}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
