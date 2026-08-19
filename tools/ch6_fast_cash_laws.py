"""
ch6_fast_cash_laws.py — Joseph's fast-cash proposals, declared before results
=============================================================================

DECLARED 2026-08-19 BEFORE THE RUN (Rule 9). Joseph's proposals, his
words: CH6 "is meant to be a fast cash grab — so maybe we open it up
and maybe drop the >=5% end of day sell to >=2%."

FRAME (identical to the filed exit studies for comparability —
ch3_structural_cut.py / ch3_vehicle_refusal.py): daily store,
herd-uncovered events only, short at the completed close c[t], path
c[t+1..t+5], TRUE GAP accounting (an exit books the close that
crossed the line, however deep), events capped at the herd-history
end. LIMITATION, stated: daily closes only — this measures the
end-of-day bank, not the intraday +5%-arm/1pt-trail harvest, which
the live engine keeps under both laws.

EVENT SETS (exactly two; no other definitions examined):
  CURRENT   gain >= 8% day, volume >= 3x trailing-20 mean, close >= $5
  WIDENED   gain >= 5% day, volume >= 2x trailing-20 mean, close >= $5
            (same species, smaller specimens — Joseph: "open it up")
  The MARGINAL set (widened minus current) is reported alone so the
  added supply's quality is visible, never blended.

LAWS (exactly two; the anomaly trigger and clock unchanged):
  LAW A (current): exit at first close <= 0.95 x entry (HARVEST) or
        first close >= 1.20 x entry (ANOMALY); else 5th close (TIME).
  LAW B (Joseph's 2% bank): HARVEST bar moves to 0.98 x entry;
        everything else identical.

REPORTING per half (derive <= 2023-12-31 / CONFIRM frozen 2024+),
per event set, per law: n, money per 100 events, outcome counts,
wins/losses, worst single event, events below -50%, mean sessions
held, share resolved on day 1, and overnight position-nights per
event (nights the book stays exposed). Money and counts, no naked
scalars. Filed to artifacts/ch4_uf/ch6_fast_cash_laws.json.

Usage:  python tools/ch6_fast_cash_laws.py
"""

from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, "ch4_live_store.parquet")
HERD = os.path.join(ROOT, "artifacts", "ch4_uf", "herd_state_daily.parquet")
OUT = os.path.join(ROOT, "artifacts", "ch4_uf", "ch6_fast_cash_laws.json")

PRICE_FLOOR, HOLD, HERD_END = 5.0, 5, 20260324
STOP_X = 1.20
DERIVE_END = 20231231
SETS = {"CURRENT_8pct_3x": (8.0, 3.0), "WIDENED_5pct_2x": (5.0, 2.0)}
LAWS = {"LAW_A_bank5": 0.95, "LAW_B_bank2": 0.98}


def main() -> None:
    df = pd.read_parquet(STORE, columns=["Date", "Symbol", "Close", "Volume"])
    df["Date"] = pd.to_datetime(df["Date"])
    df["day"] = df["Date"].dt.strftime("%Y%m%d").astype(int)
    herd = pd.read_parquet(HERD, columns=["sym", "date"])
    herd_keys = set(zip(herd["sym"], herd["date"].astype(int)))

    rows = []
    for sym, s_df in df.groupby("Symbol", sort=False):
        s_df = s_df.sort_values("Date")
        cf = s_df["Close"].to_numpy(dtype=float)
        vf = s_df["Volume"].to_numpy(dtype=float)
        d = s_df["day"].to_numpy()
        n = len(cf)
        if n < 26 + HOLD:
            continue
        sv = np.concatenate(([0.0], np.cumsum(vf)))
        for t in range(21, n - HOLD):
            if d[t] > HERD_END:
                break
            if cf[t] < PRICE_FLOOR or cf[t - 1] <= 0:
                continue
            gain = 100 * (cf[t] / cf[t - 1] - 1)
            if gain < 5.0:          # widest bar; set membership below
                continue
            va = (sv[t] - sv[t - 20]) / 20.0
            if va <= 0 or vf[t] < 2.0 * va:
                continue
            if (sym, int(d[t])) in herd_keys:
                continue
            entry = cf[t]
            in_current = gain >= 8.0 and vf[t] >= 3.0 * va
            row = {"date": int(d[t]), "in_current": in_current}
            for law, harvest_x in LAWS.items():
                exit_px, status, k_exit = cf[t + HOLD], "TIME", HOLD
                for k in range(1, HOLD + 1):
                    px = cf[t + k]
                    if px <= harvest_x * entry:
                        exit_px, status, k_exit = px, "HARVEST", k
                        break
                    if px >= STOP_X * entry:
                        exit_px, status, k_exit = px, "ANOMALY", k
                        break
                row[f"{law}_ret"] = 100 * (entry - exit_px) / entry
                row[f"{law}_st"] = status
                row[f"{law}_days"] = k_exit
            rows.append(row)

    ev = pd.DataFrame(rows)
    ev.to_parquet(OUT.replace(".json", "_events.parquet"))
    print(f"events (widened frame): {len(ev)} (per-event rows filed)")

    def ledger(sub: pd.DataFrame) -> dict:
        out = {"n": int(len(sub))}
        if not len(sub):
            return out
        for law in LAWS:
            r, st, dy = sub[f"{law}_ret"], sub[f"{law}_st"], sub[f"{law}_days"]
            out[law] = {
                "money_per_100ev": round(100 * float(r.sum()) / len(sub), 1),
                "outcomes": {k: int(v) for k, v in st.value_counts().items()},
                "wins_losses": f"{int((r > 0).sum())}W/{int((r < 0).sum())}L",
                "worst_event_pct": round(float(r.min()), 1),
                "events_below_-50pct": int((r < -50).sum()),
                "mean_sessions_held": round(float(dy.mean()), 2),
                "resolved_day1": f"{int((dy == 1).sum())}/{len(sub)}",
                "position_nights_per_event": round(float(dy.mean()), 2),
            }
        return out

    result = {"declared": "frame, both event sets, both laws, split and "
                          "reporting in the docstring before results; daily-"
                          "close limitation stated"}
    for half_tag, half in (("derive_le_2023", ev[ev["date"] <= DERIVE_END]),
                           ("CONFIRM_2024_plus", ev[ev["date"] > DERIVE_END])):
        result[half_tag] = {
            "CURRENT_8pct_3x": ledger(half[half["in_current"]]),
            "MARGINAL_widened_only": ledger(half[~half["in_current"]]),
            "WIDENED_all": ledger(half),
        }
    json.dump(result, open(OUT, "w"), indent=1)
    print(json.dumps(result, indent=1))
    print("filed:", OUT)


if __name__ == "__main__":
    main()
