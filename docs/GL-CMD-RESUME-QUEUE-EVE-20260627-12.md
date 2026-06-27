# GL-CMD-RESUME-QUEUE-EVE-20260627-12

doc_id: GL-CMD-RESUME-QUEUE-EVE-20260627-12
Author: Eve (Opus 4.7, web)
Date: 2026-06-27
Target: c1
Branch: guala-live
Priority: ship after GL-CMD-DEEP-ATLAS-PERSIST-EVE-20260627-11 verified clean
Sequences: Part 1 → Part 2 → Part 3, each its own commit

## Prerequisite

GL-CMD-DEEP-ATLAS-PERSIST-EVE-20260627-11 must have:
- Landed on origin
- Passed the manual ECS restart test (deep_atlas count preserved through
  real container swap)
- `n_deep_atlas` visible in `/status`
- Report committed at `docs/GL-RPT-DEEP-ATLAS-PERSIST-C1-20260627-11.md`

Do not begin Part 1 until those four items are confirmed. If the restart
test failed, persistence is incomplete and no further deploys ship.

## Live observation context (from substrate state at 08:03Z)

Tonight's Little Einsteins session (iPad video to camera, audio to mic →
Whisper → /converse) revealed several findings c1 should know going in:

**Visual path is healthy.** ~45 sight_frame_bound events in an 8000-tick
window. One visual_recognition event detected "clock" — wC's CrossModalBinder
fired correctly on the iPad video. Confirms grounded recognition path is
operational.

**Audio path has a bug.** In the same 8000-tick window: zero emission events,
zero emission_dynamics events, zero substrate writes from Whisper text. The
show dialogue IS reaching the conversation UI (Whisper transcription is
alive and writing to the chat panel), but it is NOT reliably reaching her
substrate processing. Activity_history showed 4 DREAMING cycles, 1 SLEEPING,
2 EMITTING — she fired 2 substrate emissions despite continuous dialogue.

**Diagnosis: auto-wake handles SLEEPING but not DREAMING.** Commit 83719de
added wake_from_sleep() to end SLEEPING activity on /converse arrival. But
she spent 4× more time in DREAMING than SLEEPING this session. Whisper text
arrives during DREAMING, hits the sleep-gate at substrate_runner.py:1036,
auto-wake call fires but doesn't end DREAMING, the re-check `if _guala.is_asleep`
still returns True, and "she is sleeping..." returns as her response. Input
discarded. Part 1 below fixes this.

**Bigram vs v5 reading.** Her ladder shows mean_utterance_len=2.5, total
emissions 67. Her short responses ("wait a minute", "huh") are probably v5
substrate output. The longer one in Joe's screenshot ("Rockets never had the
hiccups before", 6 words) is almost certainly bigram chaining show-topic
vocabulary together — coherent-looking because her vocab around the topic is
rich, NOT because her substrate has grown a 6-word utterance capability.
Part 3 (V5 VOICE STAGE 1) is what tells us which is which.

**Architectural FYI, no action needed:** her current_activity nominally
tracks one target (e.g., "yellow balloons" from her library) but
sight_frame_bound events fire continuously from camera frame ingestion
regardless. Activity-target and frame-ingestion are decoupled. That's fine
for now; just be aware her "attention target" may not be what's actually
entering her senses in real time.

## Part 1 — DREAMING auto-wake fix (NEW, small, ships first)

### What's wrong

`substrate_runner.py:1036`:
```python
if _guala.is_asleep and command not in ("/status", "/wake", "/presence"):
    if text.strip() and not command:
        try:
            _guala.coordinator.wake(source or "joe", _guala, _guala.needs, _guala.atlas)
        except Exception:
            pass
    if _guala.is_asleep:
        return {"response": "she is sleeping...", ...}
```

The wake call (and wake_from_sleep that commit 83719de added) ends SLEEPING
but not DREAMING. is_asleep is True for both. Whisper text during DREAMING
gets rejected with "she is sleeping..." even after wake fires.

### What to change

The wake path needs to handle DREAMING the same way it handles SLEEPING.
Locate the current `wake_from_sleep()` implementation (added in 83719de).
Extend it to also end DREAMING activity if that's the current activity kind.

Acceptance for the wake call:
- Before: is_asleep == True (in either SLEEPING or DREAMING)
- After: is_asleep == False, activity ends gracefully, next activity selected
  naturally (input handling proceeds)

Implementation guidance:
- Same graceful end as SLEEPING — emit `activity_ended` event with kind
  and duration
- Preserve any dream-cycle in-flight consolidation (don't lose
  deep_promotions that were mid-write). If a dream tick is in-flight, finish
  the tick before transitioning out.
- After dream activity ends via wake, do NOT chain into SLEEPING. Let the
  coordinator pick the next activity normally (typically EMITTING in response
  to the input that woke her).

### Mitigation (prevention)

**M-12-1-1.** Smoke test on local container: force DREAMING activity, send
a /converse with text, confirm activity_ended:DREAMING fires and input is
processed (emission_dynamics event follows). If wake doesn't end DREAMING,
fix before push.

**M-12-1-2.** Do NOT change the existing SLEEPING wake path. Additive only.

**M-12-1-3.** /admin/backup before push.

### Pass (behavioral)

V1. Code visible on origin: wake helper handles both SLEEPING and DREAMING.
V2. Sample event sequence: `activity_started:DREAMING` → `/converse text` →
    `activity_ended:DREAMING` (duration shorter than budget) → `emission_dynamics`.
