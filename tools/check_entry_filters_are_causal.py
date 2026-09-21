"""Lookahead detector for entry filters.

Why this exists
---------------
`L5_CANONICAL_BASELINE.md` (locked 2026-03-25) and the header of
`web/scripts/execution/financial_rules.mjs` advertise this ladder:

    Accumulate only        57.1% WR | 7,290 signals
    + Close >= $5          57.7% WR | 6,556 signals
    + Rising 5d            75.0% WR | 3,674 signals
    + B_k > -0.80          81.1% WR | 2,072 signals
    + B_k > -0.50          81.4% WR | 2,016 signals

"Rising 5d" is `Return_5d > 0`, and `Return_5d` in
`quarantine_12k_l5_trades.csv` is the **forward** five-day return — verified
400/400 against the raw bars. It selects rows whose price rose AFTER the entry
and then scores what happened after that. It is worth +17.6 points of pure
lookahead, and every rung above it inherits the contamination.

That number stood for six months, shaped the production diagnosis ("entries
are fine, exits are broken"), and cost real money chasing an exit bug that was
never the whole story. It survived because nobody asked one question:

    can this quantity be computed from bars strictly BEFORE the entry bar?

This script asks it mechanically, for every column of a trades/signals file,
so the next contaminated ladder fails immediately instead of shipping.

Method
------
For each numeric column, test whether its values match a forward-looking
transform of the price series at the signal date. A column matches "forward
N-day return" if close[i+N]/close[i]-1 reproduces it. Any match is a
lookahead column and must never be used to select an entry.

Usage:
  python tools/check_entry_filters_are_causal.py quarantine_12k_l5_trades.csv
  python tools/check_entry_filters_are_causal.py <file.csv> --bars <bars.parquet>

Exit code 1 if any lookahead column is found.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BARS = ROOT / "quarantine_12k_universe.parquet"
HORIZONS = (1, 2, 3, 5, 10, 20, 60)
SAMPLE = 400
TOL = 1e-6


def main() -> int:
    src = Path(sys.argv[1])
    bars_path = Path(sys.argv[sys.argv.index("--bars") + 1]) if "--bars" in sys.argv else DEFAULT_BARS
    t = pd.read_csv(src, parse_dates=["Date"])
    u = pd.read_parquet(bars_path, columns=["Date", "Symbol", "Close"])
    u["Date"] = pd.to_datetime(u.Date)
    groups = {s: g.sort_values("Date").reset_index(drop=True) for s, g in u.groupby("Symbol", sort=False)}

    numeric = [c for c in t.columns if c not in ("Date", "Symbol") and pd.api.types.is_numeric_dtype(t[c])]
    print(f"{src.name}: {len(t)} rows, checking {len(numeric)} numeric columns "
          f"against bars from {bars_path.name}\n")

    sample = t.head(SAMPLE)
    verdicts = {}
    for col in numeric:
        fwd_hits = {h: 0 for h in HORIZONS}
        back_hits = {h: 0 for h in HORIZONS}
        n = 0
        for _, r in sample.iterrows():
            g = groups.get(r.Symbol)
            if g is None:
                continue
            i = g.index[g.Date == r.Date]
            if not len(i):
                continue
            i = i[0]; n += 1
            v = r[col]
            if not np.isfinite(v):
                continue
            c = g.Close.values
            for h in HORIZONS:
                if i + h < len(c) and abs((c[i + h] / c[i] - 1) - v) < TOL:
                    fwd_hits[h] += 1
                if i - h >= 0 and abs((c[i] / c[i - h] - 1) - v) < TOL:
                    back_hits[h] += 1
        if not n:
            continue
        fh = max(fwd_hits, key=lambda k: fwd_hits[k])
        bh = max(back_hits, key=lambda k: back_hits[k])
        if fwd_hits[fh] > 0.9 * n:
            verdicts[col] = ("LOOKAHEAD", f"forward {fh}-day return ({fwd_hits[fh]}/{n})")
        elif back_hits[bh] > 0.9 * n:
            verdicts[col] = ("causal", f"trailing {bh}-day return ({back_hits[bh]}/{n})")
        else:
            verdicts[col] = ("unmatched", "not a plain price return")

    bad = [c for c, (v, _) in verdicts.items() if v == "LOOKAHEAD"]
    for col, (v, why) in verdicts.items():
        mark = "!! " if v == "LOOKAHEAD" else "   "
        print(f"{mark}{col:16s} {v:10s} {why}")

    print()
    if bad:
        print(f"FAIL — {len(bad)} column(s) computed from bars AFTER the signal date:")
        for c in bad:
            print(f"        {c}")
        print("\nThese may be measured as outcomes. They must NEVER select an entry.")
        return 1
    print("PASS — no column reproduces a forward price return.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
