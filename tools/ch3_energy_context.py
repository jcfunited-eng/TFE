"""
ch3_energy_context.py — individual lifetime energy, group energy, system energy
===============================================================================

DECLARED 2026-08-17 BEFORE THE RUN. Joe's directive, verbatim: "you
need to see the entire structure, compare it to similar shares and
evaluate the energy of the individual and the group over the entire
lifetime and the presence of system energy." Three nested readings
per event, all causal at the event close, all counts — no averages,
no fitted thresholds.

INDIVIDUAL (whole lifetime through the kernel): the stock's full
  history flows through the canonical L0-L4 chain. The event bar's
  stored-tension reading URF(t) is placed within the stock's OWN
  prior life: life_pos = (# prior bars since warmup with URF <
  URF(t)) / (# prior bars). An exact count-rank, discretized in
  quarters Q1..Q4 (counts, not fitted constants). Same for the raw
  structural action perV(t) within its own life.
GROUP (similar shares, v1 declared): the event day's cohort — every
  other stock in the store that qualifies as an uncovered spike the
  SAME day. Group reading = cohort size in dyadic classes
  {1, 2-3, 4-7, 8-15, 16+}. (Behavior-similarity families by
  trailing field correlation are the v2 refinement — the streaming-
  correlation mask bug in family_heat_for must be fixed first; this
  is disclosed, not hidden.)
SYSTEM (presence of system energy): the herd frame's breadth that
  day — the share of covered names carrying crowd energy (gband >=
  1) — in the classes {100%, [75,100), [50,75), [25,50), [0,25)}
  (quarters plus the known saturated state; the 100% state occurs on
  ~39% of decade days and is a distinct physical regime, measured
  long ago). Plus total market supply that day (all qualifying
  spikes, covered and uncovered) in dyadic classes.

QUOTIENTS (all declared now, none added after labels):
  J   the joint structure ( life_URF_quarter ; cohort_class ;
      breadth_class ) — sparse is reported sparse
  M1  life_URF_quarter alone       M2  life_act_quarter alone
  M3  cohort_class alone           M4  breadth_class alone
  M5  supply_class alone           M6  ( life_URF_quarter ; breadth_class )
EVENT SET / LABEL / SPLIT: identical to the tuple-time run
(uncovered spikes, grenade = any next-5 close >= 1.20x entry,
derive <= 2021-12-31, confirm frozen 2022+, n >= 50 to claim,
universe imbalance across the split disclosed).

Usage:  python tools/ch3_energy_context.py
Output: artifacts/ch4_uf/ch3_energy_context.json
        artifacts/ch4_uf/ch3_energy_context_events.parquet
"""

from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.ch4_uf_kernel_v2 import replay_symbol_v2  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, "ch4_live_store.parquet")
HERD = os.path.join(ROOT, "artifacts", "ch4_uf", "herd_state_daily.parquet")
OUT = os.path.join(ROOT, "artifacts", "ch4_uf", "ch3_energy_context.json")
OUT_TABLE = os.path.join(ROOT, "artifacts", "ch4_uf",
                         "ch3_energy_context_events.parquet")

EVENT_GAIN, VOL_MULT, PRICE_FLOOR, HOLD, HERD_END = 8.0, 3.0, 5.0, 5, 20260324
GRENADE_X = 1.20
DERIVE_END = 20211231
WARMUP = 60
MIN_CLASS_N = 50


def quarter(frac: float) -> str:
    return "Q4" if frac >= 0.75 else ("Q3" if frac >= 0.5
                                      else ("Q2" if frac >= 0.25 else "Q1"))


def dyad(n: int) -> str:
    if n <= 1:
        return "1"
    if n <= 3:
        return "2-3"
    if n <= 7:
        return "4-7"
    if n <= 15:
        return "8-15"
    return "16+"


def breadth_class(share: float) -> str:
    if share >= 1.0:
        return "100"
    if share >= 0.75:
        return "75-100"
    if share >= 0.5:
        return "50-75"
    if share >= 0.25:
        return "25-50"
    return "0-25"


