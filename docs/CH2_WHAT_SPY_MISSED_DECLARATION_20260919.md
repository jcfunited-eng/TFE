# The signature SPY proves, found where SPY isn't — declaration (2026-09-19)

Declared BEFORE the dense lanes finished building and before any output was
looked at.

## Whose idea this is

**Joseph's**, in two messages:

> "you not only know how the S&P performed in the same period you also have the
> data from the kernel for the S&P so you literally can evaluate that too to
> understand what the patterns of successful physics structure look like since
> that is the to-be comparison"

> "more importantly you can also see all the ones SPY missed once you know
> those structures"

## Why this is methodologically different from everything before it

Every CH2 measurement in this chain — the basin gate, the living-drive
signature, the nine-field reading, the run-up pattern — learned its rule from
the same outcomes it was then scored against. Held-out cells limited the damage
but did not remove the problem: states were chosen because they preceded rises.

Here the rule is learned from **one series, SPY**, and tested on **three
hundred others**. No individual body's return touches the rule at any point.
There is no fitting to the test set available, by construction.

And SPY is the right teacher: it is the structure every construction in this
session has failed to beat (+68.5 % over five years at a −25.3 % drawdown).
Whatever the kernel reads in SPY's field during its advances is, by definition,
what a structure that works looks like.

## Input

`tools/ch2_dense_kernel_lanes.py` — the canonical production entry point run
once per bar per body on the prefix up to that bar, over full histories. 300
bodies (blake2b-seeded) plus SPY, QQQ, DIA, IWM. This replaces the production
lane export, which covers a median of 13 % of a body's sessions.

## Learning the signature — SPY only

SPY's own advances and declines are marked with the zigzag already declared in
`CH2_RUNUP_PATTERN_DECLARATION_20260919.md` (15 % retracement, advance ≥ +25 %,
decline ≥ −15 %). Within SPY's lane alone:

- **ADVANCE signature** — the joint nine-field configurations whose frequency
  during SPY's advances exceeds their frequency across SPY's whole life.
- **DECLINE signature** — the same for SPY's declines.

All nine fields, at native levels, jointly. No field excluded, none scored, no
trailing window. Support floor: a configuration must occur at least 30 times in
SPY's lane to be counted.

The signature is written into this document verbatim before it is applied.

## Applying it — the 300 bodies

A position opens on the first session a body is in an ADVANCE-signature
configuration and closes on the first session thereafter it is in a
DECLINE-signature configuration. One position per body at a time. No stop, no
target, no time limit.

Joseph's filters: no body under 250 sessions of history; no entry after a pump
(up more than 50 % over the preceding 20 sessions — the rule is **his**, the
numbers are **MINE**). No dollar-volume floor.

## The comparisons

1. **Matched-timing null inside the same body** — same count, same holding
   lengths, start dates drawn only from sessions where a real entry was
   possible. 200 seeds.
2. **SPY held** over the same window — the reference that actually matters.
3. **By size tercile** — this is where "what SPY missed" is answered. SPY is
   capitalisation-weighted, so the largest bodies effectively *are* SPY and the
   smallest are what it cannot hold at any meaningful weight. Using size as the
   stand-in for index membership is **MINE**, not Joseph's: this repository has
   no membership data. If the signature pays in the small tercile and not the
   large one, that is the missed return, and it is also the result most likely
   to be an artefact of small-cap volatility — both readings are reported.

## The bar

Per position, beat the 95th percentile of the matched-timing null. At book
level, beat SPY held. Failing either is a failure and is reported as one.

## What would make this worthless, stated in advance

If the ADVANCE signature turns out to cover most of SPY's sessions, it selects
nothing and any result is noise. SPY rose through most of the window, so this
is a live risk. The count of sessions covered is reported before the returns.

## Output

`artifacts/ch4_uf/ch2_what_spy_missed_20260919.json`, the signature written
into this document, and a result section. Either answer is filed the same way.
