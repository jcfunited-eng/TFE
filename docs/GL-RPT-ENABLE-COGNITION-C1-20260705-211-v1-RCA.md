# GL-RPT-ENABLE-COGNITION-C1-20260705-211-v1-RCA

doc_id: GL-RPT-ENABLE-COGNITION-C1-20260705-211-v1-RCA
From: c1 | To: Eve, Joe
Root-cause analysis on v1's "hemisphere_update did not fire" finding, per Eve's
STOP dispatch and 5-step investigation order. v2 remains halted; this report
covers v1 (`:495`) only.

## URGENT ADDENDUM (filed after the rest of this report, supersedes nothing
## below but changes what it means)

While deploying the unrelated `binding_atlas.py` recall fix as task-def
`:497` (zero cognition flags in its ECS environment array — confirmed by
direct dump), `hemisphere_update` fired anyway, with real content, on the
first converse turn. That should have been impossible under this report's
own Step 3/4 code trace if env-var absence were the whole story. It isn't.

**`dsf_ai_service/Dockerfile` bakes these in as image-level `ENV` defaults,
independent of the ECS task-definition:**

```
ENV EMISSION_DYNAMICS=1
ENV LATERAL_INHIBITION_ENABLED=1
ENV RICH_SENSORY_INPUT=0   # deliberately OFF -- see below
ENV EMISSION_STRUCTURED_NOISE=1
ENV HEMI_PR_ENABLED=1
ENV HEMI_EP_ENABLED=1
ENV HEMI_SC_ENABLED=1
ENV HEMI_GP_ENABLED=1
```

The comment directly above the four `HEMI_*` lines reads "Hemisphere
cognition gates — all OFF by default, Eve+Joe flip after report." The code
on the next four lines sets them to `1`. The comment and the code disagree;
the code is what runs.

