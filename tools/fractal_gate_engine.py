"""
fractal_gate_engine.py
=======================

NON-CANONICAL — application of the recovered Fractal-Gate framework
(docs/recovered_lineage/) with the declared completions
(docs/FRACTAL_GATE_COMPLETION_NONCANONICAL.md) to the side kernel's
real field. Kernel untouched; this consumes its retained structures.

PART 1 — fit-free tests of the framework's own predictions on the
real field (T1 relaxation, T2 realignment, T3 meadow linkage,
T4 vertex linkage). Closed bars only: the current (possibly forming)
bar is excluded.

PART 2 — the lineage simulation: gates with interpretive angles,
conservative cluster coupling, mosaic interference, Kuramoto
motivation — driven by the completed four-axis input
(S = share vector, T = exact Δt, V = swept volume, R = attention
bursts from traded dollar volume). Emergence check, report-only.

Usage: python tools/fractal_gate_engine.py
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from fractions import Fraction

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.vtvr_structure_search import build_field, _mean  # noqa: E402
from tools.run_market_vtvr_capture import _headers  # noqa: E402
import tools.vtvr_leadlag_walkforward as wf  # noqa: E402

HORIZONS = (20, 60)
REALIGN_K = (5, 20)
RELAX_K = (1, 5, 20)

# H4 pinned simulation parameters
D_STATE = 8
CLUSTER_SIZE = 10
ALPHA = 0.1
BETA = 1.0
ETA = 0.05
SPECTRAL = 0.9


def _rng(tag: str) -> np.random.Generator:
    seed = int.from_bytes(hashlib.sha256(tag.encode()).digest()[:8], "big")
    return np.random.default_rng(seed)


def fetch_dollar_volume(symbols, start_iso, limit=1700):
    """Traded dollar volume per symbol per date (the R axis source)."""
    out = {}
    for s in symbols:
        url = (f"https://data.alpaca.markets/v2/stocks/{s}/bars"
               f"?timeframe=1Day&limit={limit}&feed=iex&adjustment=split"
               f"&start={start_iso}")
        req = urllib.request.Request(url, headers=_headers())
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                payload = json.loads(r.read())
        except Exception:
            continue
        for b in payload.get("bars") or []:
            out.setdefault(b["t"][:10], {})[s] = float(b["c"]) * float(b["v"])
    return out


def attention_series(dv, dates, symbols, win=20):
    """H3: r_i(t) = dollar_vol / trailing-20 median, per vertex."""
    n = len(symbols)
    r = np.ones((len(dates), n))
    hist = {s: [] for s in symbols}
    for k, d in enumerate(dates):
        row = dv.get(d, {})
        for i, s in enumerate(symbols):
            v = row.get(s)
            if v is None:
                continue
            h = hist[s]
            if len(h) >= 5:
                med = float(np.median(h[-win:]))
                if med > 0:
                    r[k, i] = v / med
            h.append(v)
    return r


def main():
    symbols, common, field, px_frac = build_field()  # cohort A
    px = np.array([[float(v) for v in row] for row in px_frac])
    m_total, n = len(common), len(symbols)

    # Closed bars only: drop the last bar if it is today's (possibly forming)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if common[-1][:10] == today:
        m_total -= 1
        print(f"Excluded forming bar {today}; using {m_total} closed bars")

    dx = np.array([[float(v) for v in row] for row in field.dxhat])[:m_total]
    vol = np.array([[float(v) for v in row] for row in field.volume])[:m_total]
    xhat = np.array([[float(v) for v in row] for row in field.xhat])[:m_total]
    dates = [d[:10] for d in common[:m_total]]

    # ── H1/H2: phases, coherence, dissonance ────────────────────────────
    phi = np.zeros((m_total, n))
    for t in range(2, m_total):
        phi[t] = np.arctan2(dx[t], dx[t - 1])
    Z = np.exp(1j * phi[2:]).mean(axis=1)
    omega = np.abs(Z)                       # field coherence, t=2..
    theta_m = np.angle(Z)
    diss = 1 - np.cos(phi[2:] - theta_m[:, None])   # vertex dissonance
    T0 = 2  # offset of omega/diss arrays vs bar index

    print("=" * 68)
    print("PART 1 — the framework's own predictions on the real field")
    print("=" * 68)
    print(f"Field: {n} vertices, {m_total} closed bars "
          f"({dates[0]} .. {dates[-1]})")
    print(f"Field coherence Ω: mean {omega.mean():.3f} | "
          f"p10 {np.percentile(omega, 10):.3f} | "
          f"p90 {np.percentile(omega, 90):.3f}")
    print()

    # T1 — relaxation (Kuramoto attractor prediction: negative corr)
    print("T1 RELAXATION — corr(Ω(t), Ω(t+k)−Ω(t)):")
    for k in RELAX_K:
        a = omega[:-k]
        b = omega[k:] - omega[:-k]
        c = float(np.corrcoef(a, b)[0, 1])
        print(f"  k={k:<3} corr = {c:+.3f}  "
              f"({'relaxes (as predicted)' if c < -0.1 else 'weak/none'})")
    print()

    # T2 — realignment of dissonant vertices (source's own law)
    print("T2 REALIGNMENT — Δdissonance next k bars, top vs bottom tercile:")
    for k in REALIGN_K:
        top_ch, bot_ch = [], []
        for t in range(len(diss) - k):
            row = diss[t]
            q1, q2 = np.percentile(row, [33.3, 66.7])
            top = row >= q2
            bot = row <= q1
            dch = diss[t + k] - row
            top_ch.append(dch[top].mean())
            bot_ch.append(dch[bot].mean())
        print(f"  k={k:<3} dissonant Δ = {np.mean(top_ch):+.4f} | "
              f"aligned Δ = {np.mean(bot_ch):+.4f}  "
              f"({'realigns (as predicted)' if np.mean(top_ch) < np.mean(bot_ch) else 'contradicted'})")
    print()

    # Forward returns for T3/T4
    fwd = {}
    for h in HORIZONS:
        f = np.full((m_total, n), np.nan)
        f[:m_total - h] = (px[h:m_total] - px[:m_total - h]) / px[:m_total - h]
        fwd[h] = f

    # T3 — meadow linkage: forward outcomes by field-coherence tercile
    print("T3 MEADOW LINKAGE — forward universe outcome by Ω tercile:")
    o_terc = np.percentile(omega, [33.3, 66.7])
    for h in HORIZONS:
        print(f"  +{h} bars:")
        for name, mask in (
            ("Ω low ", omega <= o_terc[0]),
            ("Ω mid ", (omega > o_terc[0]) & (omega <= o_terc[1])),
            ("Ω high", omega > o_terc[1]),
        ):
            rows = []
            for t in np.where(mask)[0]:
                bar = t + T0
                if bar < m_total - h:
                    rows.extend(fwd[h][bar])
            rows = [r for r in rows if not math.isnan(r)]
            wr = _mean([1.0 if r > 0 else 0.0 for r in rows]) * 100
            print(f"    {name}: N={len(rows):<6} WR {wr:5.1f}%  "
                  f"mean {100 * _mean(rows):+6.2f}%")
    print()

    # T4 — vertex linkage: forward outcomes by dissonance tercile
    print("T4 VERTEX LINKAGE — forward outcome by vertex dissonance tercile:")
    for h in HORIZONS:
        bands = {"low ": [], "mid ": [], "high": []}
        for t in range(len(diss)):
            bar = t + T0
            if bar >= m_total - h:
                break
            row = diss[t]
            q1, q2 = np.percentile(row, [33.3, 66.7])
            for i in range(n):
                r = fwd[h][bar, i]
                if math.isnan(r):
                    continue
                key = "low " if row[i] <= q1 else ("high" if row[i] >= q2 else "mid ")
                bands[key].append(r)
        print(f"  +{h} bars:")
        for name, rows in bands.items():
            wr = _mean([1.0 if r > 0 else 0.0 for r in rows]) * 100
            print(f"    dissonance {name}: N={len(rows):<6} WR {wr:5.1f}%  "
                  f"mean {100 * _mean(rows):+6.2f}%")
    print()

    # ── PART 2 — lineage simulation on the four-axis input ──────────────
    print("=" * 68)
    print("PART 2 — gate/cluster/mosaic simulation (pinned parameters)")
    print("=" * 68)
    start_iso = (datetime.now(timezone.utc) - timedelta(days=2600)) \
        .strftime("%Y-%m-%dT%H:%M:%SZ")
    dv = fetch_dollar_volume(symbols, start_iso)
    att = attention_series(dv, dates, symbols)
    print(f"Attention axis built: mean burst {att.mean():.2f}, "
          f"p99 {np.percentile(att, 99):.2f}")

    dts = np.array([float(t) for t in field.dts])[:m_total]
    dts_n = dts / max(dts.max(), 1.0)

    clusters = [list(range(c, min(c + CLUSTER_SIZE, n)))
                for c in range(0, n, CLUSTER_SIZE)]
    W = []
    for i in range(n):
        g = _rng(f"W:{symbols[i]}")
        M = g.standard_normal((D_STATE, D_STATE))
        Q, _ = np.linalg.qr(M)
        W.append(Q * SPECTRAL)
    P = _rng("P").standard_normal((4, D_STATE)) * 0.5
    Pb = _rng("Pb").standard_normal((2, D_STATE)) * 0.5
    theta = _rng("theta").uniform(0, 2 * np.pi, n)
    y = np.zeros((n, D_STATE))

    omega_m_series = []
    theta_hist = [theta.copy()]
    for t in range(2, m_total):
        X = np.stack([
            xhat[t],                    # S
            np.full(n, dts_n[t]),       # T
            vol[t] / (vol[t].max() if vol[t].max() > 0 else 1.0),  # V
            np.clip(att[t], 0, 10) / 10,                            # R
        ], axis=1)                       # n×4
        b = BETA * np.stack([np.cos(theta), np.sin(theta)], axis=1) @ Pb
        y_new = np.zeros_like(y)
        for ci, cl in enumerate(clusters):
            k = len(cl)
            ysum = y[cl].sum(axis=0)
            for i in cl:
                coupling = ALPHA / k * (ysum - k * y[i])   # conservative
                y_new[i] = np.tanh(W[i] @ y[i] + X[i] @ P + b[i] + coupling)
        y = y_new

        # ψ_C per cluster (H5) and mosaic
        psis = []
        for cl in clusters:
            yc = y[cl]
            ybar = yc.mean(axis=0)
            nrm = np.linalg.norm(yc, axis=1) * np.linalg.norm(ybar)
            ok = nrm > 0
            om_c = float(np.mean((yc[ok] @ ybar) / nrm[ok])) if ok.any() else 0.0
            th_c = math.atan2(ybar[1], ybar[0])
            psis.append(om_c * np.exp(1j * th_c))
        psi_m = np.mean(psis)
        omega_m_series.append(abs(psi_m))
        theta_big = np.angle(psi_m)
        theta = theta - ETA * np.sin(theta - theta_big)
        if t % 200 == 0:
            theta_hist.append(theta.copy())

    omega_m = np.array(omega_m_series)
    lim = min(len(omega_m), len(omega))
    c = float(np.corrcoef(omega_m[:lim], omega[:lim])[0, 1])
    drift = float(np.mean(np.abs(theta - theta_hist[0])))
    print(f"Mosaic coherence Ω_M: mean {omega_m.mean():.3f} "
          f"(range {omega_m.min():.3f}..{omega_m.max():.3f})")
    print(f"Emergence check: corr(Ω_M, field Ω) = {c:+.3f}")
    print(f"Angle drift (mean |θ_final − θ_init|): {drift:.3f} rad — "
          f"the gates {'reoriented' if drift > 0.5 else 'barely moved'}")
    print()
    print("All numbers above are raw; nothing was selected or tuned.")


if __name__ == "__main__":
    main()
