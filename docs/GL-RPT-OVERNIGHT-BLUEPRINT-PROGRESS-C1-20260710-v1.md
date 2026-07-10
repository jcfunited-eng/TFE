# GL-RPT-OVERNIGHT-BLUEPRINT-PROGRESS-C1-20260710-v1

**doc_id:** GL-RPT-OVERNIGHT-BLUEPRINT-PROGRESS-C1-20260710-v1
**From:** c1
**Executing:** Joe's standing overnight authorization ("get as many agents as you can
working on it and get it working in prod... give me all the approval requests you
need now") plus his direct instruction mid-session ("you will not only correct all
the items your outline but you will continue on with the blueprint work").
**To:** Joe (direct report)

---

## Summary

Three real features shipped and verified live tonight. Separately, a deep
investigation into "why doesn't the population ever grow" turned up that
Blueprint Phase 1 (event-driven substrate) and Phase 2 (lateral inhibition) are
much further along than the standing status notes suggested — not because
anything new was built there tonight, but because work from the last few days
(word-branch spike injection, the polarity-based inhibition fix, a fire-rate
circuit breaker) is durably live and holding, and the test suite was
misreporting it as broken. That's corrected now. Population growth itself
(Phase 6) is genuinely still flat — but that turns out to be a deliberate,
already-ratified design choice, not a bug.

## 1. Shipped and verified live

- **Keyhole wiring extension** (`2d83ca4`, task-def 580): extended the
  existing subject→verb→object excitatory chain to object→modifier→ground→
  intro, same band/strength already proven safe. Live, healthy.
- **Sleep Reorganize** (`70fb7e3`, task-def 581): a new mechanism where,
  during each dream cycle, she can form a tentative, low-confidence link
  between two things she really experienced recently if they're
  chi-proximate — distinct from the existing mechanism that only
  strengthens links she already has. Went through an adversarial multi-agent
  review before deploy, which found real issues (the mechanism would have
  silently done nothing in production due to a wrong wiring path; a
  duplicate-write bug; an undersized cleanup buffer; a case where the TTL
  cleanup could delete a genuinely-confirmed entry; and four places
  downstream where an unconfirmed guess could have leaked into something
  that looks like real memory or real speech). All fixed, all re-tested
  (11 local test scenarios), full suite clean, then deployed and verified
  live.
