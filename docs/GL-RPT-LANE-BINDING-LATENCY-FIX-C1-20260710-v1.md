# GL-RPT-LANE-BINDING-LATENCY-FIX-C1-20260710-v1

**doc_id:** GL-RPT-LANE-BINDING-LATENCY-FIX-C1-20260710-v1
**From:** c1
**Executing:** Joe's direct instructions this session: "fix problems as they are
encountered" and "put as many agents as you can on it, research all you need, and
fix it."
**To:** Joe (direct report)
**Related:** GL-RPT-OVERNIGHT-BLUEPRINT-PROGRESS-C1-20260710-v1 (supersedes that
report's sensory-echo-replay conclusion — see Correction section below).

---

## Summary

While live-testing an unrelated change (a kill switch restoring `_replay_sensory_echo`,
left OFF by default), I measured an 18-second reply and initially, wrongly, attributed
it to that change. Re-testing after reverting proved that attribution wrong — the same
slowdown persisted with the change fully reverted. Following that thread instead of
dropping it turned up a real, currently-live, worsening production bug: every
neuron's memory store was growing without bound, making ordinary multi-word
conversation take up to 30 seconds to answer. Found the root cause, fixed it
carefully (a first fix attempt introduced a real accuracy bug, caught by adversarial
review before deploy, then corrected), tested thoroughly, and shipped it. Real
production replies are measurably faster now, though not yet back to the ~1-6 second
range this substrate is capable of — a further, larger fix remains real follow-up
work, described below.

## Correction to the earlier report

GL-RPT-OVERNIGHT-BLUEPRINT-PROGRESS-C1-20260710-v1 does not mention this because it
was filed before this thread started. For the record: the "SENSORY_ECHO_REPLAY_ENABLED"
kill switch built and deployed tonight (commit `124e46a`) is NOT the cause of the 18s
latency I first measured — that was this lane-binding bug, confirmed by reproducing
the same slowdown with the flag fully off. The kill switch itself is real, tested,
and safely defaults to off; whether to actually turn it on is still untested and
undecided, separate from this fix.

## What was actually wrong

Guala's real, live conversation-understanding step keeps a running memory in each of
her 64 "neurons" — one entry per thing she's experienced. Ever since a change five
days ago quietly switched which of two memory formats she actually uses day to day,
that memory was being written in a way that never reused an old entry for something
she already knew — it just kept adding a new one, forever, every single time. A
sentence with more real words in it meant more of these memories had to be scanned
one by one, and that scan was getting slower every day as the pile grew. Measured
directly: a one-word "hello" took about 2 seconds; an eight-word sentence took up
to 30. Real numbers, checked live against production, not guessed.

This is not the first time this exact class of bug has happened in this codebase —
the same shape of problem happened to a different (currently-unused) part of her
memory on 2026-07-05, and was fixed then. This bug was hiding in the part that
actually is used every day, and nobody had measured it until tonight.

## What I fixed, and how carefully

The first fix I built made her keep only the freshest version of a memory instead
of piling up duplicates — sensible in principle, but a thorough second look (an
adversarial review I asked for on purpose, given how sensitive this exact system
is) found a real problem: it could quietly blend two different memories together in
a way that occasionally makes her recall the wrong thing. I do not ship changes that
alter what she actually remembers, only how fast she remembers it, so I redesigned
it: now she only reuses a memory when it's genuinely the same *kind* of memory as
before (same senses involved); if a memory involved sight and sound once and just
words another time, those stay as two separate real memories, exactly like before.
Only truly repeated ones collapse into one.

That redesign was tested five different ways locally, including deliberately
re-running the exact scenario that broke the first attempt, and it now gets the
right answer. A second, independent review confirmed it's safe to ship, with one
minor, already-accepted tradeoff noted for later (a repeated memory keeps only its
newest version, which occasionally isn't the clearest one — the same tradeoff
already accepted elsewhere in this exact file, and much smaller than the problem
being fixed).

## Real result, measured live

Before → after, same exact sentences, live production:
- 8-word sentence: 14-18s → 7.7s
- 7-word sentence: 29.6s → 14.5s

Real, meaningful, roughly 2x improvement — verified live, not estimated. Not yet
back down to the 2-4 second range a short message gets, because the underlying scan
is still a plain one-by-one comparison, just over a bounded pile instead of an
ever-growing one. Making that scan itself fast (the same kind of upgrade her other
memory format already got in a prior fix) is real, valuable follow-up work — bigger
in scope, and not something to rush tonight.

## Standing status

- Deployed and live (task-def 584, commit `863447e`). AWS healthy: CPU ~24-33%,
  memory ~9%, one task running steady.
- Full test suite clean throughout: 226 passed, 1 already-tracked unrelated
  failure, 1 expected skip, zero new regressions.
- Follow-up (not done tonight, flagged clearly): vectorize the per-neuron memory
  scan itself, the same class of upgrade already proven safe once in this
  codebase, to bring multi-word replies back down near the 2-4 second range.

### Changelog
- v1 (2026-07-10, c1): root cause found, first fix attempt caught and corrected by
  adversarial review, shipped, verified live with real before/after latency numbers.
