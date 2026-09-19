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

## Addendum — the basin ranking carries no information, and a precision correction

**The strength score is uninformative, not inverted.** Forward returns of all
10,612 signals bucketed by the gate's own `accumulate_basin` decile
(`tools/ch2_basin_rank_test.py`, `artifacts/ch4_uf/ch2_basin_rank_20260919.json`):

| hold | bottom decile | top decile | top − bottom | rank correlation |
|---|---:|---:|---:|---:|
| 30 sessions | +2.19 % | +1.17 % | −1.03 | **−0.008** |
| 60 sessions | +4.04 % | −13.82 % (n=29 only) | −17.86 | **−0.037** |

The deciles do not order: D3 is the best at both holds (+4.27 %, +6.04 %), D9
among the worst, and the rank correlation between the gate's own score and the
outcome is effectively zero. The 60-session top decile holds just 29 positions
— the highest-scoring signals cluster at the end of the window where 60
forward sessions do not exist — so no weight is put on its −13.82 %.

Consequence: ranking candidates by `accumulate_basin` when cash is short is
**equivalent to picking arbitrarily**. It is not the mechanism behind the
book's shortfall, and my hypothesis that the ranking was inverted is not
supported.

**Precision correction to what I told Joseph.** I said the gate's picks "lose
to random". Against the full spread of the own-universe null:

| window | cost | gate | null p05 | null mean | null p95 |
|---|---|---:|---:|---:|---:|
| full | 0 bp | +3.7 % | −1.5 % | +17.1 % | +38.3 % |
| full | 10 bp | −0.3 % | −1.5 % | +11.8 % | +30.6 % |
| first half | 0 bp | −5.1 % | −14.1 % | −3.6 % | +11.1 % |
| second half | 0 bp | +6.3 % | **+10.5 %** | +21.1 % | +36.0 % |
| second half | 10 bp | +5.3 % | **+6.1 %** | +18.7 % | +35.9 % |

Over the full window the gate's book sits in the **bottom tail of the random
distribution but inside it** — below the middle, above the 5th percentile. In
the **second half it falls below the 5th percentile**, which is the only
window where it is genuinely worse than chance. In the first half it is about
at the random mean. "Below the middle of random everywhere, outside the bottom
edge of random in the recent half" is the accurate statement; "loses to
random" overstated the full-window case.

### The coherent picture across all measurements

1. **Timing inside a name**: the gate beats random dates in the same stocks
   (+1.70 % against +0.82 % per position at 30 sessions).
2. **Choosing among the day's names**: it does worse than other eligible names
   from its own universe, decisively so in the recent half.
3. **Its strength score** adds nothing to that choice (rank correlation ≈ 0).
4. **The exits** cost 0.11–0.35 points per position — near neutral.
5. **The universe** is fine; random inside it beats random outside it.
6. **Everything** trails SPY held (+68.5 %) by a wide margin.

Nulls 1 and 2 are different questions — random *dates* in the same stock
versus random *stocks* on the same date — and the gate answers them
differently. That is the finding, and it is not contradictory.
