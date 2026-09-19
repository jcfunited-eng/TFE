# CH2 winner-side exit — measurement declaration (2026-09-19)

Declared BEFORE any result is computed (kernel-use doctrine: declare-then-run;
honest-timing rule 4: constants declared once, no sweeps). Provenance:
Joseph's order — replace what the nightly per-ticker reading gave, server-side,
at zero running cost, measured before it ships.

## The question

The reading's loser verdict (DEAD) is already replaced deterministically by the
dead clock (live since 2026-09-15). Its winner verdict (DRIVE_DYING — bank a
winner whose fueling structure is failing) has no replacement: nothing sells a
position above entry below a +20 % peak.

**Does any deterministic winner-side exit, computed from the kernel lanes the
server already holds, beat simply holding under the current law?**

## Population (fixed before measurement)

- Source of entries: `runtime_decisions_history` — the production kernel tuple
  per ticker per session, 2021-09-01 → 2026-09-19 (5.27 M rows, 12,060
  tickers). This is five years, not a decade: the lanes do not exist earlier.
- Entry rule: the live CH2 gate applied to each session's tuple —
  `computeV3Basin` (ported verbatim from `web/scripts/execution/v3_basin.mjs`,
  port verified against node on ≥ 1,000 real tuples, exact match required)
  with `decision_argmax == "Accumulate"`, `accumulate_basin >= 0.15`,
  `break_agreement < 0.20`, `bar_count > 20`.
- Omitted from the historical gate, and stated: the $500 M market-cap floor
  (no historical capitalisation series) and the sector epoch-pressure block.
  Both widen the population; neither is applied to control or candidate, so
  the comparison stays like-for-like.
- One position per ticker at a time; a new entry only after the prior one
  closes. No cooling-off (it is an entry rule, not an exit rule).

## Timing (honest-timing rules 1 and 2)

- A session's tuple is knowable at that session's close. Entry fills at the
  **next session's close**; no fill is priced before its fact is knowable.
- Every exit decision is made on a closed session and fills at the **next
  session's close**, except the two price stops below, which fill at their
  trigger price.
- Prices: `ch4_live_store.parquet` (15.8 M daily closes, 2016 → 2026-09).
  Closes only — no intraday range exists in the store. Stated consequence:
  the −20 % brake and the +20 % ratchet are evaluated on closes for both
  control and candidates, so both sides carry the same approximation.
- No costs, no slippage modeled.

## Control (what the book does today)

Hold from entry until the first of:
1. **Dead clock** — more than 16 closed sessions at or below entry × 0.95
   with no close back above that line (live rule, verbatim).
2. **90-day wall** — 90 calendar days.
3. **−20 % brake** — a close at or below entry × 0.80.
4. **+20 % ratchet** — after a peak close ≥ entry × 1.20, a close at or below
   entry + (peak − entry) × 2/3.
5. End of the measurement window (marked to the last close).

## Candidates (each measured alone — no stacking, no checklist)

Each fires only while the position is **above entry**, and sells at the next
close. Constants declared here, once:

- **A — support sag**: `S_UF` below its own trailing 20-session median on 5
  consecutive sessions.
- **B — fuel drain**: `B_k` lower than its value 10 sessions earlier on 5
  consecutive sessions.
- **C — direction loss**: `D_k != 1` on 5 consecutive sessions.
- **D — basin break**: `break_agreement >= 0.20` (the exit demoted on
  2026-08-25; already computed, measured here rather than assumed).

Stacked combinations are deliberately NOT measured: a per-stock condition
checklist is the condemned pattern (`tfe-condemned-ideas`, the spring triad).

## Null test (honest-timing rule 3)

For every candidate, a duration-matched random exit: for each position the
candidate closed after *n* sessions, close a copy of that same position after
*n* sessions regardless of structure. A candidate whose advantage over the
control is matched by its own random null has found nothing.

## Replication (honest-timing rule 6)

The window is split at its midpoint (2021-09-01 → 2024-03-15, 2024-03-15 →
2026-09-19). A candidate must beat the control in **both** halves.

## The bar to ship (declared before results)

A candidate ships only if, over the whole window and in both halves, it beats
the control on total return across identical entries, **and** its edge exceeds
its duration-matched random null. Otherwise nothing ships and the measured
failure is filed, with what would drain it.

## Output

`artifacts/ch4_uf/ch2_winner_exit_measurement_20260919.json` plus an addendum
here, committed. Failures are filed exactly as wins are.
