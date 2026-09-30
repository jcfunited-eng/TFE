"""Draw a stock's whole life as the kernel sees it — seeing first, no law.

Joe, 2026-10-01: "there will be a pattern for when the price goes up and
the price goes down — it really is not all that complicated."

One figure per stock per resolution (tau_D). Panels, top to bottom:
  price (log) with every gate boundary drawn; N_t (negative space) shaded
  resonance per gate: R_k (raw) and URF_k (gated) as steps
  D_k (+1/0/-1), R_rev_k marks, P_k
  M_k and B_k (bounded potential)
  U*_k and C_k
Everything is the production chain's own per-gate output (layer0 → layer4),
nothing averaged, nothing scored. tau_D set in this process only.

Usage: python3 tools/ch2_draw_life.py SYMBOL [SYMBOL...] --tau 0.10 --years 3
Writes artifacts/ch2_life/<SYMBOL>_tau<tau>.png
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "artifacts" / "ch2_life"


def chain(close: pd.Series):
    from uf_core.layer0 import compute_sev_series
    from uf_core.layer1 import segment_gates
    from uf_core.layer2 import interpret_gates
    from uf_core.layer3 import compute_resonance
    from uf_core.layer4 import compute_directional_signal, compute_dsf
    df = pd.DataFrame({"Close": close.values}, index=close.index)
    sev = compute_sev_series(df)
    gates = segment_gates(sev)
    interps = interpret_gates(sev, gates)
    res = compute_resonance(interps)
    dsf = compute_dsf(compute_directional_signal(res))
    return sev, gates, interps, res, dsf


def draw(symbol: str, close: pd.Series, tau: float, years: float) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import uf_core.config as cfg
    cfg.KERNEL_THRESHOLDS.tau_D = float(tau)
    sev, gates, interps, res, dsf = chain(close)
    n = len(close)
    idx = np.arange(n)
    dates = close.index
    start = max(0, n - int(years * 252))
    # per-bar step series from per-gate values
    def per_bar(vals):
        out = np.full(n, np.nan)
        for g, v in zip(gates, vals):
            out[g.start_idx: g.end_idx + 1] = v
        return out
    R = per_bar([r.R_k for r in res]); URF = per_bar([r.URF_k for r in res])
    D = per_bar([d.D_k for d in dsf]); RV = per_bar([d.R_rev_k for d in dsf]); P = per_bar([d.P_k for d in dsf])
    M = per_bar([d.M_k for d in dsf]); B = per_bar([d.B_k for d in dsf])
    U = per_bar([d.U_star_k for d in dsf]); C = per_bar([d.C_k for d in dsf])
    Nt = np.array([s.N for s in sev], dtype=float)
    bounds = [g.start_idx for g in gates[1:] if g.start_idx >= start]

    fig, ax = plt.subplots(5, 1, figsize=(18, 14), sharex=True,
                           gridspec_kw={"height_ratios": [3, 1.4, 1.2, 1.2, 1.2]})
    x = idx[start:]
    ax[0].plot(x, close.values[start:], color="black", lw=1.0)
    ax[0].set_yscale("log")
    for b in bounds:
        ax[0].axvline(b, color="tab:red", lw=0.5, alpha=0.6)
    qs = np.where(Nt[start:] > 0)[0] + start
    if len(qs):
        ax[0].scatter(qs, close.values[qs], s=6, color="tab:blue", zorder=3, label="N_t=1 (negative space)")
        ax[0].legend(loc="upper left", fontsize=8)
    ax[0].set_title(f"{symbol}  tau_D={tau}  gates in view={len(bounds)}  "
                    f"({dates[start].date()} → {dates[-1].date()})  red = gate boundary", fontsize=11)
    ax[1].step(x, R[start:], where="post", color="tab:purple", lw=1, label="R_k")
    ax[1].step(x, URF[start:], where="post", color="tab:green", lw=1, label="URF_k (gated)")
    ax[1].set_ylim(-0.02, 1.02); ax[1].legend(loc="upper left", fontsize=8)
    ax[2].step(x, D[start:], where="post", color="tab:blue", lw=1.2, label="D_k")
    rv = np.where(RV[start:] > 0)[0] + start
    ax[2].scatter(rv, np.zeros(len(rv)), marker="x", color="tab:red", s=30, label="R_rev_k=1")
    ax[2].step(x, P[start:] / 2.0, where="post", color="tab:gray", lw=0.8, alpha=0.7, label="P_k/2")
    ax[2].set_ylim(-1.2, 1.2); ax[2].legend(loc="upper left", fontsize=8)
    ax[3].step(x, M[start:], where="post", color="tab:orange", lw=1, label="M_k")
    ax[3].step(x, B[start:], where="post", color="tab:brown", lw=1, label="B_k")
    ax[3].axhline(0, color="k", lw=0.4); ax[3].legend(loc="upper left", fontsize=8)
    ax[4].step(x, U[start:], where="post", color="tab:red", lw=1, label="U*_k")
    ax[4].step(x, C[start:] / 3.0, where="post", color="tab:cyan", lw=1, label="C_k/3")
    ax[4].set_ylim(-0.02, 1.05); ax[4].legend(loc="upper left", fontsize=8)
    ticks = np.linspace(start, n - 1, 8).astype(int)
    ax[4].set_xticks(ticks); ax[4].set_xticklabels([str(dates[t].date()) for t in ticks], rotation=0, fontsize=8)
    for a in ax:
        a.grid(alpha=0.2)
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{symbol}_tau{tau}.png"
    fig.tight_layout(); fig.savefig(path, dpi=80); plt.close(fig)
    return path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("symbols", nargs="+")
    ap.add_argument("--tau", type=float, default=0.10)
    ap.add_argument("--years", type=float, default=3.0)
    args = ap.parse_args()
    store = pd.read_parquet(ROOT / "ch4_live_store.parquet", columns=["Date", "Symbol", "Close"])
    for s in args.symbols:
        g = store[store.Symbol == s].sort_values("Date")
        if g.empty:
            print(f"{s}: not in store"); continue
        close = pd.Series(g.Close.values.astype(float), index=pd.to_datetime(g.Date.values))
        print(draw(s, close, args.tau, args.years))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
