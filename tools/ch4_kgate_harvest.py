"""
ch4_kgate_harvest.py — the harvest cycle on the herd-conditioned object
=======================================================================

Addendum-4 refinement, declared before measurement: replace the blind
K-gate exit with each HG-species' OWN causally-earned harvest shape.

  ENTRY   band >= 0.75 prediction of the herd-conditioned species
          (bigram x herd energy x greed at issue; prior-day herd state
          when the stream is intraday), filled at the issue event's
          reveal close. Long on +1, short on -1.
  EXIT    evaluated at each subsequent gate-reveal close of the symbol:
          TARGET  favorable return >= the species' causal 75th
                  percentile of past winning harvest returns
          STOP    adverse return >= the species' causal 75th
                  percentile of past losing harvest magnitudes
          TIME    10 events elapsed (the K=10 horizon)
          Until a species has 10 completed harvests, the replicated
          baseline applies: exit at the 3rd event (blind K=3).
  STORES  per HG-species lists of completed harvest returns, updated
          at settlement (available only to later issues). Strictly
          causal, nothing tuned: 75/10/3/10 are declared once.
  BOOK    fresh $100,000 per entry year, 10% slices, max 10 open.

Usage: [CH3_PREDS=...] [CH4_HERD_LAG=1] python tools/ch4_kgate_harvest.py
Output: CH4_OUT (json), default artifacts/ch4_uf/ch4_kgate_harvest.json
"""

from __future__ import annotations

import hashlib
import heapq
import json
import os
from collections import defaultdict

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREDS = os.environ.get("CH3_PREDS") or os.path.join(
    ROOT, "artifacts", "ch4_uf", "ch3_daily_preds_all.parquet")
HERD = os.path.join(ROOT, "artifacts", "ch4_uf", "herd_state_daily.parquet")
HERD_LAG = int(os.environ.get("CH4_HERD_LAG", "0"))
OUT = os.environ.get("CH4_OUT") or os.path.join(
    ROOT, "artifacts", "ch4_uf", "ch4_kgate_harvest.json")
W = 20
BAND = 0.75
Q = 75                 # species quantile for target and stop
N_MIN = 10             # completed harvests before shape exits activate
K_BASE = 3             # baseline exit while the shape record is young
K_MAX = 10             # time boundary
CASH0, SLICE_PCT, MAX_OPEN = 100_000.0, 10.0, 10


def hid(*parts) -> int:
    h = hashlib.blake2b("|".join(str(p) for p in parts).encode(),
                        digest_size=8)
    return int.from_bytes(h.digest(), "big") >> 1


