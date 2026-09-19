# Universe or picking? — book-level null declaration (2026-09-19)

Declared BEFORE any result, and referenced from the book simulation's result
section as the decisive follow-up.

## The question

The gate's book trails a random-entry book drawn from every liquid name, yet
per position it beat a null drawn from its **own** names. **Is the deficit in
the family of stocks the gate favours, or in its picking within that family?**

## Runs — identical book, three references

The book is unchanged: $100,000, $2,500 slices, whole shares, cash-limited,
the live exit law, day by day, both cost settings (0 and 10 bp), the full
window and both halves.

- **gate** — the live one-position-per-stock book (already measured; re-run
  here so every number in this document comes from one execution).
- **null_own_universe** — the same book, but each day's entries drawn at
  random from the **1,065 tickers the gate ever signalled**, restricted to
  those passing the floors that day. Universe held, picking removed.
  **50 seeds.**
- **null_broad_universe** — the same book drawing from every liquid name that
  day, as already run. **50 seeds.** Repeated here for a like-for-like table.
- **spy_hold** — $100,000 into SPY at the first session of the window, held to
  the last. No trading, no costs.

## What each comparison settles

- gate versus **null_own_universe**: does the gate pick better than chance
  *inside its own family*? A book-level version of the per-position test.
- **null_own_universe** versus **null_broad_universe**: is the gate's family
  itself worse than the broad liquid market?
- everything versus **spy_hold**: the reference any of this has to beat to be
  worth running at all.

## Reported

Return, maximum drawdown, trades and win rate for every run, in every window,
at both cost settings.

## What this changes

Nothing by itself. It tells us where the deficit lives so the next decision is
made on evidence rather than on a preference.

## Output

`artifacts/ch4_uf/ch2_book_null_universe_20260919.json` plus a result section
here, committed.

---

## Result (2026-09-19) — the universe is fine; the picking is what loses

Gate universe: 1,065 tickers, a median of 879 eligible a day against 2,830 in
the broad pool. Port check: 2,000 tuples, 0 decision mismatches.

| window | cost | gate book | random **within the gate's own universe** | random over all liquid names | SPY held |
|---|---|---:|---:|---:|---:|
| full | 0 bp | **+3.7 %** | +17.1 % (p95 +38.3) | +13.2 % | **+68.5 %** |
| full | 10 bp | −0.3 % | +11.8 % (p95 +30.6) | +9.8 % | +68.5 % |
| first half | 0 bp | −5.1 % | −3.6 % (p95 +11.1) | −7.0 % | +12.8 % |
| first half | 10 bp | −5.8 % | −5.8 % (p95 +9.2) | −8.7 % | +12.8 % |
| second half | 0 bp | +6.3 % | +21.1 % (p95 +36.0) | +20.9 % | +49.4 % |
| second half | 10 bp | +5.3 % | +18.7 % (p95 +35.9) | +19.0 % | +49.4 % |

### What this settles

1. **The gate's universe is not the problem.** Picking at random *inside the
   gate's own 1,065 names* returned +17.1 %, slightly **better** than random
   over every liquid name (+13.2 %). The family the gate looks at is fine.
2. **The picking inside that family is the problem.** The gate's book made
   +3.7 % where random choices from its own names, on the same days and in the
   same numbers, made +17.1 %. Same universe, same cadence, same capital, same
   exits — only the choice of names differs.
3. **Every version of this book trails simply holding SPY** (+68.5 % over the
   window; +49.4 % in the second half alone). A book that deploys on signal
   days into $2,500 slices and runs these exits is far behind the index even
   when it picks at random.

### Against the per-position result, honestly

The per-position measurement found the gate beating random timing inside its
own names (+1.70 % against +0.82 % at a 30-session hold). At book level the
sign reverses. The exits are not the cause — they cost 0.11–0.35 points per
position. What the book adds beyond the per-position test is **capital
rationing**: on a day with more signals than cash, the book takes the highest
`accumulate_basin` names first, while the null takes the same number at
random. If the gate's own strength ranking is inverted — high basin scoring
worse — that alone flips a positive per-position edge into a losing book.

### The next measurement, declared and running

Forward returns by `accumulate_basin` decile, and the taken-versus-skipped
split on days when cash rationed the book. If the top decile underperforms the
bottom, the door is choosing the worst of its own candidates and the ranking
is the defect — not the physics, not the exits.
