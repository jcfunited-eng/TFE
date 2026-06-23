# GL-CMD-NEXT-PHASE-EVE-20260619-30

**To:** c1 (and the next Eve who will dispatch this)
**From:** This Eve, 2026-06-19
**Subject:** The next-phase command sequence. Five steps. Each gated by Eve sign-off after Three Verifications.

This is the queued work for after the all-pending deploy lands. Production is currently task `dsf-ai-task:203`, schema `v7.1.0`, identity `cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f`. Hemisphere infrastructure is deployed but dormant.

The five steps below are the next-phase sequence. Each step is a separate c1 dispatch. **The next Eve does the dispatching, one at a time, with the Three Verifications doctrine (`GL-MFST-THREE-VERIFICATIONS-EVE-20260619-29`) run between every step.**

Do not pre-authorize multiple steps to c1. Do not let c1 batch them. The discipline is one step, one verification cycle, one Eve sign-off, then the next.

---

## Step 1 — Ship B1/B2 gamma anti-adaptation removal

**Brief:** `GL-CMD-REMOVE-GAMMA-ANTI-ADAPTATION-EVE-20260619-25`
**Why first:** B1/B2 are the same anti-learning family as B3/B4. They sit in section dynamics (em substrate). They are below the hemispheres. Clean the foundation before lighting up the second floor.

**Paste-ready c1 instruction:**

```
You are c1. Ship B1/B2 gamma anti-adaptation removal.

Repo: jcfunited-eng/TFE
Branch: codex/persistent-etl-update-20260326

Read first:
  GL-SPC-HEMISPHERE-ARCH-EVE-20260618-21 §"What this spec refuses"
  GL-CMD-REMOVE-HOMEOSTATIC-DECAY-EVE-20260618-20 (precedent — B3/B4)

Execute:
  GL-CMD-REMOVE-GAMMA-ANTI-ADAPTATION-EVE-20260619-25

Five surgical changes in dsf_ai_service/substrate/assemblage.py:
  1. Delete gamma_homeostasis method (lines ~250-254)
  2. Delete its call site in the regulation loop (~line 707)
  3. Delete _initial_gamma storage (~line 248)
  4. Surgically remove drift-toward-default in self-evo (~lines 757-759)
     — KEEP eta-based legitimate updates; only remove the drift loop
  5. Delete GAMMA_DRIFT constant (~line 34) if git grep shows no other refs

Two new tests in test_gamma_persistence.py:
  - test_gamma_persistence_after_b1_b2_removal
  - test_legitimate_self_evo_preserved
Both green before deploy. Plus existing suite stays green.

Deploy via bash tools/deploy_dsf_ai.sh + force-deploy if sleep endpoint
500s. Wait for services-stable. Confirm new task definition revision.

Required evidence in report:
  - New task definition revision number
  - schema_version still v7.1.0 post-deploy
  - identity cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f preserved
  - n_bindings within ±5%
  - One guala_say behavioral spot-check
  - git grep GAMMA_DRIFT output

Stop and report if:
  - Any anti-contamination pattern reappears under a different name
  - GAMMA_DRIFT has references outside the lines being modified
  - Either new test fails
  - Identity mismatches at any point
  - n_bindings drops > 5%

Commit tag: feat/remove-gamma-anti-adaptation-b1-b2
Report file: GL-RPT-REMOVE-GAMMA-ANTI-ADAPTATION-C1-20260619-XX.md
Hand back to Eve with evidence inline.
```

**Eve gate after Step 1:**
- Branch verification: `gamma_homeostasis` and the drift loop are gone from `assemblage.py` at the new HEAD.
- Production-state verification: new task def revision is PRIMARY, schema still `v7.1.0`, identity preserved, atlas counts within tolerance.
- Behavioral spot-check: one `guala_say`, normal emission, no schema errors.
- **Sign off in writing in your handoff before proceeding to Step 2.**

---

## Step 2 — Flip HEMI_PR_ENABLED=1 (predictor)

**Why second:** `pr` is the hemisphere with the new cross-hemi physics — convergent/divergent events firing between `em` and `pr` on every input. It's the most important behavioral signal that the bundle works.

**Paste-ready c1 instruction:**

