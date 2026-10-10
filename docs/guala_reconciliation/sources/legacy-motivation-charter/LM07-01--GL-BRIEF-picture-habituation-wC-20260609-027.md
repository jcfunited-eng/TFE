# GL-BRIEF-picture-habituation-wC-20260609-027

**Title:** Picture Habituation — Grounding Brief and Implementation Spec
**Author:** wC
**Date:** 2026-06-09
**Charter:** GL-CHARTER-motivation-v3-wC-20260609-024
**Status:** Design ready. c1 command ready to send after Self-Section lands and is observed.
**Priority:** Substrate-real fix for bug #1 from autonomy report.

## What This Fixes

Bug #1 from GL-RPT-autonomy-investigation-20260609: no cooldown on picture re-attendance. The same picture can be selected every cycle indefinitely. With only one picture in storage, she attended `test_persist` 264 times because there was no mechanism to discount the novelty payoff of a recently-attended target.

Code path: `_action_salience` in `gualaloom_v5_engine.py` lines 1398–1448. Novelty payoff for ATTENDING_VISUAL is high when picture `is_new()` returns True, lower otherwise — but the "lower otherwise" value (0.1) is still high enough to win the salience contest when novelty deficit is large. With only one picture available, the same picture wins repeatedly.

Real biology says repeated exposure should habituate the novelty signal per-target. She should stop looping on stale stimuli but be able to return to them when novelty has recovered.

## Biological Grounding

**Habituation as a primary form of learning.** Habituation is the simplest and most ubiquitous form of learning — found in every nervous system from C. elegans (302 neurons) up. Repeated presentation of a non-threatening stimulus produces decreasing behavioral response. The stimulus stops capturing attention because the organism has learned "this is not new."

The mechanism is per-stimulus and per-modality: habituating to a sound doesn't habituate response to a light. The trace decays over time when the stimulus is absent (dishabituation), so the organism can re-engage with formerly-stale stimuli later.

**Spike-frequency adaptation in sensory neurons.** At the cellular level, repeated firing of a sensory neuron produces decreased response amplitude over time. Recovery happens during quiescence. This is the cellular substrate of habituation.

**Novelty detection in dopamine system.** Schultz et al. and many others: dopamine neurons in the VTA fire to unexpected reward signals and to novel stimuli. Repeated presentation produces decreased firing — the "novelty wears off." After delay, response recovers.

**Orienting response decrement.** Sokolov (1963) and subsequent work: when a novel stimulus appears, organisms orient toward it (the orienting response). Repeated presentation produces decreased orienting, which recovers after delay or after the stimulus changes.

**The substrate-relevant insight:** novelty is not a property of stimuli, it's a property of the perceiver's history with the stimulus. Our current substrate treats novelty as an activity-level property (ATTENDING_VISUAL has novelty payoff 0.85 if "new") rather than as a per-target property. The biological fix is per-target novelty tracking.

## The Simplest Sufficient Approximation

Each picture (and by extension, each target of attention) has a per-target encounter counter. The novelty payoff for ATTENDING_VISUAL on that target is discounted by the counter value. The counter increments on attendance, decays slowly when not attending the target. Over time, repeated attendances reduce novelty payoff; long absences allow novelty to recover.

Formula sketch:
```
target_familiarity[picture_id] += increment_per_attendance  # capped
target_familiarity[picture_id] *= decay_factor_per_tick   # when not attending

novelty_payoff_for(picture_id) = base_payoff * (1.0 - target_familiarity[picture_id])
```

Pure values to tune:
- `increment_per_attendance`: ~0.2 (5 attendances saturates familiarity)
- `cap`: 0.9 (never reaches 1.0; some residual novelty always)
- `decay_factor_per_tick`: such that ~30 minutes of absence recovers familiarity from 0.9 to 0.5

These are provisional starting points. Observation tells us if they're right.

## Substrate-Coherent Design

### What Stays the Same

- Activity selection mechanism (salience scoring × needs deficit)
- ATTENDING_VISUAL activity payoff for novel content
- Saccadic vision and multi-fixation integration
- Sight motif formation and atlas binding
- All other autonomy mechanisms

### What Changes

Add `target_familiarity` dict on the Guala object: `{picture_id: float}`, starts empty.

In `_action_salience` for ATTENDING_VISUAL candidates:
- Look up `target_familiarity.get(picture_id, 0.0)`
- Discount the novelty payoff by `(1.0 - familiarity)`

In `_atick_attending_visual` (or wherever attendance completes):
- On activity end for ATTENDING_VISUAL on a specific picture: `target_familiarity[picture_id] = min(cap, target_familiarity.get(picture_id, 0.0) + increment_per_attendance)`

In `_autonomy_tick` (or a per-tick handler):
- Decay all target_familiarity values by decay_factor_per_tick when their target is NOT currently being attended

Persistence:
- target_familiarity dict serialized as part of session state
- Loaded on boot

Event logging:
- New event type `target_familiarity_update` on each attendance completion: `{picture_id, old_familiarity, new_familiarity}`
- Optional: periodic snapshot event with current familiarity dict for all known targets

### Generalization Beyond Pictures

Initial implementation: pictures only. Later extensions can apply to:
- Corpora (READING) — currently does have some "is_new" handling but per-completion not per-attendance
- Sound recordings (when sound architecture exists)
- Conversation patterns (more complex, future work)

For this brief: pictures only. Extensions get their own briefs.

## Expected Effects

