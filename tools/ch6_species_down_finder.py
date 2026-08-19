"""
ch6_species_down_finder.py — second prey for CH6, declared before results
=========================================================================

DECLARED 2026-08-19 BEFORE THE RUN (Rule 9). Joseph's order: grow the
candidate pool with a different hunt, then his fast-cash exit applies.

THE FINDER (one construction, no variants scanned):
  From the filed daily prediction stream (ch3_daily_preds_all.parquet,
  alpha = bigram, issue prices already reveal-slipped, band and count
  already as-of-issue): a candidate is any issue with
      pred = DOWN, band >= 0.75, n_at_issue >= 20.
  One open position per symbol at a time.

THE DOOR (the engine's own laws, from the daily store, as of entry):
  price >= $5; normal day (median of prior 20 sessions' close x volume)
  >= $200k; lifetime-peak/price < 1000 (suicide-pill ban); NOT sound
  (life >= 2y AND price >= half peak AND crush < 4 refuses).

THE EXIT (Joseph's fast-cash law, daily closes, TRUE GAP accounting):
  short at issue price; first close <= 0.98 x entry banks (his 2%);
  first close >= 1.20 x entry cuts at that close, however deep;
  else the 5th close. The 5% bank is reported beside it, both
  declared here.

THE CONTROL (declared 2026-08-19 BEFORE any result was read; the
first run's output sat unread until this control was added): the
IDENTICAL door and exit laws on the mirror population — pred = UP,
band >= 0.75, n >= 20, shorted the same way. The exit law banks
small wins early and stops at 20%, a shape with its own profit
profile on any population; the finder only exists if shorting the
"breaks down" class clearly beats shorting the "breaks up" class.
No beat, no finder — regardless of the absolute number.
Set CH6_SPECIES_CONTROL=1 to run the control population.

REPORTING: per year — trades, candidates per session (the pool size),
win rate, average dollars per $2,000 trade, worst event, events below
-50%, mean sessions held, day-one resolution. Split derive <= 2023 /
CONFIRM 2024+. Filed to artifacts/ch4_uf/ch6_species_down_finder.json.

Usage:  python tools/ch6_species_down_finder.py
"""

from __future__ import annotations

import json
import os
from collections import defaultdict

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREDS = os.path.join(ROOT, "artifacts", "ch4_uf", "ch3_daily_preds_all.parquet")
STORE = os.path.join(ROOT, "ch4_live_store.parquet")
OUT = os.path.join(
    ROOT, "artifacts", "ch4_uf",
    "ch6_species_down_finder"
    + ("_CONTROL_up_mirror" if os.environ.get("CH6_SPECIES_CONTROL") == "1"
       else "") + ".json")

CONTROL = os.environ.get("CH6_SPECIES_CONTROL") == "1"
PRED_SIDE = 1 if CONTROL else -1
BAND, N_MIN = 0.75, 20
PRICE_FLOOR, NORMAL_DAY_MIN, SHELL_CRUSH = 5.0, 200_000.0, 1000.0
STOP_X, HOLD = 1.20, 5
BANKS = {"bank2_Joseph": 0.98, "bank5_current": 0.95}
DERIVE_END = 20231231
SLICE_USD = 2_000.0


