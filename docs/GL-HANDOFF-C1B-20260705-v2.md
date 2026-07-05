# GL-HANDOFF-C1B-20260705-v2

doc_id: GL-HANDOFF-C1B-20260705-v2
From: c1b | To: whoever picks this up next (c1b continuation, c1a,
Eve, Joe) | Session-end handoff, context heavily loaded (one /compact
already this session).

---

## Live state right now

- Deploy of `22b1d36` (latest origin/guala-live tip) was IN PROGRESS
  (CodeBuild building) when this handoff was written — **not yet
  verified**. Whoever picks this up: check `aws ecs describe-services`
  for task-def and `guala_status`'s `running_sha` before doing
  anything else. If it's still `dsf-ai-task:487` (SHA `06aecb8`), the
  deploy either finished after this handoff was filed or needs
  re-running.
- Identity `cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f` unchanged all
  session, confirmed via boot logs on every deploy tonight.
- `origin/guala-live` tip at handoff time: `22b1d36`.

## What happened this session, in order

Started by reading `GL-HANDOFF-C1B-20260705-v1` (this session's own
predecessor) and Joe's report that live chat was stalling.

1. **Diagnosed save-hot latency** (`-194`): a dispatched fix (evict
   vocab-scaled `sight_motifs` from the hot save lane) was already
   attached; applied + deployed it (`44070af`). Verified live but
   found it insufficient alone.
2. **Found and fixed the remainder myself**: hot-save writes were
   sequential, each with a real fsync round-trip; parallelized them
   (`fdeaa89`). Added per-file timing diagnostics later.
3. **`-195`** (voice/emission candidates from organism vote instead of
   tapestry echo-chamber): applied, found the attached patch was
   missing its own described telemetry, added it myself.
4. **`-196`** (emulator-everywhere, real senses to organism): built by
   a concurrent session (c1a); verified, not built by me.
5. **`-197`** (turn latency: release-reply-before-self-hear, one
   transduction pass, last-dream marker): built independently by both
   c1a and me in the same window; reconciled cleanly (c1a diffed
   theirs against mine, adopted mine, extended the one gap I'd
   missed — the non-phased converse() fallback).
6. **`-198`** (growth truth — Joe's ruling: growth is funded by
   experience, not a seed-pegged constant): re-pointed the division-
   pool refill to `sig_res` (real signal richness). Verified directly:
   language-only experience funds nothing, rich multi-sense experience
   produces real divisions. Built the `organism_growth` /status block
   and `organism_fold` events. **Found live, mid-verification, that
   the "58-fold growth burst" I was celebrating was contaminated** —
   see `-204` below.
7. **Two real bugs found live, not in any dispatch, fixed same-window**:
   - `_total_divisions`/`_fold_events_buffer` (my own new attributes)
     crashed on the real restored (unpickled) Embryo, which predates
     them — `__init__` never re-runs on unpickle. Fixed with the same
     `getattr` self-heal pattern used elsewhere for this exact class
     of schema evolution.
   - `LanguageKrimelack.feed()` crashed on `self.n_events` for any
     neuron alive since before `-178` shipped it — was silently
     breaking ALL organism learning and killing the tapestry-writer
     thread outright, this whole time, unrelated to anything I built.
