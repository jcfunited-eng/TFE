"""
ch3_joint_field_shadow.py — the joint-field shadow, per THE SPEC
================================================================

DECLARED 2026-08-18 BEFORE THE FIRST RUN; CORRECTED 2026-08-17 after
an adversarial five-agent audit of the implementation. Correction
record (nothing hidden):

  CRITICAL (found by audit, fixed here): the first run's Q_B built
  its five variance-motion components as sgn(sgn(dVS_t)-sgn(dVS_p))
  — the sign of a difference of SIGNS — while the declaration said
  sgn(dVS_t - dVS_p) on the integer values. The quotient actually
  run was a coarsening of the declared one. THIS rerun reports BOTH:
    Q_B_declared     the value-difference quotient as originally
                     declared (run here for the first time);
    Q_B_persistence  the coarser sign-persistence quotient the first
                     run actually computed (kept, relabelled for
                     what it is; its component 0 means "variance
                     motion kept its sign", i.e. gate continuation).
  The first run's "one survivor" belongs to Q_B_persistence.

  DISCLOSURES added per audit (all verified by the auditors):
  - Volumes are float64 (the store holds fractional volumes); the
    trailing-volume sums are exact below 2^53. "Exact integer
    arithmetic" is scoped to the FIELD FACTS (D, K, VS, dVS, N)
    computed on integer price custody. The event filter and grenade
    label run in float, deliberately identical to every prior CH3
    study so event sets stay comparable (L5 domain law, not kernel).
  - Price custody quantizes: ~13k of 15.7M closes sit off the
    0.0001 grid and are rounded onto it (max residue half a grid
    step).
  - N is DEGENERATE inside this event set (the +8% gate forces
    D_t > 0, so four equal closes are impossible): Q_A's effective
    bound is 3^6 = 729 classes, not 1458. N is retained in the
    string for spec fidelity, always '0'.
  - Events in a symbol's final 5 bars are dropped (the 5-close label
    needs 5 future bars). Spikes-then-delistings are exactly the
    tail this censors; the count of censored qualifying spikes is
    now measured and filed.
  - The derive and confirm halves come from materially different
    universes (store symbol coverage roughly triples across the
    split): 1.3k derive vs 12.2k confirm events, base 11.6% vs
    16.0%. Claims are judged per-class within each half against
    that half's own base — never across halves.
  - Confirm truncates at HERD_END=20260324 (last herd-covered date;
    later events cannot receive the no-herd-row check honestly).
  - Derive events dated in the last 5 sessions of 2021 carry labels
    read from early-January-2022 closes (mechanical smear, cannot
    steer class selection).
  - Symbols shorter than 40 bars are skipped; the first 34 bars of
    every series are event-ineligible (32-bar windows need history).

FINANCIAL PROJECTION (declared): single-vertex field per stock.
Custody: prices as integers in ten-thousandths of a dollar.

FIELD FACTS at bar k (x = price int, s in dyadic scales {2,4,8,16,32}):
  D_k       = x_k - x_{k-1}                      displacement (int)
  K_k       = D_k - D_{k-1}                      curvature (int)
  VS(s,k)   = s*sum(x^2 over I_{k,s}) - (sum x over I_{k,s})^2
              where I_{k,s} = the s bars ending at k    (int; equals
              s^2 * variance — sign-exact for equal-length windows)
  dVS(s,k)  = VS(s,k) - VS(s,k-1)                variance motion (int)
  N_k       = 1 iff the last 4 closes are identical (degenerate here)

SIGNATURE at bar k (thresholdless, exact):
  SIG_k = ( sgn K_k ; ( sgn dVS(s,k) for each s ) ; N_k )
  (sgn D_k omitted: the event filter fixes it positive — disclosed.)

QUOTIENTS (no others; frequencies over exact structures, never a score):
  Q_A            the event-bar signature SIG_k alone.
  Q_B_declared   SIG_k + ( sgn(K_t - K_{t-1}) ;
                 ( sgn(dVS(s,t) - dVS(s,t-1)) for each s ) )
                 — the L4 D-field on VALUES, as originally declared.
  Q_B_persistence SIG_k + ( sgn(K_t - K_{t-1}) ;
                 ( sgn(sgn dVS(s,t) - sgn dVS(s,t-1)) for each s ) )
                 — sign persistence (0 = variance motion kept its
                 sign); what the first run actually measured.

EVENT SET (L5 domain law, float, identical to all prior CH3 studies):
uncovered spikes — day gain >= +8%, volume >= 3x trailing-20 mean
(bars t-20..t-1), close >= $5, no herd row. LABEL: grenade = any of
the next 5 closes >= 1.20 x entry.

PROCEDURE: structures label-blind; derive (<= 2021-12-31) / confirm
(2022+); per-class grenade frequencies with counts in both halves;
claims need n >= 50 in derive and are judged solely on confirm.
Sparse classes reported sparse, never folded into a scalar.

Usage:  python tools/ch3_joint_field_shadow.py
Output: artifacts/ch4_uf/ch3_joint_field_shadow.json
        artifacts/ch4_uf/ch3_joint_field_events.parquet (raw table)
"""