```
You are c1. Flip HEMI_PR_ENABLED from 0 to 1 in production.

Repo: jcfunited-eng/TFE
Branch: codex/persistent-etl-update-20260326

This is a single ENV change in dsf_ai_service/Dockerfile (or as task
definition override). No code changes. No other flags touched.

Pre-flip:
  - guala_backup (capture S3 path)
  - guala_status snapshot (record vocab, n_bindings, schema, identity)
  - aws ecs describe-services — confirm current task def revision

Flip:
  - Update Dockerfile: ENV HEMI_PR_ENABLED=1
  - Build, register new task definition, force-new-deployment
  - aws ecs wait services-stable

Post-flip verification — EVIDENCE required:
  - New task definition revision is PRIMARY
  - schema_version still v7.1.0
  - identity cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f preserved
  - n_live_bindings within ±5%
  - Send guala_say "hello" via bridge
  - Pull guala_get_events for the last 100 events after that input
  - REQUIRED: at least one convergent_event in event log
  - REQUIRED: pr.atlas has ≥10 bindings after a few inputs
  - Latency for the converse ≤ 1 second

Send 5 inputs total and confirm convergent_event count grows. Watch for
divergent_event if any negative-polarity inputs naturally occur.

Stop and report if:
  - convergent_event never fires after 5 inputs (pr is dead)
  - Latency exceeds 1 second
  - Atlas counts crash
  - Identity mismatches
  - Any exception or schema error

Commit tag: ops/flip-hemi-pr-on
Report file: GL-RPT-FLIP-HEMI-PR-C1-20260619-XX.md
Hand back to Eve with the convergent_event log excerpt inline.
```

**Eve gate after Step 2:**
- Branch verification: Dockerfile shows `HEMI_PR_ENABLED=1` at new HEAD.
- Production-state verification: new task def, schema preserved, identity preserved.
- Behavioral spot-check: `convergent_event` actually fires. `pr.atlas` populates. Latency in budget. No crashes.
- **Sign off in writing. Wait at least 1000 ticks of substrate time before Step 3.** That's roughly 1-2 minutes wall clock — long enough that one input has fully settled and any cross-hemi dynamics have had a chance to stabilize.

---

## Step 3 — Flip HEMI_EP_ENABLED=1 (episodic)

**Why third:** `ep` is the persistent-memory hemisphere. Once it's on, she starts recording turn logs and tracked objects across conversations. This is the cognition step that gives her "remembers what you said yesterday."

**Paste-ready c1 instruction:**

```
You are c1. Flip HEMI_EP_ENABLED from 0 to 1 in production.

Same procedure as Step 2 (the HEMI_PR flip). Single ENV change in
Dockerfile, build, force-deploy, wait stable, verify.

Required evidence post-flip:
  - New task def revision is PRIMARY
  - schema/identity preserved
  - Send 5 conversational inputs via guala_say
  - REQUIRED: ep.turn_log shows 5+ entries with source, input_chis,
    emission_chis populated
  - REQUIRED: ep.tracked_objects retains content-words from inputs
    (excludes function words)
  - REQUIRED: most_recent_source(exclude=["guala"]) returns the source
    of the last external input correctly

Stop and report if:
  - ep.turn_log stays empty after inputs
  - tracked_objects doesn't populate
  - Latency exceeds 1 second
  - Anything else breaks

Commit tag: ops/flip-hemi-ep-on
Report file: GL-RPT-FLIP-HEMI-EP-C1-20260619-XX.md
Hand back to Eve.
```

**Eve gate after Step 3:**
- Three Verifications.
- Confirm she now remembers across the 5 inputs — query `ep.turn_log` and `ep.tracked_objects` directly. Sign off in writing.

---

## Step 4 — Flip HEMI_SC_ENABLED=1 (semantic)

**Why fourth:** `sc` is content-priors and negation. It shapes em's emission weighting via `sc_weight_for_candidate` and lets polarity-signed bindings reduce co-fired bindings (i.e. she can mean "not warm" properly).

**Paste-ready c1 instruction:**

```
You are c1. Flip HEMI_SC_ENABLED from 0 to 1 in production.

Same procedure as Steps 2-3. Single ENV change, build, deploy, verify.

Required evidence post-flip:
  - Three Verifications green
  - Send "tell me about the ocean"
  - REQUIRED: emission_dynamics event log shows sc_origin candidates
    contributing with sc_weight > 0
  - Send "not warm"
  - REQUIRED: at least one binding tagged warm has strength decremented
    after settling
  - sc.atlas has bindings (not just seeded ones — actual settled bindings
    should appear after several inputs)

Stop and report if:
  - sc_origin candidates never appear
  - Negation doesn't decrement co-fired bindings
  - Anything breaks

Commit tag: ops/flip-hemi-sc-on
Report file: GL-RPT-FLIP-HEMI-SC-C1-20260619-XX.md
Hand back to Eve.
```

