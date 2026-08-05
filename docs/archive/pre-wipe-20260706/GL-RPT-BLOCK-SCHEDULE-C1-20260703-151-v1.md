> **SUPERSEDED — DO NOT TREAT AS CURRENT TRUTH.**
> This document describes substrate state as of pre-wipe (2026-07-06
> wipe operation, GL-RPT-SUBSTRATE-WIPE-INCIDENT-C1-20260706-v1).
> The substrate described here no longer exists. Preserved as
> historical record only.
> For current substrate state, run the harness against production.

---

# GL-RPT-BLOCK-SCHEDULE-C1-20260703-151-v1

doc_id: GL-RPT-BLOCK-SCHEDULE-C1-20260703-151-v1
From: c1b | To: Eve | Date: 2026-07-03
Responds to: GL-CMD-BLOCK-SCHEDULE-EVE-20260703-151-v1
Deployed as part of Deploy 4, SHA 5376204, task:457.

---

## FAILURES FIRST

### The gate I built is correctly constructed and matches your CMD's description
### almost exactly — but post-deploy verification shows the code it gates is
### unreachable in the deployed architecture. It is not suppressing anything live.

**What I found and built against**: `CurriculumScheduler` (`loom_model/curriculum_scheduler.py:58`),
instantiated once at `substrate_runner.py:903` inside `boot_substrate()`, feeding
book chunks (`chunk_size=30`, `interval_sec=120` — both match the deployed
`CURRICULUM_CHUNK_SIZE`/`CURRICULUM_INTERVAL_SEC` env values exactly) through a tight,
unthrottled per-sentence loop in `_curriculum_feed_chunk` (`substrate_runner.py:308`),
with world-feed (`_world_feed_once`, `:455`) and lookup (`_lookup_once`, `:399`)
interleaved every `STUDY_INTERLEAVE_EVERY=2` cycles. Every env var involved
(`CURRICULUM_CHUNK_SIZE=30`, `CURRICULUM_INTERVAL_SEC=120`, `STUDY_INTERLEAVE_EVERY=2`,
`WORLD_FEEDS=1`, `LOOKUP_AUTONOMOUS=1`) matched the deploy script precisely — this read
like exactly the flood mechanism your CMD described. I gated all three call sites
(§8 duty-cycle rotation, QUIET/EXPERIENCE suppression, scaffold-intake rate cap,
`block_intake_ledger` telemetry) before writing a line of the fix itself (G-151-1).

**Then I checked whether any of it actually runs, post-deploy, and it doesn't.**
`boot_substrate()` (`substrate_runner.py:632`) — the only place `CurriculumScheduler`
is ever constructed anywhere in this codebase — **has zero callers**. Confirmed by
direct grep (`grep -n "boot_substrate()" dsf_ai_service/*.py` matches only its own `def`
line) and no `if __name__ == "__main__":` entry point either. The function that actually
runs at boot in the deployed single-process embedded architecture is
`_embedded_post_boot()` (`app.py:1296`), and it never touches `CurriculumScheduler` —
its own curriculum-related call is `_sr._start_curriculum_orchestrator()` (the
*different*, already-retired-by−109 external-subprocess mechanism, confirmed still
correctly disabled: `[curriculum] autostart disabled by env` in this boot's log).

**Live confirmation this boot (SHA 5376204, ~26 minutes of runtime at time of writing)**:
```
$ aws logs filter-log-events ... --filter-pattern '?"worldfeed" ?"lookup" ?"block_intake"'
(zero matches)
```
Zero `worldfeed`, `lookup`, or `block_intake_ledger` occurrences anywhere in this boot's
log. Not suppressed by my gate — never invoked at all. The atlas-growth-rate evidence I
initially thought corroborated an active flood (`read_count`/"reads" climbing fast,
~85/sec) turned out to be a red herring: `read_count` is a *derived property*
(`gualaloom_v5_engine.py:1380`, "sum of atlas reinforcement events... not a counter") —
it reflects total reinforcement activity across sight, sound, and language bindings
combined, not sentence-feed volume specifically, and climbs fast during any active
mic+camera+conversation session regardless of curriculum activity.

**What this means**: I do not know, as of filing, where the flood you observed
("reads ~20/s during ATTENDING and EMITTING alike... atlas grew 7.3k→11.5k in ~2h") is
actually coming from. `CurriculumScheduler` is the mechanism that best matches your
description in every configured detail, but it is not reachable from the code path that
actually boots today. Possibilities I have not been able to rule out in the time
available: (a) your observation predates whatever change made `boot_substrate()`
unreachable, and the live flood has since stopped for an unrelated reason; (b) there is a
different, not-yet-identified feeder still active; (c) the growth you saw was legitimate
sight/sound/language reinforcement from real sensory activity, not scheduled machine
intake, misread as "flood." I am reporting this rather than quietly shipping a fix that
looks complete and isn't — this is exactly the "declare a switch's state from one of
three locations" mistake this project's ledger already has entries about, and I'd rather
be the one to catch it than the one who repeats it.

---

## WHAT I ACTUALLY BUILT (correct, inert until reachable)

`_current_block()` (§8 duty-cycle rotation: scaffold 25% / experience 25% / play 15% /
converse 15% / quiet 20%, `BLOCK_CYCLE_SEC` hot-readable, default 3600s) gates all three
identified feeder call sites: `_curriculum_feed_chunk` (`substrate_runner.py:308`,
serving both book chunks and `_world_feed_once`) and `_lookup_and_ground`
(`substrate_runner.py:420`). QUIET/EXPERIENCE blocks suppress entirely; other blocks
apply a sliding-window scaffold-intake rate cap (`SCAFFOLD_RATE_CAP_PER_MIN`, default
15/min). A `block_intake_ledger` event (block, planned vs. actual, capped) fires on every
feed attempt or suppression. None of this touches her own activity selection,
converse()/`/listen` input, or attending/emitting — exactly scoped to the three
machine-push call sites, per the CMD.

I have left this code in place rather than reverting it: it is correct, harmless, and
becomes active the moment `CurriculumScheduler` (or any equivalent scheduled feeder) is
ever wired into the live boot path again — which seems likely to happen regardless of
tonight's finding, given the intent behind 65-A and the B2 Experience Engine design this
CMD references.

---

## GATES

**G-151-1 — feeder inventory filed before code: PASS.** Delivered above and in the
commit message, file:line, before any fix code was written.

**G-151-2, G-151-3, G-151-4 — NOT MEASURED.** There is no live, reachable feed cycle to
observe being suppressed, rate-capped, or ledgered. Stating this plainly rather than
fabricating a quiet-block observation against a mechanism that never fires.

**G-151-5 — diff proves scope: PASS.** `git diff` for this dispatch: gating logic,
config constants, and telemetry only, in `_curriculum_feed_chunk` and
`_lookup_and_ground`. No cognition-path change, no content edits, nothing beyond what
the CMD specified — this holds regardless of the reachability finding above.

---

## RECOMMENDATION

Before iterating further on §8 enforcement: re-locate where the observed flood actually
originates, live, right now (a fresh trace during an active window, not a code read) — I
would not build another fix against inferred code without that confirmation this time.

---

## STATE

Deploy 4, SHA 5376204, task:457. Code shipped, correctly scoped, currently inert.
Familiarity id() diagnostic Eve's Deploy 4 vehicle summary named did not land on origin
before this deploy — proceeded without it after two checks, noting its absence here
rather than silently dropping it.

End report.