- **Test-suite cleanup** (`530ad6c`, `676987b`, no deploy needed — test-only):
  the suite has been reporting "5 known pre-existing failures" every run
  for days. Investigated all 5 directly instead of continuing to wave them
  off:
  - 3 were false alarms — tests whose assumptions went stale once real,
    deliberate production work shipped this week (see #2 below). Fixed the
    tests; they now pass.
  - 1 (population growth) is real but tests the wrong mechanism — see #2.
  - 1 (recall accuracy under noise) is a real, already-tracked, deep
    research gap in the loom_model recall system, unrelated to anything
    built this week. Left as-is, flagged clearly.
  Full suite is now 226 passed, 1 real known failure, 1 expected xfail —
  down from 5 unexplained failures.

AWS checked after every deploy tonight: CPU 24-33%, memory 6-8%, ECS stable
1/1 running, S3 backup storage under control (~7.2 GB current objects, well
below the 48 GB incident from earlier this week). No resource bloat, no
runaway processes.

## 2. Corrected understanding: Phase 1 / Phase 2 are further along than the record showed

Investigating the population-growth question required understanding the
current real state of the neuron/spike-bus system. Direct investigation (not
just reading old reports) found:

- **Word-branch spike injection is the live, durable production default**
  (`EVENT_DRIVEN_SUBSTRATE=1`, confirmed directly in the running task
  definition), not "explicitly not wired" as the standing summary said.
- **A real fix for the reverberating-cascade incident from a few days ago
  shipped and is holding**: outgoing spikes are now signed by each neuron's
  own polarity (roughly 20% inhibitory / 80% excitatory, from the seeding
  chemistry that already existed but was never consulted by the firing
  path). Verified directly: a fully-potentiated 64-neuron organism, kicked
  once, does NOT keep firing after external input stops.
- **A second, independent safety layer exists**: a per-neuron fire-rate
  circuit breaker, added the night after the polarity fix, that also
  independently stops runaway firing. This is why one of the "5 known
  failures" was failing — it's a negative-control test that disables the
  polarity fix on purpose to prove the test harness can still catch the
  bug, and the second safety layer was catching the runaway firing before
  the first one even had a chance to be tested. Fixed the test to isolate
  what it's actually supposed to measure; confirmed both mechanisms work,
  independently and together.

Net: Phase 1 (event-driven substrate) and Phase 2 (sparse activity via
lateral inhibition) are real, live, and have held under real production
conditions since being fixed — not the fragile, repeatedly-rolled-back state
the standing notes described. I want to be careful not to overclaim here:
this doesn't mean full Phase 1 is "done" in the blueprint's own sense
(membrane-state emission/recall replacing the older system is a much bigger
piece of that phase and hasn't been touched), but the exact thing that broke
three times this week is now fixed, tested, and has been running quietly in
production the whole time.

## 3. Population growth (Phase 6-adjacent): real, but not a bug

The live status shows population frozen at 64 neurons, 0 divisions, since
boot. Investigated directly rather than assuming it needs fixing:

- There are two separate, unrelated growth mechanisms in the code. One is
  demo-only and has no real production caller at all — confirmed by reading
  the actual call graph. The other is the real one production uses.
- The demo-only one can't be triggered by ordinary language content anyway —
  this was already measured and documented back in June: the math behind
  how words get encoded structurally forces the growth-trigger signal to
  near zero for language, which is correct behavior, not a bug.
- The real production growth mechanism is deliberately gated on real
  non-language sensory experience (camera/microphone/pictures) — a ratified
  design decision from a few days ago: growth should be funded by real
  experience, not free from reading or talking alone. During ordinary
  text-only conversation, that gate is correctly closed, which is why
  population stays flat. The one way around it (replaying previously-real
  sensory data for language-only words) was tried and deliberately turned
  back off after it caused a real 24-second-per-turn slowdown.

So: population not growing right now is working as designed, not broken.
Making it grow for real requires either giving her more real sensory
experience (pictures, sound) or a real performance fix to the disabled
fallback — both are product decisions, not something I judged safe to
decide alone overnight. Flagging clearly rather than guessing.

## What I did NOT touch tonight, and why

Local metabolism, full neuromodulation, true population-based seeding
(Phase 6 proper), and any further changes to neuron firing/STDP logic — all
of these sit in the same hot-zone that's had three real incidents this
week. Now that Phase 1/2 are confirmed stable, these are more approachable
than the standing notes suggested, but each still needs its own careful,
reviewed design before touching production. Given the scope of what already
came up tonight (a genuine correction to the team's understanding of where
Phase 1/2 actually stand, not just a small fix), I judged it more valuable
to get that right and clearly documented than to also start a new
hot-zone feature at the tail end of a long session.

## Files / commits

- `2d83ca4` — keyhole wiring extension
- `70fb7e3` — sleep Reorganize (initial)
- `530ad6c` — 3 stale test fixes (lateral inhibition negative-control,
  2x substrate-true import checks)
- `676987b` — test_t3_corpus_growth marked xfail with full citation trail
- Key files for the Phase 1/2 correction: `dsf_ai_service/loom_model/neuron.py`
  (`_fire`, `_check_fire_rate_breaker`), `dsf_ai_service/loom_model/tests/
  test_lateral_inhibition_cascade.py`, `dsf_ai_service/v4/gualaloom_v5_engine.py`
  (`_organism_worker_loop` word branch, `EVENT_DRIVEN_SUBSTRATE`)
- Key files for the population-growth finding: `dsf_ai_service/loom_model/
  embryo.py` (`_charge_and_fold`, `_experience_core`), `dsf_ai_service/loom_model/
  cluster.py` + `neuron.py` (`fold_check`/`process_folds`, demo-only path)

---

### Changelog
- v1 (2026-07-10, c1): initial report covering tonight's shipped work and
  the Phase 1/2/6 status correction.