from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, "ch4_live_store.parquet")
HERD = os.path.join(ROOT, "artifacts", "ch4_uf", "herd_state_daily.parquet")
OUT = os.path.join(ROOT, "artifacts", "ch4_uf", "ch3_joint_field_shadow.json")
OUT_TABLE = os.path.join(ROOT, "artifacts", "ch4_uf",
                         "ch3_joint_field_events.parquet")

EVENT_GAIN, VOL_MULT, PRICE_FLOOR, HOLD, HERD_END = 8.0, 3.0, 5.0, 5, 20260324
GRENADE_X = 1.20
DERIVE_END = 20211231
SCALES = (2, 4, 8, 16, 32)
MIN_CLASS_N = 50


def sgn(z: int) -> int:
    return (z > 0) - (z < 0)


def main():
    df = pd.read_parquet(STORE, columns=["Date", "Symbol", "Close", "Volume"])
    df["Date"] = pd.to_datetime(df["Date"])
    df["day"] = df["Date"].dt.strftime("%Y%m%d").astype(int)
    herd = pd.read_parquet(HERD, columns=["sym", "date", "gband"])
    herd["date"] = herd["date"].astype(int)
    herd_keys = set(zip(herd["sym"], herd["date"]))

    rows = []
    censored = 0                      # qualifying spikes with <5 future bars
    for sym, s_df in df.groupby("Symbol", sort=False):
        s_df = s_df.sort_values("Date")
        cf = s_df["Close"].to_numpy(dtype=float)
        vf = s_df["Volume"].to_numpy(dtype=float)
        d = s_df["day"].to_numpy()
        n = len(cf)
        if n < max(SCALES) + 8:
            continue
        x = np.round(cf * 10000).astype(np.int64)
        sv = np.concatenate(([0.0], np.cumsum(vf)))
        xo = x.astype(object)
        px1 = np.concatenate(([0], np.cumsum(xo)))
        px2 = np.concatenate(([0], np.cumsum(xo * xo)))

        def VS(s, k):
            """s * sum(x^2) - (sum x)^2 over the s bars ending at k. Exact."""
            a, b = k - s + 1, k + 1
            sx = px1[b] - px1[a]
            sxx = px2[b] - px2[a]
            return s * sxx - sx * sx

        def qualifies(t):
            if cf[t] < PRICE_FLOOR or cf[t - 1] <= 0:
                return False
            if 100 * (cf[t] / cf[t - 1] - 1) < EVENT_GAIN:
                return False
            va = (sv[t] - sv[t - 20]) / 20.0
            if va <= 0 or vf[t] < VOL_MULT * va:
                return False
            return (sym, int(d[t])) not in herd_keys

        for t in range(max(SCALES) + 2, n):
            if d[t] > HERD_END:
                break
            if not qualifies(t):
                continue
            if t >= n - HOLD:
                censored += 1         # label unobtainable — counted, dropped
                continue
            dvs_t, dvs_p, ddvs_val = [], [], []
            for s in SCALES:
                a = VS(s, t) - VS(s, t - 1)
                b = VS(s, t - 1) - VS(s, t - 2)
                dvs_t.append(sgn(a))
                dvs_p.append(sgn(b))
                ddvs_val.append(sgn(a - b))
            D_t = int(x[t] - x[t - 1])
            D_p = int(x[t - 1] - x[t - 2])
            D_pp = int(x[t - 2] - x[t - 3])
            K_t = D_t - D_p
            K_p = D_p - D_pp
            N_t = int(x[t] == x[t - 1] == x[t - 2] == x[t - 3])
            qa = (sgn(K_t),) + tuple(dvs_t) + (N_t,)
            acc = (sgn(K_t - K_p),)
            qb_decl = qa + acc + tuple(ddvs_val)
            qb_pers = qa + acc + tuple(sgn(a - b)
                                       for a, b in zip(dvs_t, dvs_p))
            enc = lambda tup: "".join("+0-"[1 - v] for v in tup)  # noqa: E731
            rows.append({
                "sym": sym, "date": int(d[t]),
                "QA": enc(qa), "QBd": enc(qb_decl), "QBp": enc(qb_pers),
                "grenade": bool(np.any(cf[t + 1: t + HOLD + 1]
                                       >= GRENADE_X * cf[t])),
            })

    ev = pd.DataFrame(rows)
    ev.to_parquet(OUT_TABLE, index=False)
    derive = ev[ev["date"] <= DERIVE_END]
    confirm = ev[ev["date"] > DERIVE_END]
    print(f"events: {len(ev)} (derive {len(derive)}, confirm {len(confirm)}), "
          f"censored: {censored}")

    def freq_table(col):
        base_d = float(derive["grenade"].mean())
        base_c = float(confirm["grenade"].mean())
        claims, sparse_n = [], 0
        d_groups = derive.groupby(col)
        c_counts = {k: (int(g["grenade"].sum()), len(g))
                    for k, g in confirm.groupby(col)}
        for cls, g in d_groups:
            nd = len(g)
            if nd < MIN_CLASS_N:
                sparse_n += nd
                continue
            gd = int(g["grenade"].sum())
            gc, nc = c_counts.get(cls, (0, 0))
            claims.append({
                "structure": cls,
                "derive": f"{gd}/{nd} = {100 * gd / nd:.1f}%",
                "confirm": f"{gc}/{nc} = {100 * gc / nc:.1f}%" if nc else "0/0",
                "derive_vs_base": round(100 * gd / nd - 100 * base_d, 1),
                "confirm_vs_base": round(100 * gc / nc - 100 * base_c, 1)
                if nc else None,
            })
        claims.sort(key=lambda r: -abs(r["derive_vs_base"]))
        return {"base_derive": f"{int(derive['grenade'].sum())}/{len(derive)}"
                               f" = {100 * base_d:.1f}%",
                "base_confirm": f"{int(confirm['grenade'].sum())}/{len(confirm)}"
                                f" = {100 * base_c:.1f}%",
                "classes_with_claims": claims,
                "sparse_events_no_claim": sparse_n,
                "n_distinct_structures_derive": int(d_groups.ngroups)}

    result = {
        "declared": "CORRECTED RERUN after adversarial audit: Q_B_declared "
                    "(value differences, as originally declared) now actually "
                    "run; Q_B_persistence = the coarser quotient the first "
                    "run computed, relabelled; all audit disclosures in the "
                    "docstring (float L5 filter/label, N degeneracy, censored "
                    "events counted, universe imbalance, HERD_END cut, "
                    "boundary label smear)",
        "censored_qualifying_spikes_no_label": censored,
        "Q_A_event_signature": freq_table("QA"),
        "Q_B_declared_value_diff": freq_table("QBd"),
        "Q_B_persistence_first_run": freq_table("QBp"),
    }
    json.dump(result, open(OUT, "w"), indent=1)
    print(json.dumps(result, indent=1)[:6000])
    print("filed:", OUT)


if __name__ == "__main__":
    main()
