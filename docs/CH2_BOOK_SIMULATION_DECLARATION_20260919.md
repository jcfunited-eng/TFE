# CH2 book simulation — repeats versus one per stock (declaration 2026-09-19)

Declared BEFORE any result. Provenance: Joseph's word ("try it") after the
one-at-a-time measurement showed the cost is in discarded repeat signals, and
after I said the claim needs a capacity-bounded book rather than per-position
averages.

## The question

**With real capital limits and the live exit law, does allowing more than one
position in a stock beat the live rule of one position per stock at a time?**

## The book

- **$100,000**, fresh at the start of each measured window.
- **$2,500 per position**, whole shares only, remainder stays in cash.
- A position is opened only if cash covers it; total invested never exceeds
  the starting capital. No margin, no shorting.
- Entries are decided on the session after the signal and filled at that
  session's close; exits fill as the live law fills them (price stops at the
  trigger close, rule exits at the next close). Closes only.
- When a day offers more signals than cash, they are taken in **descending
  `accumulate_basin`** — the gate's own strength number. The same priority is
  used in every run, so it cannot favour one.
- No day-of-week block, no cooling-off: those apply identically to both runs
  and are not the variable under test.

## Exits

The live law, verbatim and identical in both runs: −20 % brake, dead clock
(>16 closed sessions at or below entry × 0.95 with no close back above),
+20 % ratchet floor (give back a third of the peak gain), 90-day wall.

## The two runs — one difference only

- **one_per_stock** — the live door: no new position in a stock that already
  has one open.
- **repeats_3** — up to **three** simultaneous positions in the same stock.
  Three is declared here, once; no other value is measured.

## Null

A random-entry book: the same cadence, sizing, cash rules and exit law, but
each day's entries drawn at random from the stocks passing the liquidity and
price floors that day instead of from the gate. **50 seeds.** If both real
runs sit inside this spread, the book's outcome is not about the gate.

## Costs

Reported twice: with no costs, and with **10 basis points round trip** per
position as a slippage allowance. The runs trade different amounts, so cost
sensitivity is part of the answer, not a footnote.

## Windows

The whole window (2021-09-01 → 2026-09-19) and each half separately
(split 2024-03-15), each starting fresh at $100,000.

## Reported

Final equity, total return, maximum drawdown on the equity curve, positions
taken, win rate, and the exit-reason mix.

## The bar

`repeats_3` is worth proposing to Joseph only if it beats `one_per_stock` in
the whole window **and** both halves, under **both** cost settings, **and**
both runs clear the 95th percentile of the random-entry book. Anything less is
reported as measured and nothing is proposed.

## What this changes

Nothing, by itself. It is a measurement. Any change to the live door needs
Joseph's word.

## Output

`artifacts/ch4_uf/ch2_book_simulation_20260919.json` plus a result section
here, committed. Either answer is filed the same way.