def main():
    df = pd.read_parquet(PREDS)
    df = df[df["alpha"] == "bigram"]
    mx = int(df["issue_d"].max())
    if mx > 10 ** 10:
        key_div, day_div = 10 ** 8, 10 ** 4
    elif mx > 10 ** 9:
        key_div, day_div = 10 ** 6, 10 ** 2
    else:
        key_div, day_div = 10 ** 4, 1
    herd = pd.read_parquet(HERD)
    hmap = {(s, d): (c, e, g) for s, d, c, e, g in zip(
        herd["sym"], herd["date"].astype(int), herd["cell"],
        herd["eband"], herd["gband"])}
    herd_days = sorted(herd["date"].astype(int).unique())
    import bisect

    def herd_at(sym, day):
        if HERD_LAG == 0:
            return hmap.get((sym, day))
        i = bisect.bisect_left(herd_days, day) - 1
        return hmap.get((sym, herd_days[i])) if i >= 0 else None

    # global chronological event stream
    df = df.sort_values(["issue_d", "sym"], kind="mergesort")
    events = list(zip(df["issue_d"].astype(int), df["sym"],
                      df["species"].astype(int),
                      df["issue_px"].astype(float)))
    print(f"events {len(events)} | herd states {len(hmap)} | lag={HERD_LAG}")

    # HG completion ledger for prediction bands (as-of-issue): the
    # completion object is the K_BASE-gate displacement, matching the
    # replicated entry law. Completions become available at the K_BASE-th
    # later event of the same symbol.
    per_sym = defaultdict(list)                # sym -> [(issue, sp_hg, px)]
    comp_heap = []                             # (avail_key, sp_hg, sign)
    pos, neg = defaultdict(int), defaultdict(int)
    shape = defaultdict(lambda: {"win": [], "loss": []})   # settled harvests
    held = {}                                  # sym -> position
    books = {}
    hold_events = []

    def book(y):
        return books.setdefault(y, {"cash": CASH0, "rets": [], "reasons":
                                    defaultdict(int)})

    def settle(sym, px, reason):
        h = held.pop(sym)
        ret = (px / h["epx"] - 1.0) * h["side"]
        b = books[h["y"]]
        b["cash"] += h["notional"] * (1 + ret)
        b["rets"].append(100 * ret)
        b["reasons"][reason] += 1
        st = shape[h["sp"]]
        (st["win"] if ret > 0 else st["loss"]).append(abs(100 * ret))
        hold_events.append(h["events"])

    for issue, sym, sp, px in events:
        # completions that became knowable strictly before this instant
        while comp_heap and comp_heap[0][0] < issue:
            _a, csp, sgn = heapq.heappop(comp_heap)
            if sgn > 0:
                pos[csp] += 1
            elif sgn < 0:
                neg[csp] += 1
        st_h = herd_at(sym, int(issue // day_div))
        # manage an open position on this symbol at its event close
        h = held.get(sym)
        if h is not None:
            h["events"] += 1
            ret = 100 * (px / h["epx"] - 1.0) * h["side"]
            if h["tgt"] is not None and ret >= h["tgt"]:
                settle(sym, px, "TARGET")
            elif h["stp"] is not None and ret <= -h["stp"]:
                settle(sym, px, "STOP")
            elif h["tgt"] is None and h["events"] >= K_BASE:
                settle(sym, px, "K_BASE")
            elif h["events"] >= K_MAX:
                settle(sym, px, "TIME")
        if st_h is None or px <= 0:
            per_sym[sym].append((issue, None, px))
            continue
        c, e, g = st_h
        sp_hg = hid(sp, "HG", e, g)
        # feed the completion ledger: this event completes the K_BASE-ago
        # entry candidate of the same symbol
        hist = per_sym[sym]
        hist.append((issue, sp_hg, px))
        if len(hist) > K_BASE:
            i0, sp0, px0 = hist[-1 - K_BASE]
            if sp0 is not None and px0 > 0:
                d = px / px0 - 1.0
                heapq.heappush(comp_heap, (issue, sp0,
                                           1 if d > 0 else (-1 if d < 0 else 0)))
        if sym in held:
            continue
        p, q = pos[sp_hg], neg[sp_hg]
        n = p + q
        if n < W:
            continue
        f = p / n
        band = max(f, 1 - f)
        if band < BAND:
            continue
        pred = 1 if f >= 0.5 else -1
        y = str(issue // key_div)
        b = book(y)
        open_y = sum(1 for x in held.values() if x["y"] == y)
        notional = min(b["cash"] * SLICE_PCT / 100.0, b["cash"])
        if open_y >= MAX_OPEN or notional <= 0:
            continue
        sh = shape[sp_hg]
        tgt = float(np.percentile(sh["win"], Q)) \
            if len(sh["win"]) + len(sh["loss"]) >= N_MIN and sh["win"] else None
        stp = float(np.percentile(sh["loss"], Q)) \
            if tgt is not None and sh["loss"] else None
        b["cash"] -= notional
        held[sym] = {"y": y, "notional": notional, "epx": px, "side": pred,
                     "sp": sp_hg, "events": 0, "tgt": tgt, "stp": stp}

    for sym in list(held.keys()):        # force-close at last seen event px
        h = held[sym]
        last_px = per_sym[sym][-1][2] if per_sym[sym] else h["epx"]
        settle(sym, last_px, "END")

    by_year = {}
    for y in sorted(books):
        b = books[y]
        rets = b["rets"]
        wins = sum(1 for r in rets if r > 0)
        by_year[y] = {"trades": len(rets),
                      "wr_pct": round(100 * wins / len(rets), 1) if rets else None,
                      "mean_ret_pct": round(float(np.mean(rets)), 3) if rets else None,
                      "made_usd": round(b["cash"] - CASH0, 2),
                      "ret_pct": round(100 * (b["cash"] / CASH0 - 1), 2),
                      "exits": dict(b["reasons"])}
    hh = np.array(hold_events) if hold_events else np.array([0])
    result = {"frame": "harvest cycle on HG K-gate object — quantile "
                       f"target/stop (Q{Q}, N>={N_MIN}), K_BASE={K_BASE} "
                       f"young-species exit, K_MAX={K_MAX}; strict "
                       "as-of-issue, reveal-slipped",
              "median_events_held": float(np.median(hh)),
              "by_year": by_year}
    with open(OUT, "w") as f:
        json.dump(result, f, indent=1)
    print(json.dumps(result, indent=1))
    print("filed:", OUT)


if __name__ == "__main__":
    main()
