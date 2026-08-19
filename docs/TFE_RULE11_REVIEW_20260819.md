# Rule 11 — first adversarial code review and fix pass (2026-08-19)

Rule 11 (filed 2026-08-18): physics-carrying code gets an adversarial
code review before it runs with money. This is the record of the first
one: eight independent review angles over the four files written the
night of 08-18/08-19 (`ch3_reveal_fade.py`, `ch6_fast_harvest.py`,
`ch_premarket_cut.py`, `ch_entry_reading.py`), roughly 36 raw findings,
deduplicated and fixed in one consolidated pass before today's close.

Joseph's words that created this rule: "you need to do code reviews so
you don't lie to yourself and casually replace the physics details with
shorthand/lazy coding." The review validated the rule immediately — one
night's work carried all of the following.

## Money-path defects (wrong dollars or wrong trades)

1. **CH3 day budget only counted rehearsal entries.** `day_spent`
   was incremented in the dry-run branch only; a live day could exceed
   the $30k/day exposure cap without limit. Fixed: incremented on the
   live path too.
2. **CH3 charged every close at the worst borrow tier.** The stored
   find never carried `normal_day_dollars`, so `carry_costs` saw 0 and
   billed 50%/yr + 0.5% slip on every name, liquid or not. Fixed: the
   find records its liquidity class at entry.
3. **Carry was billed in sessions, not calendar days.** A short held
   over a weekend pays three days of borrow, not one. Both engines now
   share `ch_desk.calendar_days` (raises loudly on garbage dates —
   CH6's old code silently defaulted to 1 day on any parse error).
4. **Two diverging copies of the fee schedule.** `carry_costs` existed
   verbatim in both engines and was about to be pasted a third time
   into the premarket cut. Now one copy in `tools/ch_desk.py`; both
   engines and the premarket cut import it (verified same object at
   runtime).
5. **Premarket cut could book a long winner as a short loss.** The CH3
   pass iterated every OPEN find in the shared log with no engine or
   side filter, applying short-only arithmetic. Other engine families
   with side=+1 exist in that log. Fixed: filtered to this engine
   family's open shorts only.
6. **Premarket cut skipped carry costs entirely.** A cut booked through
   it settled at different dollars than the engine's own law. Fixed:
   identical accounting, shared functions.

## Protection-path defects (the guard rails themselves)

7. **Premarket cut wrote the books non-atomically while the CH6 loop
   was live.** Raw `json.dump` over files the polling loop also writes:
   a race could resurrect a cut position after its cash was already
   credited (double-count), or a kill mid-write could truncate a book.
   Fixed: all writes go through each engine's atomic tmp+fsync+rename
   savers, plus a lock file so two premarket passes cannot overlap.
8. **Premarket cut silently skipped any symbol whose quote failed** —
   the exact position most likely to be halted or gapping is the one
   the protection would skip without a word. Fixed: one batched quote
   request, and every unquoted symbol is reported loudly as UNCHECKED.
9. **Premarket cut reason string broke the refutation law.** It wrote
   "ANOMALY-CUT premarket", which the exact-match refutation check
   ignores — a premarket-cut symbol could be re-shorted the same day.
   Fixed: reason is exactly "ANOMALY-CUT", detail in a note field.
10. **Refutation reset scanned only 25 sessions of history.** A cut
    older than 25 sessions whose reset close fell outside the window
    was refused forever. Both engines now hand the law the symbol's
    full stored history whenever a cut exists.

## Entry-gate defects (the Rules misapplied)

11. **The fillability law was ~9x too strict.** The "normal day's
    dollars" summed only the LAST 45-minute bar of each day (~1/9 of a
    day). The 1%-of-normal-day law and the no-borrow/fillability
    thresholds all measured against this undercount. Fixed: a day is
    the sum of its bars.
12. **The shell ban was blind before 2021.** Bars were fetched from
    2021-01-01, so a lifetime peak before then (the TNON class) was
    invisible to the peak/price crush ratio, and "life years" were
    amputated. Fixed: whole life fetched from 2000.
13. **MIN_READINGS contradicted the declared law.** The docstring said
    fail-closed under ~6 months of readings; the constant (320) allowed
    ~6 weeks. Now 1100 (~6 months at 9 readings/day).
14. **The gate cache re-downloaded every symbol's entire history every
    day and never evicted.** Cache was keyed per symbol per DAY. Now
    one whole-life cache per symbol, topped up incrementally; stale
    per-day files are removed.
15. **Every gate call re-read symbols already read today.** Verdicts
    are physics, not channel state; today's filed sheets (either
    channel) are now reused, and only fail-closed errors retry. Sheet
    writes are atomic.

## Structure defects (lazy shorthand, dead weight)

16. Import fragility: bare imports that only worked script-style (CH6's
    in-function `from ch_entry_reading import gate` would crash at
    runtime on the first day with eligible events under package-style
    invocation). All cross-module imports are now package-style
    (`tools.`) with one path insert.
17. Dead code removed: `covered_universe` attrs written and never read
    (both engines), the retired `MAX_NEW_PER_DAY=10_000` cap, a
    duplicated halt-file check, the `sync` tombstone command, an unused
    loop variable, module-level `_HERD_COVERAGE` globals standing in
    for locals.

## Verification

- All four files parse; both engines import package-style and
  script-style; verified at runtime that both bind the SAME
  `ch_desk.carry_costs`/`calendar_days` objects.
- Desk math spot-checked (tier boundaries, calendar day counts,
  garbage-date raise).
- Batched premarket quote call verified live against Alpaca.
- CH3 dry run with the rebuilt gate: whole-life caches build, verdict
  sheets file, no book mutation.

## Deferred (filed, not forgotten)

- The candidate scanner (`candidate_events` / `qualifying_events`),
  market loader, and herd readers remain near-verbatim twins across the
  two engines. They should move to one shared module; deferred because
  unifying them hours before a close pass risks more than it saves
  today.
- A `settle_find` helper in CH3 so the engine and the premarket cut
  share one close-accounting function (they are line-identical today,
  synchronized by hand).
- Desk floor item 7 (sector crowding cap) and item 8 (news) remain
  unbuilt/partial, as recorded in the desk floor doc.
