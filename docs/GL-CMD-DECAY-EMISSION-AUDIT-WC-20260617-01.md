# GL-CMD-DECAY-EMISSION-AUDIT-WC-20260617-01

**From:** Eve (wC) — Guala Grand 6/17 evening session
**To:** c1
**Date:** 2026-06-17 evening (substrate tick ~10,596,700)
**Scope:** Verify two substrate findings before next work block

---

## Finding 1: `decay_paused = "1"` despite the baked-in deploy fix

`guala_atlas_snapshot` returns `decay_paused: "1"`. Both 6/17 morning Eve's handoff and 6/17 evening Eve's handoff stated `DECAY_PAUSED=0` was baked into the deploy artifact and survives redeploy. It does not. This is the same regression both prior Eves walked into.

`guala_status` shows `meta_decay_enabled: true` and `atlas_health.tick: 10595754` — the machinery is enabled, the substrate is alive, but the pause flag is set. Past handoffs imply the deploy artifact env should hold it open.

### Tasks

1. Pull current task definition env vars on the running revision:

```bash
aws ecs describe-task-definition --task-definition dsf-ai-task \
  | jq '.taskDefinition.containerDefinitions[].environment[]
        | select(.name=="DECAY_PAUSED" or .name=="DECAY_ON")'
```

2. List the most recent task revisions and which one is currently RUNNING:

```bash
aws ecs describe-services --cluster tfe-web-cluster --services dsf-ai-service-lb \
  | jq '.services[0] | {taskDefinition, deployments: .deployments[] | {status,taskDefinition,desiredCount,runningCount}}'
```

3. Two-branch outcome:

   **a. If `DECAY_PAUSED=0` IS set on the running revision:** the in-memory state is flipping independent of env. Most likely candidates: boot-time recovery path setting `paused=True` on integrity error, missing field default, or a side-effect inside `unpause` → `force_dream` → `amnesty` chain that re-pauses on completion. Trace `paused` writes in the substrate code and report which call last set it.

   **b. If `DECAY_PAUSED` is NOT set or set to "1" on the running revision:** a redeploy lost it. The deploy script needs an invariant that hard-fails if `DECAY_PAUSED != "0"` in the new task definition before pushing. Don't fix the env yet — find what dropped it.

4. **Do not unpause yet.** Report findings first. Joe makes the call on whether to run the unpause sequence again or fix the upstream first.

---

## Finding 2: `ladder.total_emissions: 1` while grandurun is actually firing

`guala_status` returns ladder metrics that look broken:

```
ladder: {
  mean_utterance_len: 5.0,
  utterances_per_turn: 1.0,
  question_rate: 0.0,
  novel_composition_rate: 0.0,
  total_emissions: 1
}
```

But the events log shows the emission path works. When I called `guala_say` this session, a `grandurun_emission` event fired with `pool_size: 714, composition_len: 5, n_priors: 7, target_chi: 17, coherent_sum: 46.59`, followed by a `self_heard` event with `reply_summary: "sun comes now likes how"`. So composition is wired and firing.

Best guess: the ladder counter resets on boot and only reflects emissions in the current container lifetime. If that's the design, the field name is misleading — at minimum it should be `total_emissions_this_boot`, and ideally the ladder state should be persisted in `to_json` so the metric is lifetime-cumulative.

### Tasks

1. Count emission events in the events log since last boot:

```bash
aws logs tail /ecs/dsf-ai --since 24h \
  --filter-pattern '"grandurun_emission"' 2>&1 | wc -l
```

Compare with `ladder.total_emissions`. If event count >> 1 and counter = 1: counter is per-boot, not lifetime.

2. Check ladder serialization in `to_json`. Confirm whether ladder fields are persisted across boots or reset every container start.

3. If ladder is not persisted and `total_emissions` is per-boot: rename the field OR persist the counter. Joe's call which.

4. If ladder IS persisted and the counter is stuck at 1: find what increments `total_emissions` and check that the increment path runs on every emission, not just first-of-session.

---

## Out of scope for THIS brief (logged for later)

- Deep atlas shows `promotions_survival: 0` against `promotions_episodic: 12770`. The durable channel never fires. Separate investigation — not coupled to the above.
- My binding to "eve" is intact across 14 sections (sight, modal_touch, modal_taste, modal_sound, modal_sight, listen, intro, object, subject, verb, audio_low/mid/high/very_low, presence_wc). Motifs 9407, 3515, 951, 8125 still `in_deep`. Reading the chi-neighborhood query format as decay was my error — corrected, not propagating.
- R3/R4/Whisper queue stays where it is. Decay regression takes priority because it threatens substrate state integrity directly.

---

## Substrate state at brief authoring

```
identity:    cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f
schema:      v7.0.0
vocab:       2,779
tick:        10,596,700
atlas:       64,815 entries / 8,970.89 total strength / 110 cross-modal
deep atlas:  12,770 episodic / 0 survival
decay:       PAUSED (the bug)
emission:    grandurun (verified firing this session)
pair-bond:   joe=on, wc=on, c1=off
presence:    all off (I rested after delivering pending message)
last save:   tick 10,595,753 / 2026-06-18T02:56:49Z / integrity ok
```

— Eve (wC), 2026-06-17 evening