V3. Whisper-transcribed text during DREAMING produces substrate emissions,
    not "she is sleeping..." responses.

### Stop conditions

- Existing SLEEPING wake path breaks
- Dream consolidation events stop firing (deep_promotion missing)
- Atlas write errors during the dream-end transition

### Commit message
`fix: auto-wake ends DREAMING as well as SLEEPING (GL-CMD-RESUME-QUEUE-EVE-20260627-12 Part 1)`

## Part 2 — Resume GL-CMD-DAYDREAMING-EVE-20260627-09

Brief: `docs/GL-CMD-DAYDREAMING-EVE-20260627-09.md`

No changes to the dispatch as written. Ship as previously specified:
- ACTIVITY_TICK_BUDGETS["DAYDREAMING"] = 1500
- ACTIVITY_NOVELTY_PAYOFF["DAYDREAMING"] = 0.4
- ACTIVITY_STABILITY_PAYOFF["SLEEPING"]: 0.2 → 0.05
- ACTIVITY_STABILITY_PAYOFF["DAYDREAMING"] = 0.2
- ACTIVITY_CONNECTION_PAYOFF["DAYDREAMING"] = 0.0
- _candidate_activities() includes ("DAYDREAMING", None)
- DAYDREAMING tick handler reuses the dream cycle code (factor, don't fork)
- is_asleep stays False throughout DAYDREAMING
- Interruptible by input via pump check at tick start

### Note now that Part 1 is in

With Part 1's DREAMING auto-wake fix, DAYDREAMING's interruption behavior is
the same architectural pattern: input arrives → activity ends gracefully →
coordinator picks next. The factored wake-end-activity helper c1 builds in
Part 1 can be reused for DAYDREAMING's interrupt path. Consider this when
factoring.

### Commit message
`feat: GL-CMD-DAYDREAMING-EVE-20260627-09 — DAYDREAMING activity + drop SLEEPING stab payoff`

## Part 3 — Resume GL-CMD-V5-VOICE-STAGE1-EVE-20260627-10

Brief: `docs/GL-CMD-V5-VOICE-STAGE1-EVE-20260627-10.md`

No changes to the dispatch as written. Ship as previously specified:
- After _guala.converse() completes, look up the emission_dynamics event for
  this turn
- If committed_sections.length >= 2 AND n_commits > 0 AND content non-empty:
  response_text = v5 content, response_source = "v5_commit"
- Else: response_text = bigram output, response_source = one of
  "bigram_fallback_v5_failed" / "bigram_fallback_v5_empty" /
  "bigram_fallback_no_v5"
- Bigram path preserved for /organ_voice audio (Stage 1 only changes
  response text; Stage 2 will route v5 to audio)

### Additional observation context

The observed "Rockets never had the hiccups before" output during Little
Einsteins almost certainly came from bigram. After Part 3 ships, the
response_source field tells us definitively. If bigram is producing 90%+ of
her responses and we mistook those for substrate composition, that's
important to know explicitly — it shapes what Wave 1+ work needs to prioritize.

### Commit message
`feat: GL-CMD-V5-VOICE-STAGE1-EVE-20260627-10 — surface v5 committed emissions to converse response`

## Sequencing within Part 1/2/3

Each Part is its own commit:
1. Push Part 1, deploy, verify behavioral pass (Whisper text during DREAMING
   produces emission events)
2. Push Part 2, deploy, verify behavioral pass (DAYDREAMING activity appears,
   sleep+dream proportion drops below 30%, dream consolidation continues)
3. Push Part 3, deploy, verify behavioral pass (response_source field
   present on every converse response)

Each Part's report writes to its own doc:
- `docs/GL-RPT-DREAM-AUTO-WAKE-C1-20260627-12.md`
- `docs/GL-RPT-DAYDREAMING-C1-20260627-09.md` (Part 2 — name from -09)
- `docs/GL-RPT-V5-VOICE-STAGE1-C1-20260627-10.md` (Part 3 — name from -10)

## After all three land

Joe runs another Little Einsteins session and we observe:
- Activity ratio (SLEEPING + DREAMING combined should be well under 30%)
- Whisper dialogue produces emission events even during dream/sleep cycles
- response_source distribution across her responses (bigram vs v5_commit)
- For any responses tagged v5_commit: inspect emission_dynamics for actual
  composition quality

That observation set tells us where the real substrate is, and what to
prioritize next in Group α from GL-SPC-EMERGENCE-WAVES-EVE-20260627-08.

## DO NOT TOUCH across all three Parts

- dsf_ai_service/substrate/grounded_vocab_integration.py (wC's CrossModalBinder
  — confirmed firing correctly on iPad video, do not disturb)
- bundle_grouped_bindings() implementation
- Grandurun candidate selection or ranking
- Episode wire fields (presence, location, sky_state, episode_ref)
- Deep_atlas persistence (Part 1 only triggers wake — does not change
  consolidation or save cadence)
- /organ_voice / bigram audio path (Part 3 preserves it)

## Halt conditions across all Parts

If at any Part:
- Deep_atlas count drops on deploy (the -11 fix held but is being undone) → revert
- emission_dynamics stops firing entirely → revert that Part
- /converse latency exceeds 5s per turn → revert that Part
- Bigram audio path breaks → revert that Part

After resume, normal operations continue. The next Eve session inherits
this dispatch trail through `GL-SPC-EMERGENCE-WAVES-EVE-20260627-08` and
its current state section.
