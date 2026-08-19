"""
ch6_extinction_presence_law.py — LAW E: no death, no short
===========================================================

DECLARED 2026-08-19 BEFORE RESULTS, under Rule 9. Evaluated from the
FILED event record of the vehicle-refusal study
(artifacts/ch4_uf/ch3_vehicle_refusal_events.parquet — 12,098
uncovered decade events, true-gap fade accounting, facts computed by
the canonical v2 chain over each stock's entire prior life).

THE LAW (entry-side, both fade engines):
  REFUSE any candidate whose prior life contains ZERO channel deaths
  (extinction events). Rule 4: the short window is EXHAUSTED phase —
  crest in, push dead, buzz returning, channel deaths RESUMING. A
  life that has never died once cannot be in the deaths-resuming
  phase; Rule 5: a clean rehearsal floor is the loading state — stand
  aside. The boundary is presence/absence (exact zero structure), not
  a fitted threshold.

PROVENANCE: MINE-on-trial. Enters force only if BOTH halves say the
refused class is poorer per event than the kept class AND the refusal
does not concentrate the tail into the kept class.

HONESTY DISCLOSURE (Rule 9 / label-blindness): the confirm-half extN
marginal (0 -> 50.9 fade/100ev, monotone up to 16+ -> 247.6) was
READ by this session in the parent study's filed JSON before this
declaration — the confirm half is therefore NOT label-blind for
direction. The derive half's extN breakdown was never filed and is
first-look. The boundary (zero/nonzero) is structural, chosen from
Rule 4/5's own language, not from a sweep.

Split identical to the parent study: derive <= 2021-12-31,
confirm 2022+. Reporting: per half, kept vs refused — n, fade per
100 events, wins/losses, worst single event, events below -50%,
ran/unwound rates. Nothing else; no other boundaries examined.

Usage:  python tools/ch6_extinction_presence_law.py
Output: artifacts/ch4_uf/ch6_extinction_presence_law.json
"""

from __future__ import annotations

import json
import os

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVENTS = os.path.join(ROOT, "artifacts", "ch4_uf",
                      "ch3_vehicle_refusal_events.parquet")
OUT = os.path.join(ROOT, "artifacts", "ch4_uf",
                   "ch6_extinction_presence_law.json")
DERIVE_END = 20211231


def ledger(sub: pd.DataFrame) -> dict:
    if not len(sub):
        return {"n": 0}
    r = sub["fade_ret"]
    return {
        "n": int(len(sub)),
        "fade_per_100ev": round(100 * float(r.sum()) / len(sub), 1),
        "wins_losses": f"{int((r > 0).sum())}W/{int((r < 0).sum())}L",
        "worst_event_pct": round(float(r.min()), 1),
        "events_below_-50pct": int((r < -50).sum()),
        "ran": f"{int(sub['ran'].sum())}/{len(sub)}",
        "unwound": f"{int(sub['unwound'].sum())}/{len(sub)}",
    }


def main() -> None:
    ev = pd.read_parquet(EVENTS)
    ev["never_died"] = ev["extN"].astype(str) == "0"

    out = {"declared": "law, boundary, split, reporting and the "
                       "confirm-half contamination disclosure are in the "
                       "docstring, written before these numbers existed"}
    for tag, half in (("derive_le_2021", ev[ev["date"] <= DERIVE_END]),
                      ("CONFIRM_2022_plus", ev[ev["date"] > DERIVE_END])):
        out[tag] = {
            "KEPT_died_at_least_once": ledger(half[~half["never_died"]]),
            "REFUSED_never_died": ledger(half[half["never_died"]]),
        }
    json.dump(out, open(OUT, "w"), indent=1)
    print(json.dumps(out, indent=1))
    print("filed:", OUT)


if __name__ == "__main__":
    main()
