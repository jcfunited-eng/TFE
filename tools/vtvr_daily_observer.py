"""
vtvr_daily_observer.py
=======================

NON-CANONICAL — daily live observer for joint-field structural states.

Runs the frozen side kernel over the declared universe and appends today's
state memberships to a local ledger:

    artifacts/vtvr_observer/observations.jsonl

Observed states (frozen 2026-07-28 from the structure search; see
docs/TFE_SIDE_KERNEL_VTVR_MARKET_NONCANONICAL.md):

  coherent_laggard_v1  BRTH.L:MID & COH.S:HI & LTRND.L:LO
      moderate 120-bar breathing, top-third 30-bar herd coherence,
      bottom-third 120-bar leadership trend.
      Search WR@60 77.8% (N=418) | Holdout WR@60 78.0% (N=200, +8.87%).

  smooth_laggard_v1    LTRND.L:LO & REV.L:LO & BRTH.S:LO
      bottom-third leadership trend, smoothest-third motion, quietest-
      third recent breathing.
      Search WR@60 74.3% | Holdout 65.3% (+8.31%).

  calm_coherent_v1     smooth half + moderate pressure + moderate cohesion
      (the first composite from the 120-bar forward study).

Over time the ledger builds the forward-confirmation record on data no
study has ever seen. Score matured observations with --score.

Read-only vs markets; writes only its own ledger. Kernel untouched.

Usage:
    python tools/vtvr_daily_observer.py            # observe latest bar
    python tools/vtvr_daily_observer.py --score    # score matured rows
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.vtvr_structure_search import (  # noqa: E402
    build_field,
    per_step_arrays,
    window_desc,
    W_LONG,
    W_SHORT,
    _mean,
)

LEDGER_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "artifacts", "vtvr_observer",
)
LEDGER = os.path.join(LEDGER_DIR, "observations.jsonl")
SCORE_HORIZONS = (20, 60)


def _thirds_band(descs, key, n):
    order = sorted(range(n), key=lambda i: descs[i][key])
    band = {}
    for pos, i in enumerate(order):
        band[i] = ("LO", "MID", "HI")[min(2, (pos * 3) // n)]
    return band


def _halves_quartiles(descs, key, n):
    order = sorted(range(n), key=lambda i: descs[i][key])
    pos = {i: p for p, i in enumerate(order)}
    return pos


def evaluate_states(symbols, arrs, m):
    n = arrs["n"]
    dl = window_desc(arrs, m, W_LONG)
    ds = window_desc(arrs, m, W_SHORT)

    brth_l = _thirds_band(dl, "BRTH", n)
    coh_s = _thirds_band(ds, "COH", n)
    ltrnd_l = _thirds_band(dl, "LTRND", n)
    rev_l = _thirds_band(dl, "REV", n)
    brth_s = _thirds_band(ds, "BRTH", n)

    coherent_laggard = sorted(
        symbols[i] for i in range(n)
        if brth_l[i] == "MID" and coh_s[i] == "HI" and ltrnd_l[i] == "LO"
    )
    smooth_laggard = sorted(
        symbols[i] for i in range(n)
        if ltrnd_l[i] == "LO" and rev_l[i] == "LO" and brth_s[i] == "LO"
    )

    p_rev = _halves_quartiles(dl, "REV", n)
    p_pre = _halves_quartiles(dl, "PRES", n)
    p_coh = _halves_quartiles(dl, "COH", n)
    calm_coherent = sorted(
        symbols[i] for i in range(n)
        if p_rev[i] < n // 2
        and n // 4 <= p_pre[i] < 3 * n // 4
        and n // 4 <= p_coh[i] < 3 * n // 4
    )

    return {
        "coherent_laggard_v1": coherent_laggard,
        "smooth_laggard_v1": smooth_laggard,
        "calm_coherent_v1": calm_coherent,
    }


def observe():
    symbols, common, field, px = build_field()
    arrs = per_step_arrays(symbols, field)
    m = arrs["m"] - 1
    if m < W_LONG:
        raise SystemExit("Insufficient history for the 120-bar entry filter.")

    states = evaluate_states(symbols, arrs, m)

    os.makedirs(LEDGER_DIR, exist_ok=True)
    stamp = datetime.now(timezone.utc).isoformat()
    with open(LEDGER, "a", encoding="utf-8") as fh:
        for state, members in states.items():
            fh.write(json.dumps({
                "observed_at": stamp,
                "bar_date": common[m][:10],
                "state": state,
                "members": members,
                "universe_size": arrs["n"],
                "h_raw": field.h_raw,
            }) + "\n")
    print(f"Observed {common[m][:10]}:")
    for state, members in states.items():
        print(f"  {state:<22} {', '.join(members) if members else '(empty)'}")
    print(f"Ledger: {LEDGER}")


def score():
    if not os.path.exists(LEDGER):
        raise SystemExit("No observations ledger yet.")
    symbols, common, field, px = build_field()
    date_idx = {d[:10]: k for k, d in enumerate(common)}
    with open(LEDGER, encoding="utf-8") as fh:
        rows = [json.loads(line) for line in fh if line.strip()]
    n_scored = 0
    for row in rows:
        k = date_idx.get(row["bar_date"])
        if k is None:
            continue
        for h in SCORE_HORIZONS:
            if k + h >= len(common):
                continue
            rets = []
            for s in row["members"]:
                if s in symbols:
                    i = symbols.index(s)
                    rets.append((px[k + h][i] - px[k][i]) / px[k][i])
            if rets:
                wr = _mean([1.0 if r > 0 else 0.0 for r in rets]) * 100
                print(f"{row['bar_date']} {row['state']} +{h}: n={len(rets)} "
                      f"mean={_mean(rets)*100:+.2f}% win={wr:.0f}%")
                n_scored += 1
    if not n_scored:
        print("No matured observations to score yet.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--score", action="store_true")
    args = ap.parse_args()
    (score if args.score else observe)()
