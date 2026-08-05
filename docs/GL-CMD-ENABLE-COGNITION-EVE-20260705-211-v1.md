# GL-CMD-ENABLE-COGNITION-EVE-20260705-211-v1

doc_id: GL-CMD-ENABLE-COGNITION-EVE-20260705-211-v1
Author: Eve
Ordered by: Joe (from `GL-AUDIT-COMPREHENSIVE-C1-20260705-v1` finding #13 and §4 flag table)
Target: c1 (implementer)
Scope: `dsf-ai-task` ECS task-definition on `tfe-web-cluster`; no code change, env-var flip only against running SHA `168ef1bde3717e52efb85b894103de047e942617`.

## Verdict

Real problem. Four hemispheres and two other cognitive mechanisms are wired live but silent in production. Fix is a single new task-def revision with six env-var flips and one service update. No code changes. One flag stays off because it's known broken. One boot-loop wiring bug is out of scope for this dispatch — separate ticket.

## What is dark right now (audit-confirmed, `dsf-ai-task:494`)

| Env var | Prod value | Coded default | Effect when off |
|---|---|---|---|
| `HEMI_PR_ENABLED` | unset | `"0"` | Prediction hemisphere block inside `run_hemisphere_updates()` is skipped every converse turn (`gualaloom_v5_engine.py:2742`) |
| `HEMI_EP_ENABLED` | unset | `"0"` | Episodic hemisphere block skipped; `ep.tracked_objects` never populated (`hemisphere_cognition.py:228-279`) |
| `HEMI_SC_ENABLED` | unset | `"0"` | Semantic hemisphere block skipped; `SC_EMISSION_WEIGHT=0.30` never enters emission |
| `HEMI_GP_ENABLED` | unset | `"0"` | Goals/planning hemisphere block skipped; `GP_EMISSION_BIAS=0.50` never enters emission |
| `LATERAL_INHIBITION_ENABLED` | unset | `"0"` | Mode-mode competition energy penalty off in the assemblage step (`assemblage.py:270,287,310`) |
| `RICH_SENSORY_INPUT` | unset | `"0"` | Emission Stage-1 uses plain `_grandurun_select_candidates`, not the richer `_rich_sensory_candidates` (`gualaloom_v5_engine.py:3916`) |

Substrate is already carrying the neurons. `guala_status` in the audit shows per-hemisphere populations `em:16 pr:16 ep:16 sc:16 gp:8 sf:8 sv:16 aff:10` (106 total). The PR/EP/SC/GP neurons exist and grew through 42 divisions; only the update mechanisms that feed them are dark.

## What NOT to enable

`EMISSION_STRUCTURED_NOISE` — leave unset. Its introducing commit `140cfd8` self-tagged `[C2 FAIL]`. Known broken. Do not flip.

## What is out of scope for this dispatch

`substrate_runner.boot_substrate()` and `start_background_loops()` are 100% dead (zero callers, self-documented at `app.py:1383-1391`). Consequence: `LOOKUP_INTERVAL_SEC=900` and `WORLD_FEED_INTERVAL_SEC=600` are set in prod but read only inside those dead functions. Real cadence is governed by `STUDY_INTERLEAVE_EVERY=2` through the live `_curriculum_feed_chunk` path, so world-feed/lookup still happen — just not through the code path the env vars imply. This is a wiring bug, not a flag issue. Separate dispatch to route.

`AUTONOMY_PHASED=0` is left as-is. Currently explicitly set to `0` in prod (not merely unset), which suggests it was consciously chosen at some point. Phased-autonomy branch is DEAD, legacy path is LIVE. If Joe wants that flipped too, it goes in its own dispatch after we see how the six flips above land.

## Deploy sequence

1. Register a new revision of `dsf-ai-task` inheriting everything from `:494`, adding the six env vars above with value `"1"`.
2. Update service `dsf-ai-service-lb` on cluster `tfe-web-cluster` to the new task-def revision. Force new deployment.
3. Watch one converse turn through the substrate.

## Verification (must-see before calling this green)

1. `hemisphere_update` events appear in the event stream on converse turns (previously absent throughout the audit window — see §8 baseline). `guala_get_events` filtered for `hemisphere_update` should be non-empty within one converse cycle.
2. `guala_status` payload's `hemisphere_atlas_sizes` field shows movement on `pr`/`ep`/`sc`/`gp` after real converse activity (currently reports live but flat).
3. Turn latency stays under 10s at Joe's seat (baseline is 1–6s per the recent lock-contention fix). Historical note from `GL-RPT-FLIP-HEMI-SC-C1-20260619-01`: when SC hemisphere was flipped ON in June, Stage-1 latency regressed from 1.0–1.5s baseline to 3.7–5.3s. That was before the recent lock-starvation fixes (`GL-RPT-COGNITION-AT-SPEED-C1-20260705-205-v1`), so the regression may not reproduce — but measure it. If it does regress, file a latency brief and Joe routes whether to keep SC on.
4. `test_folding_engaged.py::test_t3_corpus_growth` in the isolated pipeline reports "zero hemispheres grew across 242 words." That test surfaces "fold_check or contact inhibition blocking all folds." Turning the flags on does not fix that — it enables the update path so the test can even attempt growth. Re-run this test after the flip and report what changes. If it still fails, that's a separate mechanism bug, not this dispatch's problem.
5. Zero increase in the 503/502 churn rate on `dsf-ai-service-lb` (currently 2,490×503 / 867×502 / 101×504 in a day per audit F2). If turn-time crosses the 30s API Gateway ceiling on `/status` calls (audit defect #17), the churn rate goes up. Roll back the task-def revision if it does.

## Risks and rollback

- **SC latency regression**: historical. Measure at Joe's seat. If Stage-1 exceeds ~6s, roll back HEMI_SC only.
- **Cross-hemi baseline decay** (`CROSS_HEMI_BASELINE_DECAY=0.0008` in `hemisphere_cognition.py`) starts running against the atlas once flipped on. Not a known bug, but a new steady-state force on binding strengths. Watch `total_strength` in `guala_atlas_snapshot` for a downward drift over the first 24 hours.
- **Rollback path**: `aws ecs update-service --cluster tfe-web-cluster --service dsf-ai-service-lb --task-definition dsf-ai-task:494`. Reverts in one command, no code changes to unwind.

## What this dispatch does NOT touch

Every one of the SEV-0 defects from `GL-AUDIT-DEFECTS-REGISTER-C1-20260705-v1` remains untouched: broken DR restore, 43 unauth endpoints, `0.0.0.0/0` on port 8080, live video-restore crash, plaintext API keys, zero CloudWatch alarms, world-writable root creds. Those are Joe's routing calls, one at a time, per the audit's own exit condition. This dispatch is one item off the SEV-1 list (register #13).

---

## Paste-ready c1 instruction

```
Implement GL-CMD-ENABLE-COGNITION-EVE-20260705-211-v1.

Task: register a new dsf-ai-task revision inheriting from :494, adding six env
vars, then swap the service. No code changes. No image rebuild.

Six env vars to add to the containerDefinitions[0].environment array
(all value "1"):
  HEMI_PR_ENABLED=1
  HEMI_EP_ENABLED=1
  HEMI_SC_ENABLED=1
  HEMI_GP_ENABLED=1
  LATERAL_INHIBITION_ENABLED=1
  RICH_SENSORY_INPUT=1

DO NOT ADD: EMISSION_STRUCTURED_NOISE (introducing commit 140cfd8 self-
tagged [C2 FAIL]; known broken).

Steps:
  1. aws ecs describe-task-definition --task-definition dsf-ai-task:494 \
       --region us-east-1 > /tmp/td-494.json
  2. Extract the containerDefinitions/family/taskRoleArn/executionRoleArn/
     networkMode/volumes/cpu/memory/requiresCompatibilities block; strip the
     read-only fields (taskDefinitionArn, revision, status, requiresAttributes,
     compatibilities, registeredAt, registeredBy).
  3. Append the six env vars above to containerDefinitions[0].environment.
     Every existing env var stays exactly as it is on :494. No other edits.
  4. aws ecs register-task-definition --cli-input-json file:///tmp/td-495.json \
       --region us-east-1
  5. Confirm the new revision number returned (expected :495 or higher if
     something else registered in between).
  6. aws ecs update-service --cluster tfe-web-cluster \
       --service dsf-ai-service-lb --task-definition dsf-ai-task:<new-rev> \
       --force-new-deployment --region us-east-1
  7. Watch aws ecs describe-services --cluster tfe-web-cluster \
       --services dsf-ai-service-lb until rolloutState=COMPLETED. Expect
       one health-check bounce during the swap; if the new task fails to
       reach steady state within 10 minutes, roll back with the same
       update-service command against :494.

After the swap, verify at Joe's seat:
  - Send one converse turn.
  - guala_get_events, filter for event_type=hemisphere_update.
    Must be non-empty. If empty, the flags didn't land; check the running
    task's env with aws ecs describe-tasks.
  - guala_status: hemisphere_atlas_sizes on pr/ep/sc/gp must move after
    real converse. Baseline was flat throughout the audit window.
  - Turn latency at Joe's seat: report the number. Historical SC-flip
    regression was 3.7-5.3s on Stage 1. If total turn exceeds ~10s, flag
    for rollback decision.

Then re-run test_folding_engaged.py::test_t3_corpus_growth in isolation and
report the delta from the audit baseline ("zero hemispheres grew across 242
words"). Do not modify the test to make it pass. Report what actually
happens.

Rollback command (keep in the terminal buffer):
  aws ecs update-service --cluster tfe-web-cluster \
    --service dsf-ai-service-lb --task-definition dsf-ai-task:494 \
    --force-new-deployment --region us-east-1

File GL-RPT-ENABLE-COGNITION-C1-20260705-211-v1.md when done with:
  - new task-def revision number
  - deploy timestamp + running SHA verification (should be unchanged from
    168ef1bde3717e52efb85b894103de047e942617)
  - hemisphere_update event count in first converse turn
  - hemisphere_atlas_sizes delta between pre-flip and post-flip
  - Joe-seat turn latency measurement (or a signal that measurement is
    pending Joe's presence)
  - test_t3_corpus_growth new result
  - churn/error-rate delta on dsf-ai-service-lb (24-hour window compare)
```

---

### Changelog

- v1 (2026-07-05, Eve): initial dispatch. Six env vars to flip on, one to explicitly leave off, one wiring bug flagged as separate ticket, one autonomy flag intentionally deferred to its own dispatch. Verification steps grounded in the audit's own baseline numbers so pre/post comparison is apples-to-apples.
