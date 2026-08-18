"""
ch3_field_state_precedent.py — similar energy conditions over the whole history
===============================================================================

DECLARED 2026-08-17 BEFORE THE RUN. Joe's method, assembled from his
directives: after the tuple is dimensionalized across time, "you look
for the similar energy conditions and behavior over the whole
history... then you can predict the pattern — and even tell junk
stocks, pump and dumps, etc, so you can cut them out of the analysis
to have a finer refined assessment."

PROVENANCE: 70 whole-life kernel readings (12-agent workflow, filed)
produced a taxonomy of field-states. This sweep freezes those states
as EXACT predicates and counts, across ALL uncovered spikes in the
decade, how each state resolved. The 70 read events are EXCLUDED
from the counts (they built the taxonomy; scored separately for
reference). Split derive <= 2021-12-31 / confirm 2022+ retained for
regime honesty — note the taxonomy was built on 2024+ events, so the
pre-2022 half is fully blind to the taxonomy's construction.

FIELD FACTS per event t (kernel outputs over the 20-bar approach,
all causal at the event close):
  urf0_run        consecutive bars ending at t with URF == 0
  bars_since_cl   bars since gate_count last incremented
  closures20      gate_count increments in t-19..t
  urf0_frac20     URF==0 bars in t-19..t
  rres_slope3     sgn(R_res(t) - R_res(t-3))
  rres_below_max  R_res(t) < max(R_res over t-5..t-1)
  fn_dir          sgn(F_n(t) - F_n(t-1))
  price_leak      sgn(close(t-1) - close at the current open gate's
                  start) — displacement through the block
  attn_alive      sgn(v(t-1) - median(v, trailing 20 at t-1)) —
                  attention awake BEFORE the spike day

STATE CLASSES (first match wins; the count constants 3/10/20/6 are
declared translations of the readers' qualitative language — "weeks
without a closure" >= 10 bars, "latched" >= 3 bars, "fast clock" >=
6 closures per 20 — fixed here before any scoring, not fitted):
  BLOCK_LIVE   (bars_since_cl >= 10 or urf0_run >= 3) and
               rres_slope3 >= 0 and price_leak > 0 and attn_alive >= 0
  BLOCK_DEAD   (bars_since_cl >= 10 or urf0_run >= 3) and
               (rres_slope3 < 0 or attn_alive < 0)
  BLOCK_OTHER  remaining blocked states
  ADMIT_CHEAP  closures20 >= 3 and urf0_frac20 == 0 and
               rres_slope3 > 0 and fn_dir <= 0
  SPENT_BACK   rres_below_max and fn_dir > 0
  CONDUCT      closures20 >= 6 and urf0_frac20 == 0
  OTHER        everything else

OUTCOMES (three declared scores per event — the clock is itself
noisy per the readings, so the physical outcomes ride beside it):
  grenade   any of next 5 closes >= 1.20 x entry      (the clock)
  retained  close(t+5) >= close(t)                    (level kept)
  relaxed   close(t+5) <= close(t-1)                  (full round trip)
Plus the fade's dollars under the live law (harvest 0.95x / cut
1.20x / 5-session time), summed per 100 events per class.

VEHICLE TYPING (Joe: junk / pump-and-dump cut, causal at t): a
blow-off scar = any prior day j < t-5 in the stock's own life with
close(j) >= 1.5 x close(j-5) followed within 10 bars by a close
<= 0.6 x close(j). scars(t) in {0, 1, 2+}. Every class table is
filed uncut AND with scarred vehicles (scars >= 1) removed —
the refined assessment beside the raw one, neither replacing the
other.

Usage:  python tools/ch3_field_state_precedent.py
Output: artifacts/ch4_uf/ch3_field_state_precedent.json
        artifacts/ch4_uf/ch3_field_state_events.parquet
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
SAMPLE = ("/tmp/claude-0/-workspaces-Tao-Financial-Engine/"
          "1e2e4787-6974-44f5-8e43-7b6605a7182e/scratchpad/"
          "jeweler_sample.json")
OUT = os.path.join(ROOT, "artifacts", "ch4_uf",
                   "ch3_field_state_precedent.json")
OUT_TABLE = os.path.join(ROOT, "artifacts", "ch4_uf",
                         "ch3_field_state_events.parquet")

EVENT_GAIN, VOL_MULT, PRICE_FLOOR, HOLD, HERD_END = 8.0, 3.0, 5.0, 5, 20260324
GRENADE_X, HARVEST_X = 1.20, 0.95
DERIVE_END = 20211231
WARMUP = 60
MIN_CLASS_N = 50


def sgn(z: float) -> int:
    return (z > 0) - (z < 0)


def classify(f):
    blocked = f["bars_since_cl"] >= 10 or f["urf0_run"] >= 3
    if blocked:
        if (f["rres_slope3"] >= 0 and f["price_leak"] > 0
                and f["attn_alive"] >= 0):
            return "BLOCK_LIVE"
        if f["rres_slope3"] < 0 or f["attn_alive"] < 0:
            return "BLOCK_DEAD"
        return "BLOCK_OTHER"
    if (f["closures20"] >= 3 and f["urf0_frac20"] == 0
            and f["rres_slope3"] > 0 and f["fn_dir"] <= 0):
        return "ADMIT_CHEAP"
    if f["rres_below_max"] and f["fn_dir"] > 0:
        return "SPENT_BACK"
    if f["closures20"] >= 6 and f["urf0_frac20"] == 0:
        return "CONDUCT"
    return "OTHER"


# v1.1 — DECLARED 2026-08-18 BEFORE ANY SWEEP RESULT EXISTED, after the
# NESR worked example exposed a translation defect in v1: the readers'
# "resonance alive/holding" was translated as a raw 3-bar sign, which
# calls a -0.005 wobble on a held 0.40 plateau "falling". The kernel's
# own notion of "unchanged resonance" is drift within one hysteresis
# width (H_MAX = 0.20, pinned in ch4_uf_kernel_v2). v1.1: charge is
# ALIVE iff R_res(t) - R_res(t-3) >= -0.20 (held within one width);
# DEAD iff it fell by more than the width or attention is starved.
# Both classifications are computed and filed; neither replaces the other.
def classify_v11(f):
    blocked = f["bars_since_cl"] >= 10 or f["urf0_run"] >= 3
    held = f["rres_d3"] >= -0.20
    if blocked:
        if held and f["price_leak"] > 0 and f["attn_alive"] >= 0:
            return "BLOCK_LIVE"
        if (not held) or f["attn_alive"] < 0:
            return "BLOCK_DEAD"
        return "BLOCK_OTHER"
    if (f["closures20"] >= 3 and f["urf0_frac20"] == 0
            and f["rres_slope3"] > 0 and f["fn_dir"] <= 0):
        return "ADMIT_CHEAP"
    if f["rres_below_max"] and f["fn_dir"] > 0:
        return "SPENT_BACK"
    if f["closures20"] >= 6 and f["urf0_frac20"] == 0:
        return "CONDUCT"
    return "OTHER"


def main():
    t0 = time.time()
    read70 = set()
    try:
        for r in json.load(open(SAMPLE)):
            read70.add((r["sym"], int(r["date"])))
    except Exception:  # noqa: BLE001 — sample custody lost => exclude nothing, disclose
        print("WARNING: jeweler sample file unreadable; 70-event "
              "exclusion NOT applied")
    df = pd.read_parquet(STORE, columns=["Date", "Symbol", "Close", "Volume"])
    df["Date"] = pd.to_datetime(df["Date"])
    df["day"] = df["Date"].dt.strftime("%Y%m%d").astype(int)
    herd = pd.read_parquet(HERD, columns=["sym", "date", "gband"])
    herd["date"] = herd["date"].astype(int)
    herd_keys = set(zip(herd["sym"], herd["date"]))

    rows = []
    n_done = skipped = 0
    for sym, s in df.groupby("Symbol", sort=False):
        s = s.sort_values("Date")
        c = s["Close"].to_numpy(dtype=float)
        v = s["Volume"].to_numpy(dtype=float)
        d = s["day"].to_numpy()
        dates = s["Date"].to_numpy()
        n = len(c)
        if n < WARMUP + HOLD + 25:
            continue
        sv = np.concatenate(([0.0], np.cumsum(v)))
        evs = []
        for t in range(WARMUP + 21, n - HOLD):
            if d[t] > HERD_END:
                break
            if c[t] < PRICE_FLOOR or c[t - 1] <= 0:
                continue
            if 100 * (c[t] / c[t - 1] - 1) < EVENT_GAIN:
                continue
            va = (sv[t] - sv[t - 20]) / 20.0
            if va <= 0 or v[t] < VOL_MULT * va:
                continue
            if (sym, int(d[t])) in herd_keys:
                continue
            evs.append(t)
        if not evs:
            continue
        try:
            states = replay_symbol_v2(dates, c, v, warmup=WARMUP)
        except Exception:  # noqa: BLE001
            skipped += len(evs)
            continue
        # blow-off scars, causal prefix scan once per symbol
        scar_day = np.zeros(n, dtype=np.int64)   # cumulative scars known by bar
        scars = 0
        for j in range(5, n - 10):
            if c[j - 5] > 0 and c[j] >= 1.5 * c[j - 5]:
                w = c[j + 1: j + 11]
                if len(w) and np.min(w) <= 0.6 * c[j]:
                    scars += 1
                    scar_day[j + 10:] = scars   # known once the collapse shows
        for t in evs:
            w = states[t - 20: t + 1]
            if any(x is None for x in w):
                continue
            st = states[t]
            gc_series = [x.gate_count for x in w]
            closures20 = int(gc_series[-1] - gc_series[0])
            bars_since_cl = 0
            for k in range(len(gc_series) - 1, 0, -1):
                if gc_series[k] != gc_series[k - 1]:
                    break
                bars_since_cl += 1
            urf_series = [x.URF for x in w]
            urf0_run = 0
            for k in range(len(urf_series) - 1, -1, -1):
                if urf_series[k] == 0.0:
                    urf0_run += 1
                else:
                    break
            gate_start = t - 1 - min(bars_since_cl, t - 1 - WARMUP)
            f = {
                "urf0_run": urf0_run,
                "bars_since_cl": bars_since_cl,
                "closures20": closures20,
                "urf0_frac20": int(sum(1 for u in urf_series if u == 0.0)),
                "rres_slope3": sgn(st.R_res - states[t - 3].R_res),
                "rres_d3": float(st.R_res - states[t - 3].R_res),
                "rres_below_max": bool(st.R_res < max(x.R_res
                                                      for x in w[-6:-1])),
                "fn_dir": sgn(st.F_n - states[t - 1].F_n),
                "price_leak": sgn(c[t - 1] - c[gate_start]),
                "attn_alive": sgn(v[t - 1]
                                  - float(np.median(v[max(0, t - 21): t - 1]))),
            }
            cls = classify(f)
            cls11 = classify_v11(f)
            entry = c[t]
            exit_px = c[t + HOLD]
            for k in range(t + 1, t + HOLD + 1):
                if c[k] <= HARVEST_X * entry or c[k] >= GRENADE_X * entry:
                    exit_px = c[k]
                    break
            rows.append({
                "sym": sym, "date": int(d[t]), "cls": cls, "cls11": cls11,
                "scars": ("2+" if scar_day[t] >= 2
                          else str(int(scar_day[t]))),
                "in70": (sym, int(d[t])) in read70,
                "grenade": bool(np.any(c[t + 1: t + HOLD + 1]
                                       >= GRENADE_X * entry)),
                "retained": bool(c[t + HOLD] >= entry),
                "relaxed": bool(c[t + HOLD] <= c[t - 1]),
                "fade_ret": 100 * (entry - exit_px) / entry,
            })
        n_done += 1
        if n_done % 500 == 0:
            print(f"  [{n_done}] symbols, {len(rows)} events, "
                  f"{time.time() - t0:.0f}s", flush=True)

    ev = pd.DataFrame(rows)
    ev.to_parquet(OUT_TABLE, index=False)
    body = ev[~ev["in70"]]
    print(f"events: {len(ev)} ({int(ev['in70'].sum())} were among the 70 "
          f"read — excluded from counts), replay-skipped: {skipped}")

    def table(sub, col="cls"):
        out = {}
        for cls, g in sub.groupby(col):
            if len(g) < MIN_CLASS_N:
                out[cls] = {"n": int(len(g)), "sparse": True}
                continue
            out[cls] = {
                "n": int(len(g)),
                "grenade": f"{int(g['grenade'].sum())}/{len(g)}"
                           f" = {100 * g['grenade'].mean():.1f}%",
                "retained": f"{int(g['retained'].sum())}/{len(g)}"
                            f" = {100 * g['retained'].mean():.1f}%",
                "relaxed": f"{int(g['relaxed'].sum())}/{len(g)}"
                           f" = {100 * g['relaxed'].mean():.1f}%",
                "fade_per_100ev": round(100 * float(g["fade_ret"].sum())
                                        / len(g), 1),
            }
        return out

    derive = body[body["date"] <= DERIVE_END]
    confirm = body[body["date"] > DERIVE_END]
    clean = body[body["scars"] == "0"]
    result = {
        "declared": "state predicates, translation constants, outcome "
                    "scores, scar typing and the 70-event exclusion all "
                    "declared in docstring before the run",
        "replay_skipped_events": skipped,
        "derive_le_2021_blind_to_taxonomy": table(derive),
        "confirm_2022_plus": table(confirm),
        "v1_1_hysteresis_aliveness_derive": table(derive, "cls11"),
        "v1_1_hysteresis_aliveness_confirm": table(confirm, "cls11"),
        "the_70_reference_only": table(ev[ev["in70"]]),
        "scar_distribution": {str(k): int(n) for k, n in
                              body["scars"].value_counts().items()},
        "refined_scars0_derive": table(clean[clean["date"] <= DERIVE_END]),
        "refined_scars0_confirm": table(clean[clean["date"] > DERIVE_END]),
        "scarred_vehicles_confirm": table(
            body[(body["scars"] != "0") & (body["date"] > DERIVE_END)]),
        "runtime_s": round(time.time() - t0),
    }
    json.dump(result, open(OUT, "w"), indent=1)
    print(json.dumps(result, indent=1)[:8000])
    print("filed:", OUT)


if __name__ == "__main__":
    main()
