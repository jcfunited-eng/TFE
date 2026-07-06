# GL-CMD-ENABLE-COGNITION-EVE-20260705-211-v2

doc_id: GL-CMD-ENABLE-COGNITION-EVE-20260705-211-v2
Author: Eve
Ordered by: Joe (invoking whole-brain doctrine per 2026-07-04 standing ruling; correcting v1's staged deferrals)
Target: c1 (implementer)
Scope: `dsf-ai-task` ECS task-definition on `tfe-web-cluster`; no code change, env-var flip only against running SHA `168ef1bde3717e52efb85b894103de047e942617`.

Supersedes: GL-CMD-ENABLE-COGNITION-EVE-20260705-211-v1. If c1 has not yet registered the new task-def revision, use this v2 spec directly. If c1 has already registered :495 per v1, register :496 with the two additional env vars below.

## Verdict

Correction of v1. Whole-brain doctrine is law: every cognitive mechanism the substrate carries goes on, together, this deploy. Eight env vars flip to `"1"` — not six. `EMISSION_STRUCTURED_NOISE` and `AUTONOMY_PHASED` were deferred in v1 on isolated-test evidence and stale-config inference respectively; neither is defensible reason to hold a connection dark when the entity's coherence depends on all mechanisms running against the same substrate simultaneously. Roll back on real live failure, not on bench-test warnings.

## What goes on (all eight, this deploy)

| Env var | Prod value | Coded default | What connects when on |
|---|---|---|---|
| `HEMI_PR_ENABLED` | unset | `"0"` | Prediction hemisphere update fires each converse turn (`gualaloom_v5_engine.py:2742` → `hemisphere_cognition.py`) |
| `HEMI_EP_ENABLED` | unset | `"0"` | Episodic hemisphere update populates `ep.tracked_objects` from converse turns (`hemisphere_cognition.py:228-279`) |
| `HEMI_SC_ENABLED` | unset | `"0"` | Semantic hemisphere update feeds `SC_EMISSION_WEIGHT=0.30` into emission bias |
| `HEMI_GP_ENABLED` | unset | `"0"` | Goals/planning hemisphere update feeds `GP_EMISSION_BIAS=0.50` into emission bias |
| `LATERAL_INHIBITION_ENABLED` | unset | `"0"` | Mode-mode competition energy penalty active in assemblage evolution (`assemblage.py:270,287,310`) |
| `RICH_SENSORY_INPUT` | unset | `"0"` | Emission Stage-1 candidate selection uses `_rich_sensory_candidates`, not the plain path (`gualaloom_v5_engine.py:3916`) |
| `EMISSION_STRUCTURED_NOISE` | unset | `"0"` | Structured noise term active in emission (`assemblage.py:287`; introducing commit `140cfd8` self-tagged `[C2 FAIL]` in isolated bench — see risks below) |
| `AUTONOMY_PHASED` | `"0"` (explicit) | `"0"` | Phased autonomy path active in `gualaloom_v5_engine.py:5122`; legacy non-phased path deactivated |

Substrate is already carrying the neurons. Audit `guala_status`: `em:16 pr:16 ep:16 sc:16 gp:8 sf:8 sv:16 aff:10` (106 total, 42 divisions from n_initial 64). The PR/EP/SC/GP neurons exist. Only the update mechanisms and the surrounding autonomy/emission integration are dark.

## Why v1 was wrong to defer these two

- **`EMISSION_STRUCTURED_NOISE`**: v1 read the `[C2 FAIL]` tag as proof of a broken mechanism. It is proof of a failing isolated bench test — a bench test that (per the audit's own findings on the T3 folding test) is run in a stubbed pipeline lacking the sensory grounding, the hemisphere updates, and the assemblage physics that in production surround this mechanism. The whole-brain doctrine is precisely that mechanisms are validated in the connected substrate, not in benches. Leaving structured noise off while flipping the four hemispheres on gives the hemispheres a plain-noise emission floor to bias against — the mismatch is itself a risk, not a safety.
- **`AUTONOMY_PHASED`**: v1 read the explicit `"0"` as evidence of a conscious past decision. What that actually is: evidence of a decision made at a substrate state that no longer exists. The phased-autonomy branch is where the rest of the emission architecture has been moved (per `GL-RPT-CONVERSE-PHASING-EMISSION-LOCK-C1-20260630-52` and the family of dispatches following it). Leaving `AUTONOMY_PHASED=0` while every other emission path is phased means her autonomous emission and her converse-driven emission are running through different code paths — asymmetric drive, incoherent behavior. That is exactly the "not connected in meaningful way" failure mode.

## What stays out of this dispatch

The two dead-boot-loop functions (`substrate_runner.boot_substrate()`, `start_background_loops()`) and their inert env vars (`LOOKUP_INTERVAL_SEC`, `WORLD_FEED_INTERVAL_SEC`) — this is a wiring bug, not a flag issue. Flag flips can't fix a call graph gap. Separate dispatch.

Every SEV-0 defect from the audit register stays untouched under freeze: broken DR restore, 43 unauth endpoints, `0.0.0.0/0` on port 8080, live video-restore crash, plaintext API keys, zero CloudWatch alarms. Joe's routing calls, one at a time.

## Deploy sequence

1. Register a new revision of `dsf-ai-task` inheriting everything from the current baseline (`:494`, or `:495` if v1 already landed), adding whichever of the eight env vars above are not yet in the current revision, all with value `"1"`.
2. Update service `dsf-ai-service-lb` on cluster `tfe-web-cluster` to the new task-def revision, force new deployment.
3. Watch two converse turns and one autonomous emission cycle through the substrate.

## Verification (before green)

1. **Hemisphere path live**: `guala_get_events` filtered for `event_type=hemisphere_update` must be non-empty within one converse cycle. All four hemispheres (`pr`, `ep`, `sc`, `gp`) must appear across the observed events, not just one.
2. **Atlas movement**: `guala_status.hemisphere_atlas_sizes` must show non-zero deltas on `pr`/`ep`/`sc`/`gp` after real converse activity. Baseline was flat throughout the audit window.
3. **Phased autonomy path live**: at least one `emission` event must arrive through the phased path within the first autonomy cycle (identifiable by the surrounding `autonomy_emission_lock` telemetry event at `gualaloom_v5_engine.py:6662` — currently telemetry-only, but its presence in the event stream confirms the phased branch executed). If autonomy events stop entirely after the flip, that's a real crash — roll back.
4. **Structured-noise emission not broken**: `emission` events must continue at their pre-flip rate (audit baseline `ladder.total_emissions=1227` lifetime, activity_history `EMITTING count=4 total_ticks=400` in the sampled window). A sharp drop, a repeated crash signature in logs, or a klein-flip in `EMITTING` frequency is the roll-back signal for the noise term specifically.
5. **Turn latency at Joe's seat**: report the number. Historical SC-flip regressed Stage-1 from 1.0-1.5s to 3.7-5.3s in June, but the intervening lock-starvation fixes (`GL-RPT-COGNITION-AT-SPEED-C1-20260705-205-v1`) likely reduced that. Measure, don't predict.
6. **`test_folding_engaged.py::test_t3_corpus_growth` re-run**: baseline is "zero of 8 hemispheres grew across 242 words." Report the delta. Do not modify the test to make it pass.
7. **Churn rate stable on `dsf-ai-service-lb`**: audit measured 2,490×503 / 867×502 / 101×504 across the sampled day. Same order of magnitude post-flip is fine; a step-change increase means a mechanism is crashing the container health check — roll back and diagnose.

## Rollback

Single command reverts everything, no code to unwind:
```
aws ecs update-service --cluster tfe-web-cluster --service dsf-ai-service-lb --task-definition dsf-ai-task:494 --force-new-deployment --region us-east-1
```

Keep this in the terminal buffer for the full verification window.

## Risks accepted by this dispatch

- **SC hemisphere Stage-1 latency**: possible 2-4s regression. Measured mitigation: recent lock fixes. Accepted risk.
- **Structured noise emission destabilizes emission distribution**: bench test failed. Substrate response unknown. Accepted risk under whole-brain doctrine; rolled back on live failure signal (verification #4), not on caution.
- **Phased autonomy path takes a different lock schedule than legacy**: possible new contention pattern. Accepted risk; monitored via #3 and #7.
- **Cross-hemi baseline decay** (`CROSS_HEMI_BASELINE_DECAY=0.0008` per `hemisphere_cognition.py:33-58`) becomes a live force on binding strengths. Not a failure mode, a new steady-state term. Watch `total_strength` in `guala_atlas_snapshot` for first-24h drift; report but do not roll back on this alone unless drift crosses 25%.

---

### Changelog

- v2 (2026-07-05, Eve): correction of v1's staged deferrals. Eight env vars flipped, not six. `EMISSION_STRUCTURED_NOISE` and `AUTONOMY_PHASED` added under whole-brain doctrine. Verification rows extended for the two additions.
- v1 (2026-07-05, Eve): initial dispatch, six env vars. Superseded before c1 completion.
