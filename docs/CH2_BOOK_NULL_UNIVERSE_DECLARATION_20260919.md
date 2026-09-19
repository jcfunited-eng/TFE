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
