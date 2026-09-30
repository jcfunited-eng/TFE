"""Print a stock's tuples over time — one row per gate, the production
chain's own values, nothing averaged. Read it; do not score it.

Resolution (Joe, 2026-09-30: "the resolution was daily ... there is a
'resolution' consideration for D_k for tickers at market cap and price
points that alter what volatility looks like — the Smooth Glass conundrum").
Bars are daily. One fixed tau_D sees a large, high-priced name as smooth
glass (SNY: 0.37 boundaries a year at 0.20) and a small, low-priced one as
a storm (LAC: 19.5 a year). HIS: the resolution must be set per ticker by
its size and price. MINE: the setting — tau_D for a ticker is `c` times
that ticker's own typical daily deviation D(t) = |dF| + sigma + kappa (the
median over its life). c defaults to 3.77, which puts MTD at 0.10, the
resolution at which its phases were first read. The kernel is unmodified;
tau_D is set in this process only.

Usage: python3 tools/ch2_tuples_over_time.py SYMBOL [--c 3.77 | --tau 0.10] --years 3
"""
import argparse, sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from tools.ch2_draw_life import chain
import uf_core.config as cfg
from uf_core.layer0 import compute_sev_series
from uf_core.layer1 import compute_deviation

C_DEFAULT = 3.77   # 0.10 / MTD's median daily deviation 0.0265


def own_resolution(close: np.ndarray, c: float = C_DEFAULT) -> tuple[float, float]:
    """tau_D for this ticker = c x its own typical daily deviation (life median)."""
    D = compute_deviation(compute_sev_series(pd.DataFrame({"Close": close})))
    typical = float(np.median(D[1:]))
    return c * typical, typical


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("symbol"); ap.add_argument("--tau", type=float, default=None)
    ap.add_argument("--c", type=float, default=C_DEFAULT); ap.add_argument("--years", type=float, default=3.0)
    a = ap.parse_args()
    store = pd.read_parquet(ROOT / "ch4_live_store.parquet", columns=["Date", "Symbol", "Close"])
    g = store[store.Symbol == a.symbol].sort_values("Date")
    close = pd.Series(g.Close.values.astype(float), index=pd.to_datetime(g.Date.values))
    if a.tau is None:
        tau, typical = own_resolution(close.values, a.c)
        how = f"own resolution: {a.c} x typical day {typical:.4f}"
    else:
        tau, how = a.tau, "fixed"
    cfg.KERNEL_THRESHOLDS.tau_D = float(tau)
    sev, gates, interps, res, dsf = chain(close)
    n = len(close); start = max(0, n - int(a.years * 252))
    yrs = (close.index[-1] - close.index[0]).days / 365.25
    print(f"{a.symbol}  tau_D={tau:.4f} ({how})  {len(gates)} gates in {yrs:.1f} y = {len(gates)/yrs:.1f}/yr; showing those ending after {close.index[start].date()}")
    print(f"{'k':>3} {'start':10} {'end':10} {'len':>4} {'px_in':>8} {'px_out':>8} {'chg%':>7} {'next%':>7} | {'D':>2} {'M':>6} {'Rev':>3} {'U*':>5} {'C':>2} {'P':>2} {'B':>5} | {'R':>5} {'URF':>5} {'g':>1} {'Hy':>2} {'IAS':>3} {'U':>5} {'w':>5} {'psi':>5} {'S':>5} regime")
    for k, (gt, it, rs, d) in enumerate(zip(gates, interps, res, dsf)):
        if gt.end_idx < start: continue
        s, e = gt.start_idx, gt.end_idx
        nxt = gates[k + 1] if k + 1 < len(gates) else None
        chg = 100 * (close.iloc[e] / close.iloc[s] - 1)
        nxtc = 100 * (close.iloc[nxt.end_idx] / close.iloc[nxt.start_idx] - 1) if nxt else float('nan')
        print(f"{k:>3} {str(close.index[s].date()):10} {str(close.index[e].date()):10} {e-s+1:>4} {close.iloc[s]:>8.2f} {close.iloc[e]:>8.2f} {chg:>+7.1f} {nxtc:>+7.1f} | {int(d.D_k):>+2} {d.M_k:>+6.2f} {int(d.R_rev_k):>3} {d.U_star_k:>5.2f} {int(d.C_k):>2} {int(d.P_k):>2} {d.B_k:>+5.2f} | {rs.R_k:>5.2f} {rs.URF_k:>5.2f} {rs.g_k:>1} {rs.Hyst_k:>2} {rs.IAS_k:>3} {rs.U_k:>5.2f} {it.w_k:>5.2f} {it.psi_k:>5.2f} {it.S_k:>5.2f} {it.regime}")
