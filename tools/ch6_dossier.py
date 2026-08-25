"""
ch6_dossier.py — one life, one dossier, for a reading
======================================================

Built 2026-08-20 on the last session's proven form (doss9f3): the
whole life coarse from the daily lanes, the recent month fine at five
readings per session, the kernel's layers beside price — everything a
reader needs to name the mechanism, nothing else. Output is plain
text, ~8KB, deterministic.

Usage: python tools/ch6_dossier.py SYM [out.txt]
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DAY_LANES = os.path.join(ROOT, "artifacts", "ch4_uf", "population_lanes")
FINE_LANES = os.environ.get(
    "CH6_FINE_LANES",
    os.path.join(ROOT, "artifacts", "ch6_harvest", "year_lanes"))


def build(symbol: str) -> str:
    out = []
    d = pd.read_parquet(os.path.join(DAY_LANES, f"{symbol}.parquet"))
    f = pd.read_parquet(os.path.join(FINE_LANES, f"{symbol}.parquet"))
    c = d["close"].to_numpy(float)
    out.append(f"=== {symbol} dossier — as of close {d['date'].iloc[-1]} ===")
    out.append(f"life: {d['date'].iloc[0]} .. {d['date'].iloc[-1]}  "
               f"({len(d):,} sessions)  close {c[-1]:.2f}  "
               f"life-peak {c.max():.2f}  peak/now {c.max()/max(c[-1],1e-9):.1f}x")
    ext_total = int(d["extinction"].sum())
    out.append(f"channel deaths in life: {ext_total}  "
               f"({ext_total/max(0.1,len(d)/252):.0f}/yr)")
    out.append("")
    out.append("--- WHOLE LIFE (daily lanes, every 15th session) ---")
    out.append(f"{'date':>12} {'close':>9} {'S_UF':>6} {'URF':>6} {'B':>7} "
               f"{'U*':>6} {'regime':>13} {'gates':>6} {'dies':>5}")
    step = max(1, len(d) // 60)
    for i in range(0, len(d), step):
        r = d.iloc[i]
        dies = int(d["extinction"].iloc[max(0, i - step + 1):i + 1].sum())
        out.append(f"{r['date']:>12} {r['close']:>9.2f} {r['S_UF']:>6.3f} "
                   f"{r['URF']:>6.3f} {r['B_k']:>7.3f} {r['U_star_k']:>6.3f} "
                   f"{r['regime']:>13} {int(r['gate_count']):>6} {dies:>5}")
    out.append("")
    sessions = sorted(set(f["date"]))[-22:]
    ff = f[f["date"].isin(sessions)]
    out.append("--- LAST 22 SESSIONS (5 readings/session) — session closes ---")
    out.append(f"{'date':>12} {'close':>9} {'S_UF':>6} {'URF':>6} {'U*':>6} "
               f"{'deaths':>6} {'ign':>4} {'rev':>4} {'D-':>4} {'D+':>4}")
    for s in sessions:
        g = ff[ff["date"] == s]
        r = g.iloc[-1]
        Dv = g["D_k"].to_numpy(float)
        out.append(f"{s:>12} {r['close']:>9.2f} {r['S_UF']:>6.3f} "
                   f"{r['URF']:>6.3f} {r['U_star_k']:>6.3f} "
                   f"{int(g['extinction'].sum()):>6} {int(g['ignition'].sum()):>4} "
                   f"{int(g['Rev_k'].sum()):>4} {int((Dv<0).sum()):>4} "
                   f"{int((Dv>0).sum()):>4}")
    out.append("")
    out.append("--- FINAL 3 SESSIONS, EVERY READING ---")
    out.append(f"{'date':>12} {'time':>6} {'close':>9} {'URF':>6} {'D':>3} "
               f"{'Rev':>4} {'die':>4} {'ign':>4} {'F_n':>7} {'Rres':>7}")
    for _, r in f[f["date"].isin(sessions[-3:])].iterrows():
        out.append(f"{r['date']:>12} {r['time']:>6} {r['close']:>9.2f} "
                   f"{r['URF']:>6.3f} {int(r['D_k']):>3} {int(r['Rev_k']):>4} "
                   f"{int(r['extinction']):>4} {int(r['ignition']):>4} "
                   f"{r['F_n']:>7.3f} {r['R_res']:>7.3f}")
    return "\n".join(out)


if __name__ == "__main__":
    text = build(sys.argv[1].upper())
    if len(sys.argv) > 2:
        open(sys.argv[2], "w").write(text)
    print(text[:600])
    print(f"... [{len(text)} chars]")
