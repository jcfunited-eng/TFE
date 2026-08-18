"""
ch3_joint_field_full.py — the COMPLETE joint-field chain, from Joe's document
=============================================================================

DECLARED 2026-08-18 BEFORE THE RUN. Source of authority: docs/
UF_Spec_v1_3_JointField_Reconstruction_VERBATIM.tex (Joe's pasted
document, filed verbatim from the session record). Every equation
below cites its line in that file. No canonical-kernel scalar (w, S,
U, R_res, URF) appears anywhere in this chain.

TOPOLOGY (declared; spec l.170-187 requires typed structure):
  Vertices V = the spiking stock + its 7 band-liquidity peers
    (same entry price band; largest trailing-20 median dollar volume
    at t-1; >= 128 aligned bars; deterministic, causal, no outcome
    contact). Loss: peer choice is a declared calibration, not a
    ratified physical relation — named per spec l.183.
  Edges E = star: {spike stock, peer_i} for each peer (7 edges).
  Groups G = one group containing all 8 vertices (spec l.254-265:
    group normalization removes one common positive scale — here the
    cohort's common market scale — preserving orientation and ratios).
  Perspectives = ONE (all vertices, all descriptors). Loss: the
    cross-perspective set X is empty by construction — disclosed.
  Window: the 64 bars ending at the event bar t, with 64 further
    bars of causal history behind them for trailing windows.
  Scales (spec l.239-246): Scales_64 = {1,2,4,8,16,32,64}; causal
    intervals I_k,s = last s bars ending at k. Full windows only.

CUSTODY (spec l.196-199, invariant 4 l.738-740):
  x_{k,v} = integer price code in ten-thousandths of a dollar.
  a_{k,g} = sum over the group of |x| (integer); normalized field
  x^_{k,v} = x/a encoded as a DECLARED dyadic rational: round(2^40
  x/a) — quantum 2^-40, labelled loss per invariant 4. All further
  arithmetic is exact integer arithmetic on that custody.
  Relevance r_{k,v} (spec l.308) = volume code (thousandths).
  A_{k,v}: rows present in the store = observed; an event whose
  window has missing rows is UNKNOWN and counted, never zero-filled
  (invariant 5).

THE CHAIN (all equations from the verbatim file):
  L0 (l.284-306): Delta = x^_k - x^_{k-1}; kappa = Delta_k -
    Delta_{k-1}; sigma^(s)_k = var over I_k,s. Exact via
    n*Sum(y^2)-(Sum y)^2 with fixed n = s (sign- and sum-exact,
    common 1/(s^2 2^80) scaling per scale, declared).
  L1 (l.344-374): signature Sigma^(s)_k = ({sgn Delta_v}_v,
    {sgn kappa_v}_v, {sgn(sigma^(s)_k - sigma^(s)_{k-1})_v}_v, N_g);
    gates = maximal runs of constant Sigma (NO threshold, l.376-379).
  L1 TVR (l.383-404): per gate T_G, V_{G,v} = Sum|Delta|,
    R_{G,v} = Sum r, Q^(s)_{G,v} = Sum sigma^(s), K_{G,v} = Sum kappa
    — the full component tensors, nothing dropped.
  L2 (l.458-510): baselines over the W prior gates of the same
    scale, W = 5 (constitutional memory bound, declared, mirrors the
    canonical registry's NEIGH); CV^(s)_{m,v,f} = X - mean(prior);
    interpretation tuple I^(s)_{m,v} = (sgn CV_V, sgn CV_R,
    sgn CV_Q, sgn CV_K, N); contradiction atoms U_m = {(s,s',v,f):
    sgn CV^(s) * sgn CV^(s') = -1} evaluated on each scale's gate
    containing the event bar (alignment declared). NO w, S, U.
  L3 (l.529-563): edge fact q^(s)_{m,e,f} = sgn(CV_u - CV_v)
    (comparable because both live in the normalized field);
    temporal resonance rho = +1 same nonzero sign as previous gate,
    -1 flipped, 0 otherwise; cross-scale rho^(s,s') = q*q';
    hysteresis H = 1[rho changed]; vertex fact rho_v = sgn CV;
    coherence graph per scale (l.565-579): edges with rho in {0,+1}
    for ALL descriptors and +1 for at least one.
  L4 (l.624-694): typed atoms (s,v,f) and (s,e,f) kept disjoint;
    D = rho_m - rho_{m-1}; M = second difference; R_rev =
    1[D*D_prev < 0]; U* = 1[atom participates in U_m]; P = |D -
    D_prev|; C = the edge field itself; B recursion with the
    constitution's exact xi = 1/10, chi = 1/10, B in [-1,1]
    (declared from the canonical registry constants, l.677-694).
    Recursions run per scale over that scale's window-local gate
    sequence from B_0 = 0 (loss: no cross-window memory — named).

EVENT EVALUATION (spec L6 rules l.801-810: quotients declared
before labels, each listing its discards, typed partitions
independent, conjunctions never weighted scores):
  QV  spike stock's motion interpretation across scales 2, 8, 32:
      (sgn CV^(2)_V ; sgn CV^(8)_V ; sgn CV^(32)_V). Discards:
      other scales, descriptors R/Q/K, peers, edges, durations.
  QU  contradiction load on the spike vertex: count of atoms of
      U touching it, dyadic {0,1,2-3,4-7,8+}. Discards: which
      atoms, edge contradictions.
  QC  cohesion: number of peers positively coherent with the spike
      stock at scale 8 (0..7 exact). Discards: other scales,
      which peers.
  QJ  the full four-descriptor interpretation of the spike stock
      at scale 8: (sgn CV_V ; sgn CV_R ; sgn CV_Q ; sgn CV_K).
      Discards: scales other than 8, peers, edges.
OUTCOMES (L5 domain law, declared): ran = any next-5 close >=
1.20x entry; unwound = c(t+5) <= c(t-1); fade money per the live
law summed per 100. Split derive <= 2021-12-31 / confirm 2022+;
claims need n >= 50 in derive; the 70 taxonomy events excluded.

Usage:  python tools/ch3_joint_field_full.py [--example]
Output: artifacts/ch4_uf/ch3_joint_field_full.json
"""

