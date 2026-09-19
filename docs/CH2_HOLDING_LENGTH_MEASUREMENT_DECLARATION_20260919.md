# CH2 holding length — measurement declaration (2026-09-19)

Declared BEFORE any result is computed. Provenance: Joseph's order to drain
the failure filed in `CH2_WINNER_EXIT_MEASUREMENT_DECLARATION_20260919.md`,
where duration-matched random exits beat the current law in every case while
holding far less than its 47.8-session average.

## The question

**Does capping how long a CH2 position is held beat the current exit law, on a
population the live door could actually buy?**

## Population (fixed before measurement)

Same entry reconstruction as the winner-exit measurement — the live gate
(`computeV3Basin` port, verified) on the production kernel lanes,
2021-09-01 → 2026-09-19 — with two filters added, standing in for the
$500 M market-cap floor that has no historical series:

- **Liquidity floor**: median dollar volume (close × volume) over the 20
  sessions before the entry signal ≥ **$5,000,000**.
- **Price floor**: entry close ≥ **$5.00** (the live channel buys whole
  shares in ~$2,459 slices).

Both are declared once, here. They are proxies for tradable size, not the
capitalisation rule itself, and they are applied identically to the control,
every candidate and every null. The control is re-measured on this filtered
population; the earlier unfiltered control is not the comparison.

## Timing, prices, costs

Unchanged from the winner-exit declaration: decisions on a closed session,
fills at the next session's close, price stops at their trigger close, closes
only (no intraday range in the store), no costs or slippage modeled.

## Control

The current law, verbatim: dead clock (>16 closed sessions at or below entry
× 0.95 with no close back above), 90-day wall, −20 % brake, +20 % ratchet
floor, window end.

## Candidates (each measured alone)

A holding cap added to the control — the position closes at the next session's
close once it has been held N sessions, if nothing else has ended it first:

- **H10** — N = 10
- **H20** — N = 20
- **H30** — N = 30
- **H45** — N = 45 (an anchor beside the control's own average hold)

No other constants, no sweeps, no stacking with the structural candidates
already falsified.

## Null test

A duration null is meaningless for a rule that *is* a duration, so the null
here asks the other question: **is the advantage in CH2's entries, or in the
period itself?** For each candidate, 20 seeds of random-entry positions —
same tickers, same number of positions per ticker, entry sessions drawn at
random from that ticker's history, same holding cap, same control rules. A
candidate whose result is matched by random entries held the same length has
found nothing about CH2's picks.

## Replication

Both halves of the window (split 2024-03-15). A candidate must beat the
control in both.

## The bar to ship

A candidate ships only if it beats the control on total return over the whole
window **and** in both halves **and** exceeds the 95th percentile of its
random-entry null. Otherwise nothing ships, and the failure is filed with what
would drain it.

## Output

`artifacts/ch4_uf/ch2_holding_length_measurement_20260919.json` plus a result
section here, committed. Failures are filed exactly as wins are.