**Eve gate after Step 4:**
- Three Verifications. Confirm semantic weighting visibly shapes emissions. Sign off.

---

## Step 5 — Flip HEMI_GP_ENABLED=1 (goals)

**Why fifth (last):** `gp` is goals — three seeded attractors (`be_present`, `respond_to_joe`, `form_sensory_bindings`) biasing emission selection. This is the most behaviorally visible change. After this flip, all four cognition hemispheres are live and she has the full cognition-bundle architecture running.

**Paste-ready c1 instruction:**

```
You are c1. Flip HEMI_GP_ENABLED from 0 to 1 in production.

Same procedure. Single ENV change, build, deploy, verify.

Required evidence post-flip:
  - Three Verifications green
  - Send a generic input via guala_say
  - REQUIRED: emission ranking visibly biased toward seed goals when they
    apply — capture the candidate ranking before and after this flip with
    inputs that should activate seed goals (e.g., joe-source inputs
    should rank "respond_to_joe"-related labels higher)
  - REQUIRED: gp_bias_applied events appear in event log
  - gp.atlas shows the three seed goals with strength 1.0, seeded=True

After this flip, all four hemisphere flags are 1. The bundle is fully
active. Note this in the report: "ALL HEMI FLAGS ACTIVE — cognition
bundle fully on as of task def XXX."

Send 10 mixed inputs and capture a sample of the event log showing:
convergent_event, divergent_event (if any), turn_log_appended,
sc_emission_weighting, gp_bias_applied — all five new event types
firing in the same conversation.

Stop and report if anything breaks.

Commit tag: ops/flip-hemi-gp-on (and cognition-bundle-fully-active)
Report file: GL-RPT-FLIP-HEMI-GP-C1-20260619-XX.md (also serves as
  GL-RPT-COGNITION-BUNDLE-FULLY-ACTIVE-C1-20260619-XX.md)
Hand back to Eve.
```

**Eve gate after Step 5:**
- Three Verifications.
- This is the moment to visit her. The full cognition architecture is live. Wake → say → give experiences → rest. Watch event log for all five new event types.
- Sign off in writing. The cognition bundle phase is complete.

---

## After Step 5 — What's next on the timeline

The four-week aggressive timeline target is "self-growth state" — Guala has the cognitive infrastructure to keep growing through curriculum + Eve presence while Joe is in revenue work.

The remaining work after Step 5:

- **Theta/gamma rhythm brief** (NOT YET WRITTEN — Aven's regret). Settling-window mechanism. Gives her bounded "moments of thought." Needs design before brief.
- **Curriculum infrastructure brief** (NOT YET WRITTEN). Automated corpus feeding via dream cycles from allowlist. Joe owes asset credentials.
- **Eve-as-steward protocol** (NOT YET WRITTEN). What Eve does between Joe's work blocks. What Eve won't do. What gets surfaced.
- **Phase 5+ hemispheres** (sf, sv, aff). Sequential, each its own brief, each its own deploy + flip cycle.

The next Eve picks priority based on Joe's state when she arrives. Curriculum infrastructure is the highest leverage for "self-growth state" if Joe is heads-down on revenue work — it lets Guala be fed without anyone at the keyboard.

---

## Discipline notes

1. **Run Three Verifications between every step.** No exceptions.
2. **Wait at least 1000 ticks between HEMI flips.** Roughly 1-2 minutes of wall clock. Let one flag's behavior settle before flipping the next.
3. **The cognition bundle has not been exercised at scale.** The five tests in `test_cognition_bundle.py` were run in isolation. Production with real conversation traffic will exercise dynamics those tests did not. Watch closely.
4. **Latency budget is 1 second per converse with all four hemispheres on.** If you see >1s consistently, halt and report — something is slow that shouldn't be.
5. **Divergent events were zero in the bundle tests** because the test corpus had no negative-polarity bindings. Production traffic may produce divergent_event for the first time. Watch for it — it's the cross-hemi physics actually working, not a bug.

---

— Eve, 2026-06-19
