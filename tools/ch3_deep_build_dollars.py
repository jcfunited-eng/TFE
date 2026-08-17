"""
ch3_deep_build_dollars.py — money per build-depth structure, current law
========================================================================

DECLARED 2026-08-17 BEFORE THE RUN. Diagnostic only: no rule is
derived here. Question: under the LIVE exit law (harvest 0.95x /
anomaly-cut 1.20x / 5-session time), what does each build-depth
structure class EARN per 100 events shorted? The gate-depth study
showed deep-build spikes are grenades ~20% of the time vs 16% base
(frozen 2024+); grenade odds are not dollars — a class can carry
more grenades and still pay. This files the dollars per class so
any future engine proposal (refuse / downsize deep-build events)
argues from money, not odds. Split ≤2023 / 2024+ as in the gates
round. Every class reported with counts; no pooling across classes.

Usage:  python tools/ch3_deep_build_dollars.py
Output: artifacts/ch4_uf/ch3_deep_build_dollars.json
"""

from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, "ch4_live_store.parquet")
EVENTS = os.path.join(ROOT, "artifacts", "ch4_uf",
                      "ch3_joint_field_gate_events.parquet")
OUT = os.path.join(ROOT, "artifacts", "ch4_uf", "ch3_deep_build_dollars.json")

HARVEST_X, STOP_X, HOLD = 0.95, 1.20, 5
DERIVE_END = 20231231


def main():
    ev = pd.read_parquet(EVENTS)
    df = pd.read_parquet(STORE, columns=["Date", "Symbol", "Close"])
    df["Date"] = pd.to_datetime(df["Date"])
    df["day"] = df["Date"].dt.strftime("%Y%m%d").astype(int)

    rets = []
    for sym, g in ev.groupby("sym"):
        s = df[df["Symbol"] == sym].sort_values("Date")
        c = s["Close"].to_numpy(dtype=float)
        days = s["day"].to_numpy()
        pos = {int(dd): i for i, dd in enumerate(days)}
        for _, r in g.iterrows():
            t = pos.get(int(r["date"]))
            if t is None or t + HOLD >= len(c):
                continue
            entry = c[t]
            exit_px = c[t + HOLD]
            for k in range(t + 1, t + HOLD + 1):
                if c[k] <= HARVEST_X * entry or c[k] >= STOP_X * entry:
                    exit_px = c[k]
                    break
            rets.append({"QC": r["QC"], "band": r["band"],
                         "date": int(r["date"]),
                         "ret": 100 * (entry - exit_px) / entry})
    t = pd.DataFrame(rets)

    def table(sub):
        out = {}
        for cls, g in sub.groupby("QC"):
            if len(g) < 30:
                continue
            out[cls] = {
                "n": int(len(g)),
                "sum_return_per_100_events":
                    round(100 * float(g["ret"].sum()) / len(g), 1),
                "wins_losses": f"{int((g['ret'] > 0).sum())}W/"
                               f"{int((g['ret'] < 0).sum())}L",
            }
        return out

    derive = t[t["date"] <= DERIVE_END]
    confirm = t[t["date"] > DERIVE_END]
    result = {
        "declared": "diagnostic of dollars per structure class under the "
                    "live exit law; no rule derived; declared before results",
        "derive_le_2023": table(derive),
        "confirm_2024_plus": table(confirm),
        "deep_build_80plus_frozen": table(
            confirm[(confirm["QC"].str.startswith("2-3")) |
                    (confirm["QC"].str.startswith("4-7")) |
                    (confirm["QC"].str.startswith("8+"))]),
    }
    json.dump(result, open(OUT, "w"), indent=1)
    print(json.dumps(result, indent=1))
    print("filed:", OUT)


if __name__ == "__main__":
    main()
