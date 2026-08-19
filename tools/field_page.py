"""
field_page.py — draw any life from the population reading layer
================================================================

The last session's 3D lane instrument (AMD page renderer, reused as
found), fed from artifacts/ch4_uf/population_lanes/. Column recipes
validated against the AMD page's own shipped data 2026-08-19
(14/15 exact; the repaired-carry lane is a labeled reconstruction:
channel-alive share over 256 readings, closest verified match).
Resolution set per life (0.5/99.5 percentile ranges per lane), gate
count drawn as DENSITY (gates opened per 64 readings), M on an
asymmetric robust range — per Joseph 2026-08-19: play with the
resolutions; the coarse view already shows structure.

Usage:  python tools/field_page.py SYM [entry_date] [out.html]
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LANES = os.path.join(ROOT, "artifacts", "ch4_uf", "population_lanes")
TPL = os.path.join(ROOT, "artifacts", "ch4_uf", "field_page_template.html")


def build(sym: str, entry_date: str | None = None,
          out: str | None = None) -> str:
    m = pd.read_parquet(os.path.join(LANES, f"{sym}.parquet"))
    urf = m["URF"].to_numpy()
    D = m["D_k"].to_numpy(dtype=float)
    M = np.zeros(len(urf))
    M[2:] = urf[2:] - 2 * urf[1:-1] + urf[:-2]
    P = np.abs(np.diff(D, prepend=0.0))
    A256 = np.array([np.mean(urf[max(0, i - 255):i + 1] > 0)
                     for i in range(len(urf))])
    L64, C64 = [], []
    g = m["gate_count"].to_numpy()
    for i in range(len(D)):
        w = D[max(0, i - 63):i + 1]
        nz = w[w != 0]
        L64.append(abs(nz.sum()) / max(1, len(nz)))
        j = max(0, i - 63)
        C64.append(int(g[i] - g[j]))
    rows = []
    for i in range(len(m)):
        r = m.iloc[i]
        rows.append([r["date"][2:], "16:00", round(float(r["close"]), 4),
                     int(r["D_k"]), round(float(M[i]), 4), int(r["Rev_k"]),
                     round(float(r["U_star_k"]), 4), int(C64[i]), int(P[i]),
                     round(float(r["B_k"]), 4), round(float(r["S_UF"]), 4),
                     round(float(urf[i]), 4), int(r["ignition"]),
                     int(r["extinction"]), round(float(A256[i]), 4),
                     round(float(L64[i]), 4)])
    px = m["close"].to_numpy()

    def rng(a, pad=0.06):
        lo = float(np.nanpercentile(a, 0.5))
        hi = float(np.nanpercentile(a, 99.5))
        span = max(hi - lo, 1e-6)
        return round(lo - pad * span, 4), round(hi + pad * span, 4)

    plo, phi = np.log(px.min()) - 0.05, np.log(px.max()) + 0.05
    ulo, uhi = rng(m["U_star_k"])
    slo, shi = rng(m["S_UF"])
    rlo, rhi = rng(urf)
    mlo, mhi = rng(M, pad=0.1)
    clo, chi = 0, max(4, int(np.percentile(C64, 99.5) * 1.1))
    F = (f'const F=[{{n:"price",k:2,lo:{plo:.3f},hi:{phi:.3f},log:true}},\n'
         f' {{n:"alive256*",k:14,lo:0.4,hi:1.02}},'
         f'{{n:"L64",k:15,lo:-0.05,hi:1.05}},{{n:"U*",k:6,lo:{ulo},hi:{uhi}}},\n'
         f' {{n:"S_UF",k:10,lo:{slo},hi:{shi}}},'
         f'{{n:"R_UF",k:11,lo:{rlo},hi:{rhi}}},\n'
         f' {{n:"M",k:4,lo:{mlo},hi:{mhi}}},{{n:"P",k:8,lo:-0.2,hi:2.2}},\n'
         f' {{n:"D",k:3,lo:-1.15,hi:1.15}},'
         f'{{n:"C64",k:7,lo:{clo},hi:{chi}}},\n'
         f' {{n:"Rev",k:5,lo:-0.15,hi:1.15}}];')
    h = open(TPL).read()
    i0 = h.find("const DATA=")
    i1 = h.find("];", i0) + 2
    h = (h[:i0] + "const DATA=" + json.dumps(rows, separators=(",", ":"))
         + ";\n" + h[i1:])
    i0 = h.find("const F=")
    i1 = h.find("];", i0) + 2
    h = h[:i0] + F + h[i1:]
    mark = entry_date[2:] if entry_date else "no-such-date"
    h = h.replace('r[0]==="26-08-17"', f'r[0]==="{mark}"')
    h = h.replace("<title>FDMT L4 Field</title>", f"<title>{sym} L4 Field</title>")
    i0 = h.find("<h1>")
    i1 = h.find("</h1>") + 5
    h = (h[:i0] + f"<h1>{sym} — all nine L4 outputs, the whole stored life, "
         "one reading per close</h1>" + h[i1:])
    i0 = h.find('<div class="sub">')
    i1 = h.find("</div>", i0) + 6
    first, last = m["date"].iloc[0], m["date"].iloc[-1]
    note = (f" The dashed wall marks {entry_date}." if entry_date else "")
    h = h[:i0] + (
        f'<div class="sub">Every reading of {sym}\'s stored life — {first} to '
        f'{last}, {len(rows):,} daily closes through the fixed kernel, drawn '
        f'from the population reading layer.{note} Drag rotates &#183; wheel '
        f'zooms days &#183; double-click resets &#183; hover reads out every '
        f'value. C64 is gate DENSITY (gates opened per 64 readings); '
        f'alive256* is a labeled reconstruction (channel-alive share, 256 '
        f'readings); every other lane reproduces the validated recipes '
        f'exactly.</div>') + h[i1:]
    out = out or os.path.join(ROOT, "artifacts", "ch4_uf",
                              f"field_{sym.lower()}.html")
    open(out, "w").write(h)
    return out


if __name__ == "__main__":
    sym = sys.argv[1].upper()
    entry = sys.argv[2] if len(sys.argv) > 2 else None
    dest = sys.argv[3] if len(sys.argv) > 3 else None
    print("written:", build(sym, entry, dest))