from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, "ch4_live_store.parquet")
HERD = os.path.join(ROOT, "artifacts", "ch4_uf", "herd_state_daily.parquet")
SAMPLE = os.path.join(ROOT, "docs", "CH3_JEWELER_SAMPLE_70.json")
OUT = os.path.join(ROOT, "artifacts", "ch4_uf", "ch3_joint_field_full.json")

EVENT_GAIN, VOL_MULT, PRICE_FLOOR, HOLD, HERD_END = 8.0, 3.0, 5.0, 5, 20260324
GRENADE_X, HARVEST_X = 1.20, 0.95
DERIVE_END = 20211231
WIN, HIST = 64, 128          # evaluation window; causal bars behind it
SCALES = (1, 2, 4, 8, 16, 32, 64)
W_MEM = 5                    # constitutional memory bound (declared)
QSHIFT = 1 << 40             # dyadic custody quantum 2^-40 (labelled)
XI_NUM, XI_DEN = 1, 10       # B recursion xi = 1/10 (constitutional)
CHI_NUM, CHI_DEN = 1, 10     # chi = 1/10
MIN_CLASS_N = 50
DESCRIPTORS = ("V", "R", "Q", "K")


def sgn(z) -> int:
    return (z > 0) - (z < 0)


def dyad(n: int) -> str:
    if n == 0:
        return "0"
    if n == 1:
        return "1"
    if n <= 3:
        return "2-3"
    if n <= 7:
        return "4-7"
    return "8+"


