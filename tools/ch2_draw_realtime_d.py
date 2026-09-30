"""Overlay the kernel's day-by-day direction (each day's own prefix) on the
final-values picture, for one stock. Seeing whether the daily reading
agrees with the finished stretch, and how many bars it takes to settle.
Usage: python3 tools/ch2_draw_realtime_d.py SYMBOL --tau 0.10 --years 3
"""
import argparse, sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from tools.ch2_draw_life import chain
import uf_core.config as cfg

ap = argparse.ArgumentParser(); ap.add_argument("symbol"); ap.add_argument("--tau", type=float, default=0.10); ap.add_argument("--years", type=float, default=3.0)
a = ap.parse_args()
cfg.KERNEL_THRESHOLDS.tau_D = a.tau
store = pd.read_parquet(ROOT / "ch4_live_store.parquet", columns=["Date", "Symbol", "Close"])
g = store[store.Symbol == a.symbol].sort_values("Date")
close = pd.Series(g.Close.values.astype(float), index=pd.to_datetime(g.Date.values))
n = len(close); start = max(0, n - int(a.years * 252))
sev, gates, interps, res, dsf = chain(close)
final = np.full(n, np.nan)
for gt, d in zip(gates, dsf): final[gt.start_idx: gt.end_idx + 1] = d.D_k
rt = np.full(n, np.nan)
for i in range(start, n):
    _, _, _, _, dd = chain(close.iloc[: i + 1])
    rt[i] = dd[-1].D_k if dd else np.nan
agree = np.nanmean(rt[start:] == final[start:])
# settle time: for each gate starting in view, first bar j>=start_idx where rt[j:] == final for the rest of the gate
settle = []
for gt in gates:
    if gt.start_idx < start: continue
    seg_f = final[gt.start_idx: gt.end_idx + 1]; seg_r = rt[gt.start_idx: gt.end_idx + 1]
    j = len(seg_r)
    for k in range(len(seg_r)):
        if np.all(seg_r[k:] == seg_f[k:]): j = k; break
    settle.append((j, gt.end_idx - gt.start_idx + 1))
print(f"{a.symbol} tau {a.tau}: daily reading equals final value on {100*agree:.0f}% of bars; gates in view {len(settle)}")
print("bars to settle / gate length:", " ".join(f"{s}/{L}" for s, L in settle))
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
fig, ax = plt.subplots(2, 1, figsize=(18, 7), sharex=True, gridspec_kw={"height_ratios": [3, 1.3]})
x = np.arange(start, n); ax[0].plot(x, close.values[start:], color="black", lw=1); ax[0].set_yscale("log")
for gt in gates[1:]:
    if gt.start_idx >= start: ax[0].axvline(gt.start_idx, color="tab:red", lw=0.5, alpha=0.6)
up = rt[start:] == 1; dn = rt[start:] == -1
ax[0].fill_between(x, close.values[start:].min(), close.values[start:].max(), where=up, color="tab:green", alpha=0.10, label="daily D_k = +1")
ax[0].fill_between(x, close.values[start:].min(), close.values[start:].max(), where=dn, color="tab:red", alpha=0.10, label="daily D_k = -1")
ax[0].legend(loc="upper left", fontsize=8); ax[0].set_title(f"{a.symbol} tau_D={a.tau}: shading = the kernel's direction read on each day's own history; red lines = gate boundaries")
ax[1].step(x, final[start:], where="post", color="tab:blue", lw=1.5, label="D_k final (whole history)")
ax[1].step(x, rt[start:] - 0.05, where="post", color="tab:orange", lw=1, label="D_k as read each day")
ax[1].set_ylim(-1.3, 1.3); ax[1].legend(loc="upper left", fontsize=8)
ticks = np.linspace(start, n - 1, 8).astype(int); ax[1].set_xticks(ticks); ax[1].set_xticklabels([str(close.index[t].date()) for t in ticks], fontsize=8)
out = ROOT / "artifacts" / "ch2_life" / f"{a.symbol}_tau{a.tau}_realtime.png"; fig.tight_layout(); fig.savefig(out, dpi=80); print(out)
