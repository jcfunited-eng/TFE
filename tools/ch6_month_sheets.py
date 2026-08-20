"""
ch4_month_sheets.py — contact sheets of the month scan, for eyes
=================================================================

Twelve lives per sheet, each life a compact column of lanes over the
last 22 sessions at 5 readings per session. Lane order follows
Joseph's ratified order compressed to the six that carry the decline
call at this size (price at the BOTTOM per his order, then upward:
U*, S_UF, R_UF, D push, deaths); the full eleven-lane order lives on
the per-stock 3D pages. For pattern-reading by eye, not decoration:
no smoothing, no color meaning beyond up/down, session gridlines.

Usage: python tools/ch4_month_sheets.py [out_dir]
"""

from __future__ import annotations

import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LANES = os.path.join(ROOT, "artifacts", "ch6_harvest", "month_lanes")
PER_SHEET = 12


def draw_life(ax_col, sym: str, lf: pd.DataFrame) -> None:
    n = len(lf)
    x = np.arange(n)
    dates = lf["date"].to_numpy()
    bounds = [i for i in range(1, n) if dates[i] != dates[i - 1]]
    c = lf["close"].to_numpy(dtype=float)
    ret = 100 * (c[-1] / c[0] - 1)
    panels = [
        ("deaths", None), ("D", None), ("R_UF", lf["URF"]),
        ("S_UF", lf["S_UF"]), ("U*", lf["U_star_k"]), ("price", None),
    ]
    for ax, (name, series) in zip(ax_col, panels):
        for b in bounds:
            ax.axvline(b, color="0.92", lw=0.4, zorder=0)
        if name == "price":
            ax.plot(x, c, lw=0.9, color="black")
            ax.set_ylabel(f"{sym}\n{ret:+.0f}%", rotation=0, ha="right",
                          va="center", fontsize=7,
                          color=("darkred" if ret < 0 else "darkgreen"))
        elif name == "D":
            d = lf["D_k"].to_numpy(dtype=float)
            ax.vlines(x[d > 0], 0, 1, color="seagreen", lw=0.6)
            ax.vlines(x[d < 0], -1, 0, color="firebrick", lw=0.6)
            ax.set_ylim(-1.2, 1.2)
        elif name == "deaths":
            e = lf["extinction"].to_numpy(dtype=float)
            ig = lf["ignition"].to_numpy(dtype=float)
            ax.vlines(x[e > 0], 0, 1, color="firebrick", lw=0.8)
            ax.vlines(x[ig > 0], -1, 0, color="seagreen", lw=0.8)
            ax.set_ylim(-1.2, 1.2)
        else:
            ax.plot(x, series.to_numpy(dtype=float), lw=0.7, color="0.2")
        ax.set_xticks([])
        ax.set_yticks([])
        for s in ax.spines.values():
            s.set_visible(False)
    ax_col[0].set_title(sym, fontsize=7, pad=1)


def main() -> None:
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        ROOT, "artifacts", "ch6_harvest", "month_sheets")
    os.makedirs(out_dir, exist_ok=True)
    files = sorted(f for f in os.listdir(LANES) if f.endswith(".parquet"))
    sheets = [files[i:i + PER_SHEET] for i in range(0, len(files), PER_SHEET)]
    for si, group in enumerate(sheets):
        fig, axes = plt.subplots(6, len(group), figsize=(len(group) * 1.9, 7),
                                 squeeze=False)
        for col, fname in enumerate(group):
            lf = pd.read_parquet(os.path.join(LANES, fname))
            draw_life([axes[r][col] for r in range(6)], fname[:-8], lf)
        for col in range(len(group), axes.shape[1]):
            for r in range(6):
                axes[r][col].axis("off")
        rows_lab = ["deaths", "push D", "R_UF", "S_UF", "U*", "price"]
        for r, lab in enumerate(rows_lab):
            axes[r][0].set_ylabel(lab, fontsize=6, rotation=90)
        fig.suptitle(f"month scan sheet {si + 1}/{len(sheets)} — 22 sessions,"
                     " 5 readings/session", fontsize=8)
        fig.tight_layout(pad=0.4)
        fig.savefig(os.path.join(out_dir, f"sheet_{si + 1:03d}.png"), dpi=110)
        plt.close(fig)
        if (si + 1) % 50 == 0:
            print(f"[{si + 1}/{len(sheets)}]", flush=True)
    print(f"DONE {len(sheets)} sheets -> {out_dir}", flush=True)


if __name__ == "__main__":
    main()
