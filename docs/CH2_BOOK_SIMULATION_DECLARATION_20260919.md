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

---

## Result (2026-09-19) — both books lose to a random-entry book of the same shape

601 signal days, 10,612 signals, 1,065 tickers. Null pool: a median of 2,830
liquid names a day. Port check: 2,000 tuples, 0 decision mismatches.

| window | cost | one per stock | repeats ≤3 | random-entry book (50 seeds) |
|---|---|---|---|---|
| full | 0 bp | +3.7 % (dd −40.2 %, 775 trades, 48.6 % wins) | +4.8 % (dd −37.6 %, 877) | mean **+13.9 %** (p05…p95 → +33.9 %) |
| full | 10 bp | −0.3 % | +3.9 % | mean +8.2 % (p95 +30.8 %) |
| first half | 0 bp | −5.1 % | −4.8 % | mean −7.6 % (p95 +7.0 %) |
| first half | 10 bp | −5.8 % | −4.8 % | mean −10.0 % (p95 +2.4 %) |
| second half | 0 bp | +6.3 % (dd −21.7 %) | +7.6 % | mean **+22.1 %** (p95 +43.2 %) |
| second half | 10 bp | +5.3 % | +0.4 % | mean +19.5 % (p95 +38.0 %) |

### Verdict against the declared bar: **repeats_3 does not pass, and neither book clears the null**

`repeats_3` beat `one_per_stock` in every window and at both cost settings —
the one part of the bar it met. But both books sit far below the random-entry
book over the full window and in the second half. The bar required clearing
the null. It is not met. Nothing is proposed.

### The finding, stated exactly

A book of the same shape that picks liquid stocks **at random** made roughly
three times what the gate's book made over five years (+13.9 % against
+3.7 %), and roughly three times again in the second half (+22.1 % against
+6.3 %). In the first half both real books beat the random mean slightly
(−5.1 % and −4.8 % against −7.6 %), which is the only window where the gate
helped.

### How this sits with the per-position result — a hypothesis, not a conclusion

The entry-gate measurement found the gate beating a null **drawn from the same
tickers it had already chosen**: it timed those names better than chance. This
book draws its null from every liquid name on the day. Both can be true at
once if the gate **times its own names well but chooses a family of names that
underperforms the broad liquid universe**. That is a hypothesis this run
cannot settle, because the two nulls differ in universe, not only in timing.

### The decisive follow-up, running now

The same book against two further nulls, declared before running: entries
drawn at random **from the gate's own 1,065 signal tickers** (timing removed,
universe held), and a plain **SPY buy-and-hold** with the same capital. If the
gate's book matches the first and both trail SPY, the deficit is in the
universe the gate favours, not in its picking. Filed as
`CH2_BOOK_NULL_UNIVERSE_DECLARATION_20260919.md`.

### Limits

Closes only; no dividends; the 10 bp allowance is a stand-in for real
slippage, not a measurement of it. The null book has no drawdown comparison
recorded. The gate's universe is narrower than the null's by construction,
which is exactly what the follow-up isolates.