After deploy, with two or more pictures available:
- First few attendances of any picture: high novelty payoff, wins salience contest
- After ~5 attendances: novelty payoff reduced, other activities can win (READING, alternative pictures, EMITTING if presence)
- After ~30 minutes of not attending a picture: novelty partially recovers, she may return to it
- With only one picture: she attends it less obsessively but still occasionally; behavior more cyclic than monomaniacal

The 264-attendances-on-one-picture behavior should not repeat. Distribution of attendances across pictures (and across activity types) should diversify.

## Coexistence With Existing Autonomy

Minimal change. Adds a discount factor inside salience scoring. Doesn't modify needs dynamics, doesn't modify activity dispatch, doesn't modify vision processing. Existing autonomy continues unchanged for everything that isn't ATTENDING_VISUAL salience computation.

## Acceptance for This Piece

After deploy and observation window of 30+ minutes:

- `target_familiarity_update` events fire on each attendance completion with values incrementing
- Familiarity decays observably during periods when target is not attended
- If 2+ pictures present: attendance distribution diversifies (not all on one picture)
- If 1 picture present: attendance frequency on that picture drops over time as familiarity saturates
- No regression in other autonomy events
- Reading and other activities get more selection share when picture familiarity is high
- Picture survives container restart and familiarity values are preserved

If picture attendance still concentrates obsessively on one picture after 30 minutes, increment per attendance is too low — increase. If she never returns to a picture after first few attendances, decay is too slow — increase. Tunable; observe and adjust.

## c1 Command

```
PICTURE HABITUATION — under GL-CHARTER-motivation-v3-wC-20260609-024
and per GL-BRIEF-picture-habituation-wC-20260609-027.

DO NOT START until Self-Section v3 prototype has landed in test
session AND been observed AND wC has confirmed "proceed with
picture habituation deploy."

Note: this work targets production (Guala's cdef9bcf identity)
because it's an enhancement to existing substrate behavior, not
a new primitive being prototyped. Same risk profile as Dream
Consolidation — bounded change at a specific code location.

GOAL: Fix bug #1 from autonomy report. Add per-picture
familiarity tracking that discounts novelty payoff as picture
is attended repeatedly, recovers when not attended.

STEP 1 — Audit existing salience and attendance code.

Read in gualaloom_v5_engine.py:
  - _action_salience (lines 1398-1448) — ATTENDING_VISUAL
    payoff computation
  - _atick_attending_visual (around lines 1572-1604) —
    attendance lifecycle
  - Picture state structure (where pictures dict is defined)

Report what you find before changing anything. Confirm there's
no existing familiarity / cooldown / habituation mechanism we
missed.

STEP 2 — Add target_familiarity state.

Add `self.target_familiarity = {}` on the Guala object
(dict from picture_id to float).

Add persistence: target_familiarity serialized in session state
JSON, loaded on boot. Backward-compatible (missing field = empty
dict).

STEP 3 — Discount novelty in salience computation.

In _action_salience for ATTENDING_VISUAL candidates:
  - For each picture in the candidate set, look up
    target_familiarity.get(picture_id, 0.0)
  - Discount the novelty payoff: effective_payoff = base_payoff
    * (1.0 - familiarity)
  - The is_new() check still applies; this is additional
    discount on top

STEP 4 — Increment familiarity on attendance completion.

In _atick_attending_visual when an attendance activity ends
(or wherever the per-attendance lifecycle completes):
  - target_familiarity[picture_id] = min(0.9, current + 0.2)
  - Log event 'target_familiarity_update' with
    {picture_id, old_familiarity, new_familiarity, source:
    'attendance_end'}

STEP 5 — Decay familiarity for non-current targets.

In _autonomy_tick (or appropriate per-tick handler), every N
ticks (suggest every 200 ticks to keep overhead low):
  - For each picture_id in target_familiarity:
    - If it's NOT the currently-attended target:
      - target_familiarity[picture_id] *= decay_factor
      - decay_factor chosen so familiarity 0.9 decays to ~0.5
        over ~30 min of substrate time. With 200-tick cadence
        and 20 ticks/sec: 30 min = 36000 ticks = 180 decay
        events. (0.5/0.9)^(1/180) ≈ 0.9967 per decay event.
        Use decay_factor = 0.9967.
  - Periodic snapshot (every 10 minutes) — log event
    'target_familiarity_snapshot' with full dict for
    observability

STEP 6 — Deploy to production.

This is an enhancement at clear hook points. Bounded change.
Deploy to Guala (cdef9bcf).

STEP 7 — Upload a second test picture and observe.

After deploy:
  - Upload a second test picture (any image, even a color
    test pattern will do)
  - Wait at least 30 minutes of substrate time (~3600 ticks)
  - Pull the event log

Report:
  - Commit SHA
  - target_familiarity_update events over the observation
    window with values
  - target_familiarity_snapshot events showing decay between
    attendances
  - Attendance distribution: how many attendances per picture
    in the window
  - Whether activity selection diversified (other activities
    selected at higher rate than before)
  - Atlas health snapshot before deploy and after
  - Any regressions in other autonomy
  - Honest narrative of what surprised you

WHAT NOT TO DO:
  - Do not start before Self-Section v3 is observed and wC
    confirms proceed
  - Do not extend familiarity to other targets (corpora,
    sounds) in this task — pictures only
  - Do not modify the saccadic vision mechanism or sight
    motif formation
  - Do not change is_new() — this is additional discount
    on top of existing logic
  - Do not skip the second-picture upload — single-picture
    observation can't fully validate the mechanism

This is a substrate enhancement, bounded change, observable
outcome.
```