def main():
    t0 = time.time()
    df = pd.read_parquet(STORE, columns=["Date", "Symbol", "Close", "Volume"])
    df["Date"] = pd.to_datetime(df["Date"])
    df["day"] = df["Date"].dt.strftime("%Y%m%d").astype(int)
    herd = pd.read_parquet(HERD, columns=["sym", "date", "gband"])
    herd["date"] = herd["date"].astype(int)
    herd_keys = set(zip(herd["sym"], herd["date"]))
    breadth = herd.groupby("date")["gband"].apply(
        lambda s: float((s >= 1).mean())).to_dict()

    # -------- pass 1: find ALL qualifying spikes (covered + uncovered) ----
    all_spikes, unc_events = {}, []       # day -> total count; event list
    per_sym = {}
    for sym, s in df.groupby("Symbol", sort=False):
        s = s.sort_values("Date")
        c = s["Close"].to_numpy(dtype=float)
        v = s["Volume"].to_numpy(dtype=float)
        d = s["day"].to_numpy()
        if len(c) < WARMUP + HOLD + 5:
            continue
        per_sym[sym] = (s["Date"].to_numpy(), c, v, d)
        sv = np.concatenate(([0.0], np.cumsum(v)))
        for t in range(WARMUP, len(c) - HOLD):
            if d[t] > HERD_END:
                break
            if c[t] < PRICE_FLOOR or c[t - 1] <= 0:
                continue
            if 100 * (c[t] / c[t - 1] - 1) < EVENT_GAIN:
                continue
            va = (sv[t] - sv[t - 20]) / 20.0
            if va <= 0 or v[t] < VOL_MULT * va:
                continue
            day = int(d[t])
            all_spikes[day] = all_spikes.get(day, 0) + 1
            if (sym, day) not in herd_keys:
                unc_events.append((sym, t, day))
    unc_per_day = {}
    for _, _, day in unc_events:
        unc_per_day[day] = unc_per_day.get(day, 0) + 1
    print(f"pass 1: {sum(all_spikes.values())} spikes total, "
          f"{len(unc_events)} uncovered, {time.time() - t0:.0f}s", flush=True)

    # -------- pass 2: kernel over each event symbol's whole life ---------
    rows = []
    by_sym = {}
    for sym, t, day in unc_events:
        by_sym.setdefault(sym, []).append((t, day))
    n_done = skipped = 0
    for sym, evs in by_sym.items():
        dates, c, v, d = per_sym[sym]
        try:
            states = replay_symbol_v2(dates, c, v, warmup=WARMUP)
        except Exception:  # noqa: BLE001
            skipped += len(evs)
            continue
        urf = np.array([s.URF if s is not None else np.nan for s in states])
        act = np.abs(np.diff(np.log(c + 1e-8), prepend=np.log(c[0] + 1e-8)))
        for t, day in evs:
            prior = urf[WARMUP:t]
            prior = prior[~np.isnan(prior)]
            if len(prior) < 20:
                continue
            life_urf = quarter(float((prior < urf[t]).sum()) / len(prior))
            pact = act[WARMUP:t]
            life_act = quarter(float((pact < act[t]).sum()) / len(pact))
            b = breadth.get(day)
            bc = breadth_class(b) if b is not None else "none"
            rows.append({
                "sym": sym, "date": day,
                "life_urf": life_urf, "life_act": life_act,
                "cohort": dyad(unc_per_day.get(day, 1)),
                "breadth": bc,
                "supply": dyad(all_spikes.get(day, 1)),
                "J": f"{life_urf};{dyad(unc_per_day.get(day, 1))};{bc}",
                "M6": f"{life_urf};{bc}",
                "grenade": bool(np.any(c[t + 1: t + HOLD + 1]
                                       >= GRENADE_X * c[t])),
            })
        n_done += 1
        if n_done % 500 == 0:
            print(f"  [{n_done}] symbols, {len(rows)} events, "
                  f"{time.time() - t0:.0f}s", flush=True)

    ev = pd.DataFrame(rows)
    ev.to_parquet(OUT_TABLE, index=False)
    derive = ev[ev["date"] <= DERIVE_END]
    confirm = ev[ev["date"] > DERIVE_END]
    print(f"events: {len(ev)} (derive {len(derive)}, confirm {len(confirm)}), "
          f"replay-skipped: {skipped}")

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
                "structure": str(cls),
                "derive": f"{gd}/{nd} = {100 * gd / nd:.1f}%",
                "confirm": f"{gc}/{nc} = {100 * gc / nc:.1f}%" if nc else "0/0",
                "derive_vs_base": round(100 * gd / nd - 100 * base_d, 1),
                "confirm_vs_base": round(100 * gc / nc - 100 * base_c, 1)
                if nc else None,
            })
        claims.sort(key=lambda r: str(r["structure"]))
        return {"base_derive": f"{int(derive['grenade'].sum())}/{len(derive)}"
                               f" = {100 * base_d:.1f}%",
                "base_confirm": f"{int(confirm['grenade'].sum())}/{len(confirm)}"
                                f" = {100 * base_c:.1f}%",
                "classes_with_claims": claims,
                "sparse_events_no_claim": sparse_n}

    result = {
        "declared": "individual-lifetime / group-cohort / system-energy "
                    "quotients declared in docstring before the run; counts "
                    "only; v1 group = same-day cohort (correlation families "
                    "deferred until the family_heat mask bug is fixed — "
                    "disclosed)",
        "replay_skipped_events": skipped,
        "J_joint_life_group_system": freq_table("J"),
        "M1_individual_life_energy": freq_table("life_urf"),
        "M2_individual_life_action": freq_table("life_act"),
        "M3_group_cohort_size": freq_table("cohort"),
        "M4_system_breadth": freq_table("breadth"),
        "M5_system_supply": freq_table("supply"),
        "M6_life_x_system": freq_table("M6"),
        "runtime_s": round(time.time() - t0),
    }
    json.dump(result, open(OUT, "w"), indent=1)
    print(json.dumps(result, indent=1)[:8000])
    print("filed:", OUT)


if __name__ == "__main__":
    main()
