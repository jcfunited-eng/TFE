# GL-HANDOFF-C1-20260710-v1

**doc_id:** GL-HANDOFF-C1-20260710-v1
**From:** c1 (this session)
**To:** whoever picks up next (Codex/c1 session already deep in
GL-RPT-SINGLE-WORD-UNAWARE-ROOTCAUSE-C1-20260710-v1.md, or Joe/Eve)
**Why:** Joe asked directly whether a handoff was needed. Yes — another
session already has a deeper, cross-validated picture of the current
real problem (combining a 12-agent code/log investigation with wC's
live telemetry) than I do, I've caught two real mistakes in my own work
in a short stretch, and this repo's `.git` is shared across concurrent
sessions — continuing to build in parallel risks collision, not help.

---

## What this session actually shipped tonight (in order), current status

1. **Keyhole wiring extension** (`2d83ca4`) — extends the emission
   settling chain from 2 links to 5. **Flagged by the other session as a
   real, credible problem**: the fixed 1.5s settling budget was never
   raised to match, and real live turns may now hit that ceiling and
   fall back to a single generic word more often than before. Tested
   against fixtures only, never against real live timing — that gap is
   real and is on me. Live now (task-def 585 and everything after it).
   **Needs the other session's item #3a (revert or re-time) — do not
   assume this is fine.**

2. **Priority-replay dream sampling + sleep Reorganize** (`b1d0eca`,
   `70fb7e3` + fixes) — real, tested, adversarially reviewed twice (a
   real regression was found and fixed before deploy each time). No
   flags raised against these by the other session. Believed sound.

3. **Sensory-echo-replay kill switch** (`124e46a`) — restores an old,
   deliberately-disabled mechanism behind a flag, **default OFF**. A
   live trial run of turning it ON showed an 18s reply — I initially,
   wrongly, blamed this flag. Re-testing with the flag back OFF showed
   the same slowdown, proving the flag wasn't the cause. **Never
   confirmed safe, never turned on. Leave OFF.**

4. **Lane-binding latency fix** (`863447e`, corrected report in
   `GL-RPT-LANE-BINDING-LATENCY-FIX-C1-20260710-v1.md`) — **the other
   session found what I should have found myself**: production's real
   organism construction (`gualaloom_v5_engine.py:2122`,
   `_Embryo(..., observable="event_count")`) explicitly overrides the
   default I checked (`embryo.py:132`'s `observable="resonant_spectral"`
   default). I verified the DEFAULT, never checked the actual live
   constructor call for an override. Production almost certainly uses
   the FLAT-VECTOR memory path (`BindingAtlas.cells`/`_concept_to_chi`,
   already fixed once in 2026-07-05's GL-FIX-RECALL-MATRIX-MIRROR), not
   the lane path (`_lane_bindings`) I spent hours fixing tonight. The
   code change itself is real, safe, and correct for the path it
   touches — it is just very likely inert in production. The live
   speedup I measured and reported (14-18s→7.7s, 29.6s→14.5s) was most
   likely the redeploy itself (clearing worker backlog / resetting
   locks), not this fix. **Do not rely on this fix for the latency
   problem. The real cause is still open** — the other session's
   strongest lead is `read_sentence()` holding one process-wide lock for
   a whole sentence, shared with camera/mic frame handling and autosave
   (measured 12-48s real stalls).

5. **Blueprint items** (`79e0233`) — researched the real current state
   of all 7 items Joe named (imagination, reflection, deliberation,
   play, aware/intro gates, organ-influence, curriculum feeders) rather
   than trusting the stale 07-04/05 audit:
   - **Deliberation and curriculum feeders were already fixed and live**
     (curriculum since `cac6684`, confirmed via real boot logs;
     deliberation's coordinator is wired and firing-capable, just hadn't
     accumulated enough uninterrupted runtime — restarts keep resetting
     it, which the other session's findings make even more likely given
     how much is currently stalling/timing out).
   - **Organ-influence-on-speech**: attempted a dead-code cleanup, found
     a real near-miss — the poll thread I almost deleted turned out to
     be genuinely live (my first CloudWatch query had a quoting bug that
     produced a false negative; a corrected query found it running every
     boot). Reverted before it went anywhere. Left untouched — it's
     real, running, and harmless (the :8090 target it polls was
     permanently deleted 2026-06-25, so it always fails silently; no
     actual effect either way). Real organ-influence on speech today
     comes from a different, already-live mechanism
     (`_recognition_from_organism`).
   - **Reflection** (`_form_reflection`) — real, tested, write-only, not
     wired to speech. An adversarial review caught and I fixed a real
     KeyError risk in its restore-path handling before shipping.
   - **Imagination** (`_imagination_candidates`) — surfaces
     `reorganize_hypothesis` entries as capped, damped emission
     candidates. Adversarially reviewed clean (full chain-of-custody
     traced to real data, single candidate path confirmed, cap and
     grounding gate verified, weight confirmed to matter in all three
     live selection paths).
   - **Play and aware/intro gates**: real, named blockers, not hedging.
     Play needs Joe's own prior-ruled design-packet approval before any
     code (his standing rule against fake-alive shims). Aware/intro
     gates live on a structurally separate voice path (`V7Session`) that
     real conversation never reaches — wiring it in without an ownership
     decision risks a second competing voice, banned by this project's
     "one brain, one voice" rule. Reported to Joe directly; no code
     written for either.

## Two real mistakes this session made, corrected before real damage

- **Organ-influence cleanup**: nearly deleted a live function based on a
  CloudWatch filter-pattern quoting bug that produced a false "never
  runs" reading. Caught before commit by testing with a corrected query
  syntax. Nothing shipped.
- **Lane-binding fix root cause**: checked a function's default
  parameter instead of its actual call site, missing an explicit
  override. The other session's independent investigation caught this
  before I did. Documented above; not silently left for someone else to
  rediscover.

## What NOT to duplicate

The other session's `GL-RPT-SINGLE-WORD-UNAWARE-ROOTCAUSE-C1-20260710-v1.md`
is the current, authoritative, most-complete picture of the live
problem — five ranked causes, cross-validated against wC's independent
live telemetry. Its recommended build-tonight list (presence-timeout
fix, cascade-timing fix for the keyhole extension, section-cap
retirement) is real, well-scoped work already in motion elsewhere. I am
stepping back from further hot-zone changes rather than risk colliding
with it on the same shared `.git`.

## Live state as of this handoff

Task-def 585, commit `6d2d581` (includes this session's reflection/
imagination work plus the other session's two docs-only commits). AWS
CPU/memory healthy throughout tonight (checked after every deploy). Full
test suite clean at every checkpoint (226 passed, 1 known pre-existing
failure, 1 expected xfail). The live conversational latency/quality
problem the other session is root-causing is real, confirmed, and still
open — not fixed by anything in this session's own lane-binding work.

### Changelog
- v1 (2026-07-10, c1): handoff filed per Joe's direct question, after
  finding this session's own lane-binding fix likely targets an unused
  code path and its keyhole-wiring commit is flagged as a real
  contributing cause of the current single-word/timeout symptom.