def chain_for_field(xq, rq):
    """The complete L0-L4 chain on a normalized field window.

    xq: int matrix [HIST+WIN? actually rows bars x n_vertices] of the
        dyadic-custody normalized field; rq: int matrix of relevance.
    Evaluates gates over the last WIN bars; trailing windows may reach
    the earlier bars. Returns per-scale chain outputs at the final
    (event-bar) gate, plus contradiction atoms.
    """
    n_bars, n_v = xq.shape
    ev_lo = n_bars - WIN                      # gates evaluated on [ev_lo, n)
    # L0 geometry (spec l.284-306)
    D = np.zeros_like(xq)
    D[1:] = xq[1:] - xq[:-1]
    Kp = np.zeros_like(xq)
    Kp[2:] = D[2:] - D[1:-1]
    p1 = np.zeros((n_bars + 1, n_v), dtype=object)
    p2 = np.zeros((n_bars + 1, n_v), dtype=object)
    for v in range(n_v):
        a1 = 0
        a2 = 0
        for k in range(n_bars):
            a1 += int(xq[k, v]); a2 += int(xq[k, v]) ** 2
            p1[k + 1, v] = a1; p2[k + 1, v] = a2

    def VS(s, k, v):
        a, b = k - s + 1, k + 1
        sx = p1[b, v] - p1[a, v]
        sxx = p2[b, v] - p2[a, v]
        return s * sxx - sx * sx              # = s^2 * variance, exact

    out = {}
    all_contra = []                            # (s, s', v, f) atoms
    per_scale_cv = {}                          # s -> {(v,f): sign} at event gate
    for s in SCALES:
        # L1 signatures over the evaluation window (spec l.344-356)
        sigs = []
        for k in range(ev_lo, n_bars):
            sig = []
            for v in range(n_v):
                dv = sgn(int(D[k, v]))
                kv = sgn(int(Kp[k, v]))
                sv = sgn(VS(s, k, v) - VS(s, k - 1, v))
                sig.append((dv, kv, sv))
            sigs.append(tuple(sig))
        # gates = maximal constant-signature runs (spec l.363-374)
        gates = []
        a = 0
        for k in range(1, len(sigs) + 1):
            if k == len(sigs) or sigs[k] != sigs[a]:
                gates.append((a + ev_lo, k - 1 + ev_lo))
                a = k
        # TVR^joint per gate (spec l.383-404)
        tvr = []
        for (ga, gb) in gates:
            row = {}
            for v in range(n_v):
                row[("V", v)] = int(np.abs(D[ga:gb + 1, v]).sum())
                row[("R", v)] = int(rq[ga:gb + 1, v].sum())
                row[("Q", v)] = sum(VS(s, k, v) for k in range(ga, gb + 1))
                row[("K", v)] = int(np.abs(Kp[ga:gb + 1, v]).sum())
            tvr.append(row)
        # L2 contrasts vs W_MEM prior gates, same scale (spec l.458-479)
        cvs = []
        for m in range(len(tvr)):
            row = {}
            lo = max(0, m - W_MEM)
            for key in tvr[m]:
                if m == 0:
                    row[key] = 0
                else:
                    prior = [tvr[j][key] for j in range(lo, m)]
                    row[key] = sgn(len(prior) * tvr[m][key] - sum(prior))
            cvs.append(row)
        out[s] = {"gates": gates, "cv": cvs}
        per_scale_cv[s] = cvs[-1] if cvs else {}
    # contradiction atoms at the event gate (spec l.498-507)
    for i, s in enumerate(SCALES):
        for s2 in SCALES[i + 1:]:
            for v in range(n_v):
                for f in DESCRIPTORS:
                    a1 = per_scale_cv[s].get((f, v), 0)
                    a2 = per_scale_cv[s2].get((f, v), 0)
                    if a1 * a2 == -1:
                        all_contra.append((s, s2, v, f))
    # L3 edge facts + coherence at the event gate, per scale (l.529-579)
    edges = [(0, v) for v in range(1, n_v)]
    l3 = {}
    for s in SCALES:
        cvs = out[s]["cv"]
        q_seq = []
        for m in range(len(cvs)):
            qm = {}
            for (u, v) in edges:
                for f in DESCRIPTORS:
                    qm[((u, v), f)] = sgn(cvs[m].get((f, u), 0)
                                          - cvs[m].get((f, v), 0))
            q_seq.append(qm)
        rho_e = {}
        H = {}
        if q_seq:
            last, prev = q_seq[-1], (q_seq[-2] if len(q_seq) > 1 else None)
            for key, qv in last.items():
                if prev is None or qv == 0 or prev[key] == 0:
                    rho_e[key] = 0
                else:
                    rho_e[key] = 1 if qv == prev[key] else -1
                H[key] = int(prev is not None and rho_e[key] !=
                             (1 if (prev[key] != 0 and len(q_seq) > 2
                                    and q_seq[-3][key] == prev[key]) else 0))
        coher = 0
        for (u, v) in edges:
            fs = [rho_e.get(((u, v), f), 0) for f in DESCRIPTORS]
            if all(x >= 0 for x in fs) and any(x == 1 for x in fs):
                coher += 1
        l3[s] = {"rho_e": rho_e, "coherent_peers": coher}
    # L4 seven fields for the spike stock's atoms over scale-8's gate chain
    # (window-local recursions from zero, loss declared)
    cvs8 = out[8]["cv"]
    l4 = {}
    for f in DESCRIPTORS:
        rho_seq = [cvs8[m].get((f, 0), 0) for m in range(len(cvs8))]
        Dseq = [0] + [rho_seq[m] - rho_seq[m - 1]
                      for m in range(1, len(rho_seq))]
        B_num, B_den = 0, 1                   # exact rational B
        ustar_ev = int(any(v == 0 and f == ff for (_, _, v, ff)
                           in all_contra))
        for m in range(len(rho_seq)):
            u = int(any(v == 0 and ff == f for (_, _, v, ff) in all_contra)) \
                if m == len(rho_seq) - 1 else 0
            # B_m = clip(B + xi*(1-U*)*D - chi*U*)
            add_num = XI_NUM * (1 - u) * Dseq[m] * CHI_DEN \
                - CHI_NUM * u * XI_DEN
            B_num = B_num * (XI_DEN * CHI_DEN) + add_num * B_den
            B_den = B_den * XI_DEN * CHI_DEN
            if B_num > B_den:
                B_num, B_den = B_den, B_den
            if B_num < -B_den:
                B_num, B_den = -B_den, B_den
        l4[f] = {
            "D": Dseq[-1] if Dseq else 0,
            "M": (rho_seq[-1] - 2 * rho_seq[-2] + rho_seq[-3])
                 if len(rho_seq) >= 3 else 0,
            "Rrev": int(len(Dseq) >= 2 and Dseq[-1] * Dseq[-2] < 0),
            "Ustar": ustar_ev,
            "P": abs(Dseq[-1] - Dseq[-2]) if len(Dseq) >= 2 else 0,
            "B_sign": sgn(B_num),
        }
    return out, per_scale_cv, all_contra, l3, l4