def main() -> None:
    preds = pd.read_parquet(
        PREDS, columns=["alpha", "sym", "issue_d", "issue_px", "pred",
                        "band", "n_at_issue"])
    preds = preds[(preds["alpha"] == "bigram") & (preds["pred"] == PRED_SIDE)
                  & (preds["band"] >= BAND) & (preds["n_at_issue"] >= N_MIN)]
    if CONTROL:
        print("CONTROL RUN: mirror population (pred = UP), shorted identically")
    preds = preds.assign(day=(preds["issue_d"] // 10 ** 4).astype(int))
    print(f"down candidates in stream: {len(preds)}")

    store = pd.read_parquet(STORE, columns=["Date", "Symbol", "Close", "Volume"])
    store["day"] = store["Date"].dt.strftime("%Y%m%d").astype(int)

    rows = []
    pool_days = defaultdict(set)
    for sym, sub in preds.groupby("sym", sort=False):
        hist = store[store["Symbol"] == sym].sort_values("Date")
        if not len(hist):
            continue
        c = hist["Close"].to_numpy(dtype=float)
        v = hist["Volume"].to_numpy(dtype=float)
        d = hist["day"].to_numpy()
        busy_until = 0
        for day, entry in sub[["day", "issue_px"]].sort_values("day").values:
            day = int(day)
            t = int(np.searchsorted(d, day))
            if t >= len(d) or d[t] != day or t < 21 or t + 1 >= len(d):
                continue
            pool_days[day // 10000].add((sym, day))
            if day <= busy_until or entry <= 0 or float(entry) < PRICE_FLOOR:
                continue
            normal_day = float(np.median(c[t - 20:t] * v[t - 20:t]))
            if normal_day < NORMAL_DAY_MIN:
                continue
            peak = float(c[:t].max())
            crush = peak / float(entry)
            if crush >= SHELL_CRUSH:
                continue
            life_years = (d[t] // 10000) - (d[0] // 10000) + (
                ((d[t] // 100) % 100) - ((d[0] // 100) % 100)) / 12.0
            if life_years >= 2 and float(entry) >= 0.5 * peak and crush < 4:
                continue
            entry = float(entry)
            path = c[t + 1: t + 1 + HOLD]
            path_days = d[t + 1: t + 1 + HOLD]
            if not len(path):
                continue
            row = {"sym": sym, "date": day}
            for tag, bank_x in BANKS.items():
                exit_px, status, k_exit = path[-1], "TIME", len(path)
                for k, px in enumerate(path, start=1):
                    if px <= bank_x * entry:
                        exit_px, status, k_exit = px, "BANK", k
                        break
                    if px >= STOP_X * entry:
                        exit_px, status, k_exit = px, "STOP", k
                        break
                row[f"{tag}_ret"] = 100 * (entry - exit_px) / entry
                row[f"{tag}_st"] = status
                row[f"{tag}_days"] = k_exit
            busy_until = int(path_days[min(row["bank2_Joseph_days"],
                                           len(path_days)) - 1])
            rows.append(row)

    ev = pd.DataFrame(rows)
    ev.to_parquet(OUT.replace(".json", "_events.parquet"))
    print(f"trades taken: {len(ev)} (per-event rows filed)")

    def ledger(sub: pd.DataFrame) -> dict:
        out = {"n": int(len(sub))}
        if not len(sub):
            return out
        for tag in BANKS:
            r, st, dy = sub[f"{tag}_ret"], sub[f"{tag}_st"], sub[f"{tag}_days"]
            out[tag] = {
                "avg_usd_per_2k_trade": round(float(r.mean()) * SLICE_USD / 100, 2),
                "outcomes": {k: int(x) for k, x in st.value_counts().items()},
                "wins_losses": f"{int((r > 0).sum())}W/{int((r < 0).sum())}L",
                "worst_event_pct": round(float(r.min()), 1),
                "events_below_-50pct": int((r < -50).sum()),
                "mean_sessions_held": round(float(dy.mean()), 2),
                "resolved_day1": f"{int((dy == 1).sum())}/{len(sub)}",
            }
        return out

    by_year = {}
    for y, g in ev.groupby(ev["date"] // 10000):
        by_year[str(y)] = {
            "trades": int(len(g)),
            "candidates_that_year": len(pool_days.get(y, ())),
            "bank2_avg_usd": round(float(g["bank2_Joseph_ret"].mean())
                                   * SLICE_USD / 100, 2),
            "bank2_wr_pct": round(100 * float((g["bank2_Joseph_ret"] > 0)
                                              .mean()), 1),
            "bank5_avg_usd": round(float(g["bank5_current_ret"].mean())
                                   * SLICE_USD / 100, 2),
        }

    result = {
        "declared": "finder, door, exits, split and reporting in the "
                    "docstring before results; issue prices reveal-slipped "
                    "by the stream's own construction",
        "derive_le_2023": ledger(ev[ev["date"] <= DERIVE_END]),
        "CONFIRM_2024_plus": ledger(ev[ev["date"] > DERIVE_END]),
        "by_year": by_year,
    }
    json.dump(result, open(OUT, "w"), indent=1)
    print(json.dumps(result, indent=1))
    print("filed:", OUT)


if __name__ == "__main__":
    main()