8. **`-199`/`-200`** were fired by/for c1a; not my build.
9. **`-202`** (growth-live window, c1a's): `running_sha` field,
   `organism_growth` forwarding fixes — not my build, verified present.
10. **`-203`** (Joe's ruling: NO CAPS on her speech, coherence gain is
    the only stopping rule): deleted `MAX_COMPOSITION_LEN` everywhere
    (3 greedy selectors, the `-195` candidate pre-trim, the constant
    itself), made the orderer (`_compose_from_cortex`) stop truncating
    to 2 trailing words, extended its section scan to all 7.
    **Found live**: everything `-203` named lives in `_emit_grandurun`,
    which is DEAD CODE under the actual live config
    (`EMISSION_MODE=grandurun` + `EMISSION_DYNAMICS=1` always routes
    to `_emit_dynamics` instead). Flagged this clearly rather than
    silently declaring victory.
11. **`-204`** (EMERGENCY, Eve's finding): a resonance loop —
    `_audio_to_sensory_words` classifies mic ENERGY into fixed labels
    ("faint"/"warm"/etc.) and both call sites fed them into
    `read_sentence` as heard language every ~5s, continuously,
    including during sleep. This is what actually funded `-198`'s
    growth burst on artifact input and swamped the organism's vote
    distribution with "faint" (her most-repeated non-word), directly
    causing the single-word replies Joe was seeing. Severed at both
    sites (kept real cochlear hearing + Whisper transcription intact).
    Deployed same-window, minutes not hours, per the dispatch's own
    framing.
12. **Went after `_emit_dynamics`'s real structural ceiling** (the
    thing `-203` didn't reach): `self._EMISSION_SECTIONS =
    ("subject","verb","object")` meant only 3 sections were ever even
    CONSTRUCTED in the assemblage-dynamics system — a hard 3-word
    ceiling regardless of every numeric cap already removed. Joe
    explicitly authorized going after this (a real, scoped decision
    point — asked first given the documented regression history in
    this code, oscillation/timeouts).
13. **Found, while testing that fix, a real thread-leak bug**: every
    `Guala()` instance starts organism-writer/tapestry-writer/diary-
    writer daemon threads and nothing ever stopped them. Zero
    production impact (one Guala per process) but made my own
    multi-instance tests hang for 2+ minutes. Added `Guala.shutdown()`
    using the sentinel pattern the worker loops already had but never
    used. Verified the baseline (pre-my-change) code has the identical
    hang, proving it wasn't caused by my `_EMISSION_SECTIONS` work.
14. **Found, per Joe's "you have time, fix it" instruction**: `ground`
    and `intro` sections were structurally UNREACHABLE —
    `_choose_role_sections` had no branch that could ever route a word
    to either. Added real `ROLE_DNA` entries (ground: here/there/
    yesterday/etc.; intro: so/then/finally/etc., same hand-curated
    DNA-table convention as every other role class) and wired them in.
    This fix and the `_EMISSION_SECTIONS` extension are INTERDEPENDENT
    — neither is visible without the other (the same tuple also gates
    whether `_word_to_emission_sections`, the reverse index
    `_brain_emission_candidates`/`_compose_from_cortex` both read,
    ever records a commit at all).
15. **Lost this combined fix TWICE to shared-`.git`-directory
    collisions** (another concurrent session's commit/checkout wiped
    my uncommitted edits both times) — rebuilt it in an isolated
    worktree each time, verified identically, and it's now committed
    as `382de49`.
16. **c1a's `-205`** (compute-follows-need, demand-paced tick loop):
    deployed with a `0.001s` yield, caused a REAL live production
    stall within minutes (tick_rate collapsed to ~0.3/s, a
    converse() task hung "settling" 24s+). c1a rolled back to task-def
    `:487` (pre-205), then fixed forward with `22b1d36` (yield raised
    to `0.02s`, ~15-25x the original, root cause not fully isolated —
    production's real background-thread mix didn't reproduce locally).
    **My `382de49` deploy (task:489) briefly carried the broken
    0.001s-yield code as an ancestor** — the "pause returned 502,
    stuck reporting 'paused' for 90s" I observed during that deploy
    may well have BEEN this exact stall, not the transient glitch I
    assumed at the time.
17. **One collateral, unplanned good find**: post-`22b1d36`-ancestor
    deploy, boot logs showed `last_real_dream_tick` populated (was
    `None` all session) with real `dream_began`/`dream_artifact`
    events — E5 (first natural sleep, open since before tonight) may
    finally be satisfied, plausibly because `-205`'s faster tick rate
    let `dream_pressure` reach threshold in real time. **Not
    independently confirmed** — worth watching, not yet declared.
18. **One flagged, unfixed concern**: same deploy's boot log showed
    `Tapestry restore FAILED: Compressed file ended before the
    end-of-stream marker was reached` — a corrupted/truncated tapestry
    pickle. Correlates with that deploy's `[pause]` call returning
    HTTP 502 instead of a clean save confirmation. Plausibly a
    save-vs-shutdown race made more likely by `-205`'s much higher
    tick rate. Not fixed, not deeply investigated — `-205`'s
    territory, named for whoever owns that thread next.

## Deployed, in dependency order (oldest to newest)

`44070af` (-194+195) → `fdeaa89` (parallel fsync) → `5f1f554` (-196,
c1a) → `d7b56b1`/`b676e3f`/`11b2bd7` (-198 + two live pickle-compat
bugs) → `6d15797` (-197 P2/P3 reconciled) → `875fa73` (-205 v1,
**rolled back**) → `06aecb8` (-204 severance) → `09b6023` (shutdown
fix) → `382de49` (ground/intro + emission-sections, **built on the
now-reverted 875fa73**) → `22b1d36` (-205 v2 yield fix, includes
382de49 as ancestor — **deploy of this was in progress when this
handoff was written, not yet verified**).

## Lessons for whoever continues this

- **Shared `.git`, multiple concurrent sessions**: lost uncommitted
  work to this TWICE tonight, in the SAME session, after already
  knowing about the risk from a prior session's handoff. The only
  reliable defense: do ALL non-trivial edits in an isolated `git
  worktree` from the start, never in the shared main working
  directory, even for "quick" fixes. I violated this rule myself
  under time pressure and paid for it twice.
- **`_EMISSION_SECTIONS` is a load-bearing tuple in two unrelated
  places** (which sections get constructed in the assemblage-dynamics
  system, AND whether the word→section reverse index records a
  commit at all). A fix that touches only one of read_word's role-
  routing or `_EMISSION_SECTIONS` is invisible; they're coupled.
- **Dead-code paths are a real risk in a codebase with env-var-gated
  alternate implementations** (`EMISSION_MODE`, `EMISSION_DYNAMICS`,
  `CONVERSE_PHASED`). Before declaring a dispatch's named fix
  complete, check `aws ecs describe-task-definition` for the ACTUAL
  live env vars and trace which code path they actually select —
  `-203`'s named targets were real fixes but dead code under the live
  config; the real live mechanism was a completely different function
  neither the dispatch nor I noticed until directly investigating.
- **A deploy built on a since-reverted ancestor commit inherits that
  ancestor's bugs.** Before deploying, check whether `origin/HEAD`'s
  direct lineage includes anything recently rolled back.
- **Baseline test suite**: same 3 pre-existing failures all session
  (`test_t7_cross_modal`, `test_t8_noise_robustness`,
  `test_t11_substrate_true`). Anything beyond those 3 is a real
  regression.

### Changelog
- v2 (2026-07-05, c1b): full session handoff at context limit (one
  compact already used). -194 through -205-adjacent work, two lost-
  and-rebuilt fixes, two live bugs found outside any dispatch, one
  flagged-not-fixed tapestry corruption concern, one unconfirmed good
  sign (first natural dream).