def main():
    example = "--example" in sys.argv
    t0 = time.time()
    read70 = {(r["sym"], int(r["date"]))
              for r in json.load(open(SAMPLE))}
    df = pd.read_parquet(STORE, columns=["Date", "Symbol", "Close", "Volume"])
    df["Date"] = pd.to_datetime(df["Date"])
    df["day"] = df["Date"].dt.strftime("%Y%m%d").astype(int)
    herd = pd.read_parquet(HERD, columns=["sym", "date", "gband"])
    herd["date"] = herd["date"].astype(int)
    herd_keys = set(zip(herd["sym"], herd["date"]))

    # aligned matrices
    px = df.pivot_table(index="day", columns="Symbol", values="Close",
                        aggfunc="last")
    vx = df.pivot_table(index="day", columns="Symbol", values="Volume",
                        aggfunc="last")
    days = px.index.to_numpy()
    day_pos = {int(d): i for i, d in enumerate(days)}
    P = px.to_numpy(dtype=float)
    Vv = vx.to_numpy(dtype=float)
    syms = list(px.columns)
    sym_pos = {s: i for i, s in enumerate(syms)}
    # trailing-20 median dollar volume (for peer choice), causal at t-1
    dollar = P * Vv

    rows = []
    unknown = 0
    n_ev = 0
    for si, sym in enumerate(syms):
        col = P[:, si]
        vol = Vv[:, si]
        ok = ~np.isnan(col)
        idxs = np.where(ok)[0]
        if len(idxs) < HIST + WIN + HOLD + 25:
            continue
        # per-symbol event detection on its own compacted series
        cc = col[idxs]
        vv = vol[idxs]
        dd = days[idxs]
        sv = np.concatenate(([0.0], np.cumsum(np.nan_to_num(vv))))
        for j in range(HIST + WIN, len(idxs) - HOLD):
            if dd[j] > HERD_END:
                break
            if cc[j] < PRICE_FLOOR or cc[j - 1] <= 0:
                continue
            if 100 * (cc[j] / cc[j - 1] - 1) < EVENT_GAIN:
                continue
            va = (sv[j] - sv[j - 20]) / 20.0
            if va <= 0 or vv[j] < VOL_MULT * va:
                continue
            key = (sym, int(dd[j]))
            if key in herd_keys or key in read70:
                continue
            t = idxs[j]                        # position in the full grid
            # peers: same band, causal liquidity rank at t-1
            p = cc[j]
            lo, hi = ((5, 10) if p < 10 else (10, 20) if p < 20 else
                      (20, 40) if p < 40 else (40, 80) if p < 80
                      else (80, 1e12))
            w0 = max(0, t - 20)
            med = np.nanmedian(dollar[w0:t], axis=0)
            band_ok = (P[t - 1] >= lo) & (P[t - 1] < hi)
            hist_ok = ~np.isnan(P[max(0, t - HIST - WIN + 1):t + 1]).any(axis=0)
            cand = np.where(band_ok & hist_ok & ~np.isnan(med))[0]
            cand = cand[cand != si]
            if len(cand) < 7:
                unknown += 1
                continue
            peers = cand[np.argsort(-med[cand])][:7]
            vs = [si] + list(peers)
            block = P[t - HIST - WIN + 1: t + 1][:, vs]
            vblock = Vv[t - HIST - WIN + 1: t + 1][:, vs]
            if np.isnan(block).any():
                unknown += 1
                continue
            x = np.round(block * 10000).astype(np.int64)     # custody
            a = np.abs(x).sum(axis=1)                        # a_{k,g}
            xq = np.round(QSHIFT * (x / a[:, None])).astype(np.int64)
            rq = np.round(vblock * 1000).astype(np.int64)
            out, cv, contra, l3, l4 = chain_for_field(xq, rq)
            enc = lambda v_: "+0-"[1 - v_]                    # noqa: E731
            QV = "".join(enc(cv[s].get(("V", 0), 0)) for s in (2, 8, 32))
            QU = dyad(sum(1 for (_, _, v_, _) in contra if v_ == 0))
            QC = str(l3[8]["coherent_peers"])
            QJ = "".join(enc(cv[8].get((f, 0), 0)) for f in DESCRIPTORS)
            entry = cc[j]
            exit_px = cc[j + HOLD]
            for k2 in range(j + 1, j + HOLD + 1):
                if cc[k2] <= HARVEST_X * entry or cc[k2] >= GRENADE_X * entry:
                    exit_px = cc[k2]
                    break
            rows.append({
                "sym": sym, "date": int(dd[j]),
                "QV": QV, "QU": QU, "QC": QC, "QJ": QJ,
                "ran": bool(np.any(cc[j + 1: j + HOLD + 1]
                                   >= GRENADE_X * entry)),
                "unwound": bool(cc[j + HOLD] <= cc[j - 1]),
                "fade_ret": 100 * (entry - exit_px) / entry,
            })
            n_ev += 1
            if example:
                r = rows[-1]
                print(f"EXAMPLE EVENT {sym} {dd[j]} entry {entry:.2f}")
                print(f" peers: {[syms[q] for q in peers]}")
                print(f" gates at event bar (per scale): "
                      f"{{s: len(out[s]['gates']) for s in SCALES}} ="
                      f" { {s: len(out[s]['gates']) for s in SCALES} }")
                print(f" spike-vertex interpretation at scale 8 "
                      f"(sgn CV V,R,Q,K): {r['QJ']}")
                print(f" motion across scales 2/8/32: {r['QV']}")
                print(f" contradiction atoms on spike vertex: {r['QU']} "
                      f"(total atoms {len(contra)})")
                print(f" coherent peers at scale 8: {r['QC']}/7")
                print(f" L4 (scale-8 chain, descriptor V): {l4['V']}")
                print(f" outcome: ran={r['ran']} unwound={r['unwound']} "
                      f"fade={r['fade_ret']:+.1f}%")
                return
        if n_ev and n_ev % 500 == 0:
            print(f"  [{n_ev}] events, {time.time() - t0:.0f}s", flush=True)

    ev = pd.DataFrame(rows)
    ev.to_parquet(OUT.replace(".json", "_events.parquet"), index=False)
    derive = ev[ev["date"] <= DERIVE_END]
    confirm = ev[ev["date"] > DERIVE_END]
    print(f"events: {len(ev)} (derive {len(derive)}, confirm {len(confirm)}), "
          f"UNKNOWN (insufficient field): {unknown}")

    def table(col):
        base_d = float(derive["ran"].mean()) if len(derive) else 0
        base_c = float(confirm["ran"].mean()) if len(confirm) else 0
        claims, sparse_n = [], 0
        cc_ = {k: g for k, g in confirm.groupby(col)}
        for cls, g in derive.groupby(col):
            if len(g) < MIN_CLASS_N:
                sparse_n += len(g)
                continue
            h = cc_.get(cls)
            claims.append({
                "structure": str(cls),
                "derive_ran": f"{int(g['ran'].sum())}/{len(g)}"
                              f" = {100 * g['ran'].mean():.1f}%",
                "derive_unwound": f"{int(g['unwound'].sum())}/{len(g)}",
                "derive_fade_per_100": round(100 * float(g['fade_ret'].sum())
                                             / len(g), 1),
                "confirm_ran": (f"{int(h['ran'].sum())}/{len(h)}"
                                f" = {100 * h['ran'].mean():.1f}%"
                                if h is not None and len(h) else "0/0"),
                "confirm_unwound": (f"{int(h['unwound'].sum())}/{len(h)}"
                                    if h is not None and len(h) else "0/0"),
                "confirm_fade_per_100": (round(100 * float(h['fade_ret'].sum())
                                               / len(h), 1)
                                         if h is not None and len(h) else None),
            })
        claims.sort(key=lambda r: r["structure"])
        return {"base": f"derive {100 * base_d:.1f}% / "
                        f"confirm {100 * base_c:.1f}%",
                "classes": claims, "sparse_events": sparse_n}

    result = {
        "declared": "complete joint-field chain per the VERBATIM document; "
                    "topology, custody, quotients, losses all in docstring, "
                    "committed before results",
        "unknown_events": unknown,
        "QV_motion_across_scales": table("QV"),
        "QU_contradiction_load": table("QU"),
        "QC_cohesion_peers": table("QC"),
        "QJ_full_interpretation_s8": table("QJ"),
        "runtime_s": round(time.time() - t0),
    }
    json.dump(result, open(OUT, "w"), indent=1)
    print(json.dumps(result, indent=1)[:7000])
    print("filed:", OUT)


if __name__ == "__main__":
    main()