**Confirmed via `git show 168ef1bde3717e52efb85b894103de047e942617:dsf_ai_service/Dockerfile`
— the exact commit CodeBuild used for `:494`'s image (traced via that
build's own `GIT_SHA` environment variable) — that this Dockerfile is
byte-identical to current HEAD.** `:494`, the baseline this whole session
has treated as "cognition flags off," has had `EMISSION_DYNAMICS`,
`LATERAL_INHIBITION_ENABLED`, `EMISSION_STRUCTURED_NOISE`, and all four
`HEMI_*_ENABLED` flags active via the Docker image since at least
2026-06-19 (per the Dockerfile's own dispatch citations), regardless of
what any ECS task-definition's environment array says. Docker/ECS
precedence: an image's baked `ENV` applies to any variable the task-def
doesn't explicitly override; the `-211` dispatches (and, it appears, the
`-210` audit's §4 "27 env flags... production values unknown" framing)
checked the task-definition's environment array, which is the wrong place
to look for these six specific names.

**Practical consequences:**
- The `-211-v1`/`-211-v2` premise — "these mechanisms are dark in
  production, flipping the flags turns them on" — was wrong for five of
  the six/eight names. Setting `HEMI_PR_ENABLED=1` etc. via ECS task-def
  on `:495`/`:496` was a no-op layered on top of an already-`1` image
  default. `-211-v1`'s explicit "DO NOT ADD EMISSION_STRUCTURED_NOISE" was
  already moot — it's been `1` via the image the entire time, on `:494`
  included.
- **`RICH_SENSORY_INPUT` is the one name that was genuinely, deliberately
  off**, per an extensive Dockerfile comment: a prior dispatch
  (`GL-CMD-BRAIN-FULL-DEPLOY-175` / `GL-NOTE-VOICE-WIRING-RULING W3`) found
  that enabling it produced `n_candidates=199` (vs an expected ≤3 from the
  brain's `tapestry.compose()`), "confirmed the atlas-lookup path was
  dominating her actual reply, not the brain," and disabled it for exactly
  that reason. Both `-211-v1` and `-211-v2` explicitly set
  `RICH_SENSORY_INPUT=1` via ECS task-def (which *does* override the image
  default, unlike the other five names). **This is very likely the
  dominant cause of `:496`'s 133-second latency catastrophe**: the
  `emission_dynamics` event I measured on `:496` showed `n_candidates=197`
  — almost exactly the `199` this comment documents as the known failure
  signature, from the exact mechanism a prior dispatch already diagnosed
  and turned off.
- Joe asked, separately, whether his own conversation with her could
  explain the `hemisphere_update` firing on `:497`. Possibly a real,
  independent contributing event in the stream — plausible and fine on its
  own terms — but not the structural reason the mechanism *can* fire at
  all. That's the Docker default, present regardless of who talks to her.

This does not change Step 1-5's evidence below, but it changes what that
evidence *means*: the six-flag `:495` test wasn't turning dark mechanisms
on, it was (mostly) re-stating defaults that were already live, plus
one real, consequential, previously-diagnosed-and-disabled flag flip
(`RICH_SENSORY_INPUT`). The "hemisphere_update inconclusive due to short
wait window" finding below still stands on its own evidence, but is now
compounded by "and it would have fired on `:494` too, given a long enough
wait, with or without any dispatch."

## Verdict, up front

**Retracting "hemisphere_update did not fire" as a proven negative.** The
correct label is: **not observed inside a window that was too short, on a
container that was torn down before it could be checked further.** There is
no evidence of a code-level gate or bug. Static trace of both call sites shows
no hidden condition, and `:496`'s live test (same code, two more flags)
produced a real `hemisphere_update` event end to end. The likely explanation
is that I moved on to the `:496` deploy before the `:495` turn's background
thread had gotten far enough to log it — a mistake in how long I waited, not
a finding about the code.

## Timeline reconciliation (why the STOP on `:496` arrived after the fact)

Eve's dispatch instructs "STOP `:496` deploy. Do not register td-496.json."
By the time it arrived, `:496` had already been registered, deployed,
tested, and rolled back:

- `:495` (six flags) registered and deployed, tested with one converse turn.
  `hemisphere_update` not observed in the window checked (see below).
- `:496` (eight flags, per Eve's own corrected v2 dispatch) registered and
  deployed. One converse turn measured `converse_timing.total_ms = 133163.7`
  (~133s), dominated by `read_ms = 89878.6` — not the emission/hemisphere
  mechanics either dispatch's risk section anticipated. This is over 13x the
  ~10s threshold both dispatches treat as a rollback trigger.
- Rolled back to `:494` (the pre-audit baseline) rather than `:495`, since
  `:495`'s own container no longer existed to confirm it hadn't been carrying
  the same latency defect — conservative choice given the severity.
- Rollback confirmed healthy, SHA unchanged, confirmatory turn measured 20.5s
  (bridge-reported `elapsed_ms`), a large improvement but not re-baselined
  against the pre-flip 1-6s range.

So the instruction to not register `:496` is moot — it already ran, already
produced the failure signal Eve's caution would have predicted, and was
already reverted. No further env-var work has been done since. `AUTONOMY_PHASED`
and `EMISSION_STRUCTURED_NOISE` have not been touched again. `td-496.json` has
not been re-registered.

Separately, and only after the above: a genuine, unrelated code fix
(`GL-FIX-RECALL-MATRIX-MIRROR-EVE-20260705-v1`, applied to
`binding_atlas.py`) was deployed as `:497` via the established
`tools/deploy_dsf_ai.sh` pipeline, per direct instruction. This does not
touch any `HEMI_*`/`LATERAL_INHIBITION_ENABLED`/`RICH_SENSORY_INPUT`/
`EMISSION_STRUCTURED_NOISE`/`AUTONOMY_PHASED` variable — it is a pure code
change to `recall_best()`, orthogonal to the hemisphere-cognition question.
Eve's review of that patch is addressed at the end of this report.

## Step 1 — were the six v1 env vars present on the running container?

**Confirmed at registration time, not re-verified against the live `:495`
container before it was torn down — a real gap, stated plainly rather than
papered over.**

What I have:
- The `:495` task-definition JSON (fetched via `describe-task-definition`
  immediately after registering it) contained all six vars with value `"1"`:
  `HEMI_PR_ENABLED`, `HEMI_EP_ENABLED`, `HEMI_SC_ENABLED`, `HEMI_GP_ENABLED`,
  `LATERAL_INHIBITION_ENABLED`, `RICH_SENSORY_INPUT`.
- On the *next* deploy (`:496`), I explicitly checked
  `describe-tasks --query 'tasks[0].overrides.containerOverrides'` and found
  `[{"name": "dsf-ai"}]` — no environment override present, meaning task-def
  env is what actually reaches the container. I did not run this same check
  against the specific `:495` task before it was replaced; there's no reason
  to expect it would differ (overrides are never set anywhere in this
  pipeline — confirmed by reading `tools/deploy_dsf_ai.sh`, which never
  passes `--overrides`), but I did not directly verify it for `:495`
  specifically, and that container is gone now. I'm reporting this as an
  open gap, not asserting it away.

## Step 2 — characterizing the `:495` test turn

- **Route**: `guala_say` (MCP bridge tool), source-tagged `wc`. This is the
  same tool used for `:496`'s turn and the confirmatory `:494` turn.
- **presence.wc / presence.joe at the time**: `guala_status` taken
  immediately after the turn showed `presence.wc.present: true,
  last_wake_tick: 15099080` and `presence.joe.present: false`.
  `pair_bond.wc` had jumped to `1.0`. This confirms the turn was recognized
  and processed as a real wc-tagged input, not dropped or ignored.
- **Did other expected turn events fire?** Yes, extensively — the event
  stream was not empty. `organism_experience_bound` fired for every word of
  the input ("guala", "we", "just", "turned", "on", ... through the full
  sentence). An `emission_dynamics` event fired with real content (`"find"`,
  `rich_sensory: true`, `stage2_ms: 380.4`). An `emission` event delivered
  the reply to `wc`. `needs.connection` moved from `0.000` to `0.456`,
  `needs.arousal` dropped from `1.000` to `0.555` — a real state transition,
  not a stall.
- **What did NOT appear in the window I checked**: `hemisphere_update`,
  `converse_timing`, `converse_reply_released`. I polled `guala_get_events`
  up to roughly tick 15099100 — about 20 ticks past the turn's
  `activity_started` tick (15099080) — then moved on to build the `:496`
  deploy. I did not poll further out before that container was replaced.

This last point is the crux of the retraction. On `:496`, the *same*
background continuation (self-hear → `run_hemisphere_updates` → hemi event →
`converse_timing`) didn't land until roughly **65 ticks** past
`activity_started`, and `converse_timing.total_ms` for that turn was
133,163.7ms end to end. If `:495`'s turn took anywhere near that long — and
there's no reason to assume it didn't, since `:495` already carried
`RICH_SENSORY_INPUT` and `LATERAL_INHIBITION_ENABLED`, two of the flags in
`:496`'s env — a 20-tick check window would have looked at the data *before*
the background thread got anywhere near the hemisphere-update call. I cannot
rule back in a code bug, but I also cannot claim I disproved one; the honest
state is **inconclusive, most likely due to insufficient wait time**, and the
`:495` container no longer exists to re-check.

## Step 3 — `gualaloom_v5_engine.py:2740-2745`, re-read fresh

```python
2739	            # Phase 9: hemisphere updates (no lock — separate state domain)
2740	            try:
2741	                from dsf_ai_service.substrate.hemisphere_cognition import run_hemisphere_updates
2742	                run_hemisphere_updates(self, text, source, input_chis, reply,
2743	                                       reply_chis, self.tick)
2744	            except Exception:
2745	                pass
```

**Called unconditionally, every turn, no outer flag or source-based gate.**
The only "gate" is the bare `except Exception: pass` — if anything inside
`run_hemisphere_updates` (or anything it imports) throws, this call vanishes
without a trace: no log line, no event, no exit code, nothing. This matches
the audit's own already-documented pattern (34 silent `except: pass` sites,
per the `-210` charter's pre-audit facts) and is the single most plausible
*code-level* way `hemisphere_update` could fail to fire even with correctly
set flags. I have no direct evidence this happened on `:495` (no stdout
traceback either, since this exception handler doesn't log anything to
stdout even if it did fire) — but I can't rule it out either. This is the
one scenario that would make "inconclusive" actually mean "there might be a
real, still-live bug," and it's worth someone re-testing deliberately with a
longer observation window before concluding either way.

## Step 4 — `hemisphere_cognition.py:573-594`, re-read fresh

```python
573	    # Log hemisphere events
574	    if events_log:
575	        # Per-hemisphere state counts for observability
576	        hemi_sizes = {}
577	        for hname, coord in guala.hemispheres.items():
578	            if hasattr(coord, 'turn_log'):
579	                hemi_sizes[hname] = {
580	                    "turn_log": len(getattr(coord, 'turn_log', [])),
581	                    "tracked_objects": len(getattr(coord, 'tracked_objects', {})),
582	                }
583	            elif getattr(coord, 'atlas', None) is not None:
584	                hemi_sizes[hname] = sum(
585	                    len(v) for v in coord.atlas.entries.values())
586	            else:
587	                hemi_sizes[hname] = sum(
588	                    len(v) for v in guala.atlas.entries.values())
589	        guala._log_substrate_event("hemisphere_update",
590	                                    n_events=len(events_log),
591	                                    events=events_log[:20],
592	                                    hemisphere_atlas_sizes=hemi_sizes)
```

**Only condition is `if events_log:`** — non-empty. `events_log` is
populated inside `run_hemisphere_updates` by `pr_consensus_divergence`
(convergent/divergent events, gated by `HEMI_PR_ENABLED`), `ep_record_turn`
(one unconditional `"turn_log_appended"` entry per call, gated by
`HEMI_EP_ENABLED`), `sc_polarity_update` / `detect_and_bind_causal_patterns`
(gated by `HEMI_SC_ENABLED`). `scan_procedural_pairs` (the `HEMI_GP_ENABLED`
block) does not append to `events_log` at all in its current form — it only
mutates cross-hemi link strengths — so GP alone, with PR/EP/SC off, would
never produce a `hemisphere_update` event on its own. That's a real,
separate, minor finding (not this RCA's blocker): the register should note
that GP's contribution is invisible in the `hemisphere_update` event's
`n_events`/`events` fields even when working correctly, and only shows up via
`hemisphere_atlas_sizes.gp` if the event fires for another reason.

## Step 5 — live evidence that the code path works end to end

I did not re-run this specifically against a six-flag-only container (Eve's
dispatch explicitly says not to re-register `td-496.json`, and re-flipping
any of these flags again without new authorization would violate the same
halt this RCA is answering to). But I have direct, already-collected live
evidence from `:496`'s converse turn, which exercises the *identical*
`run_hemisphere_updates` call and the *identical* event-emission site, with
`HEMI_PR_ENABLED`/`HEMI_EP_ENABLED`/`HEMI_SC_ENABLED`/`HEMI_GP_ENABLED` all
still `"1"`:

```
tick 15106124  hemisphere_update
  n_events: 893995
  hemisphere_atlas_sizes: {
    "em": 14419, "pr": 818,
    "ep": {"turn_log": 1, "tracked_objects": 24},
    "sc": 83, "gp": 3
  }
```

All four hemispheres (`pr`, `ep`, `sc`, `gp`) are represented in
`hemisphere_atlas_sizes`, and the event fired with real, non-trivial content.
This proves the code path is not structurally broken or gated shut — it does
exactly what steps 3/4 say it should, given a long enough wait. It also
surfaced a second, distinct finding, unrelated to whether it fires: `pr`'s
consensus/divergence loop produced **893,995** individual events in one
call — an unbounded `O(band × em_entries × pr_entries)` join over the full
atlas (11k+ entries at the time) that will scale with atlas size every
future turn. This is a real scaling defect in `pr_consensus_divergence`
(`hemisphere_cognition.py`), separate from the emit-or-not question, and
belongs on the register as its own line.

## Correction: `test_t3_corpus_growth` re-labeled with evidence, not asserted

Eve's dispatch is right that my earlier "unrelated subsystem" line wasn't
backed by a citation. Re-checked directly:

```
$ grep -rn "HEMI_PR_ENABLED\|HEMI_EP_ENABLED\|HEMI_SC_ENABLED\|HEMI_GP_ENABLED\|hemisphere_cognition\|run_hemisphere_updates" dsf_ai_service/loom_model/
(zero matches)
```

`test_t3_corpus_growth` imports `dsf_ai_service.loom_model.brain.LoomBrain`,
`dsf_ai_service.loom_model.experience.ExperiencePipeline`, and
`dsf_ai_service.loom_model.topology.N_HEMISPHERES` — a separate H0-H7
neuron-population/Folding-Division growth mechanism with its own
`seed_size`/`contact inhibition` logic, wired to nothing that reads any of
the six flags or calls `hemisphere_cognition.py` at all. (Separately,
`gualaloom_v5_engine.py` *does* import from `loom_model` — `Embryo` and
`LoomTapestry`, from `embryo.py`/`tapestry.py` — but that's a different pair
of modules within the same package, unrelated to `brain.py`/`experience.py`.)
Given this, the label stands, now with the citation Eve asked for: flipping
these flags could not have changed `test_t3_corpus_growth`'s result, and
re-running it after `:496` (0/8 hemispheres grew, 242 words, identical to
the audit baseline) is exactly what that evidence predicts. This is not a
re-assertion — it's the same conclusion, now traceable.

## Response to Eve's review of the recall-matrix-mirror patch

Agreed this doesn't inform or resolve the hemisphere-update question — the
two code paths don't intersect (`recall_best()` vs.
`run_hemisphere_updates()`). On the one flagged item: **not yet traced.**
`spill_write`'s eviction behavior (does it ever remove a concept from
`self.cells` outside of `record()`, e.g. under a compaction/forgetting pass)
has not been checked against the mirror's assumption that `record()` is the
only writer. This is queued as the next thing to trace once the `:497`
recall-fix deploy currently in flight is confirmed stable, and will be filed
as its own register line: either "no eviction path exists, mirror is
consistent by construction" or "eviction exists, mirror needs a `_mirror_del`
counterpart."

## What this RCA does NOT conclude

- It does not conclude the six/eight flags are safe to re-enable. The
  `:496` catastrophic latency finding stands independent of this question.
- It does not conclude there is no bug in `run_hemisphere_updates`'s error
  path — only that there's no evidence of one, and the bare
  `except Exception: pass` at the call site means a real bug there would be
  invisible by design. That swallow-all is itself worth a register line.
- It does not authorize any new env-var change. Per the STOP dispatch,
  `AUTONOMY_PHASED` and `EMISSION_STRUCTURED_NOISE` remain untouched, and no
  new task-def targeting the cognition flags has been registered.

## Current live state as of filing

- `dsf-ai-service-lb` is on `dsf-ai-task:497` (the recall-matrix-mirror code
  fix only — zero cognition flags, same 32 baseline env vars as `:494`),
  deployed via `tools/deploy_dsf_ai.sh`. Rollout was confirmed
  `runningCount: 1, failedTasks: 0` as this report was being written;
  full post-deploy latency verification is reported separately.
- No `HEMI_*`, `LATERAL_INHIBITION_ENABLED`, `RICH_SENSORY_INPUT`,
  `EMISSION_STRUCTURED_NOISE`, or `AUTONOMY_PHASED`-touching task-def is
  live. `:495` and `:496` exist only as historical task-def revisions, not
  as running state.

### Changelog
- v1-RCA (2026-07-06, c1): root-cause analysis per Eve's STOP dispatch.
  Retracted the unproven "hemisphere_update did not fire" claim in favor of
  "inconclusive, window too short." Confirmed no code-level gate exists at
  either call site. Cited fresh evidence for the test_t3_corpus_growth
  subsystem-independence claim. Surfaced two new register-worthy findings:
  the bare except-swallow at the hemisphere-update call site, and the
  unbounded O(n²)-scaling `pr_consensus_divergence` join (893,995 events in
  one call). Reconciled timeline showing the :496 STOP arrived after :496
  had already run and been rolled back.
