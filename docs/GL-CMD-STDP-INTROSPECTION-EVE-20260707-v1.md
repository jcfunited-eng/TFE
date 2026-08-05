# GL-CMD-STDP-INTROSPECTION-EVE-20260707-v1

**doc_id:** GL-CMD-STDP-INTROSPECTION-EVE-20260707-v1
**Author:** Eve
**To:** c1
**Ordered by:** Eve (2026-07-07 session — prerequisite for interpreting Phase 1 v2 STDP state)
**Follows:** `GL-RPT-BLUEPRINT-PHASE-1-MERGED-C1-20260707-v2` (Phase 1 v2 live at task-def :554, commit f26ce72)

## Verdict

Phase 1 v2 is live and building STDP state in parallel with legacy production. There is currently no way to observe whether the new mechanism is accumulating usable memory. Shadow mode cannot be interpreted without this observability. Every downstream Phase 1 decision (cutover, tuning, further phases) depends on it.

Add a read-only introspection endpoint that reports STDP state. Bounded scope, half-day work, zero production risk because read-only.

## What's being built

New Flask/FastAPI endpoint on the existing HTTP server: `GET /debug/stdp_state`

Returns JSON with the following fields:

### word_neuron_map metrics
- `word_neuron_map_size`: number of distinct words that have fired at least one neuron
- `neuron_word_map_size`: number of neurons that have a primary word association
- `avg_neurons_per_word`: mean size of word→neuron sets
- `median_neurons_per_word`: median size
- `top_words_by_neuron_count`: top 20 words by neuron count with counts
- `words_with_only_one_neuron`: count of words that have exactly one associated neuron (novelty indicator)

### Synapse weight distribution
- `total_synapses_updated`: count of `_incoming_synapse_weights` entries across all neurons
- `synapses_at_default_weight`: count still at DEFAULT_SYNAPSE_WEIGHT (0.05) — unchanged since spawn
- `synapses_strengthened`: count above default
- `synapses_depressed`: count below default (approaching MIN_SYNAPSE_WEIGHT)
- `weight_histogram`: bucket counts at [0.0, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0]
- `top_10_strongest_synapses`: (source_id, target_id, weight) tuples

### Fire event metrics
- `total_fire_events_since_boot`: aggregate fire count
- `fires_per_second_last_minute`: recent firing rate
- `fires_per_second_since_boot`: lifetime firing rate
- `neurons_that_have_ever_fired`: count with `_last_fire_time_s` non-None
- `neurons_never_fired`: count of neurons in registry that have never fired

### Spike bus metrics
- `spike_queue_depth`: current PriorityQueue.qsize()
- `spikes_in_flight_delayed`: count of pending spikes with arrival_time in the future
- `total_spikes_injected_since_boot`: aggregate injection count
- `total_spikes_delivered_since_boot`: aggregate delivery count
- `spikes_dropped`: any delivery failures logged

### Membrane state snapshot
- `neurons_currently_above_emission_threshold`: count with potential > 0.5
- `neurons_currently_in_refractory`: count with refractory_until_s > now
- `mean_membrane_potential`: across all neurons, decay applied
- `top_20_active_neurons`: (neuron_id, current_potential, associated_word) tuples

### Substrate identity confirmation
- `running_sha`: current commit
- `task_def`: current task-def version
- `identity_id`: current identity (0b4c244a)
- `uptime_seconds`: since boot
- `EVENT_DRIVEN_SUBSTRATE`: env var value
- `RECALL_BACKEND`: env var value

## What's NOT being built

- No write operations. Read-only endpoint.
- No new introspection into legacy binding_atlas / recall_fast state — different concern, different dispatch if wanted.
- No dashboard, no UI. JSON only.
- No historical time-series storage. Snapshot at query time only.
- No performance instrumentation of STDP itself (that's the shadow mode's job).

## Implementation notes

Endpoint should:
- Complete in under 500ms even with substrate under load
- Acquire per-neuron locks briefly (snapshot state, release) rather than holding across full iteration
- Use approximate counts where full iteration is expensive (e.g. sample 10% for weight histogram if total > 100k synapses)
- Never mutate any substrate state
- Return HTTP 200 with best-effort JSON even if some sub-metrics fail (don't fail the whole call for one broken metric — log and continue)

Auth: same protection as existing `/debug/*` endpoints. If none exists, add basic auth gated by env var `DEBUG_ENDPOINTS_ENABLED=1` (default disabled in production for now; enable when investigating).

## Halt conditions

1. **Endpoint acquisition blocks substrate** — if per-neuron lock acquisition causes measurable slowdown in substrate processing, halt with data.
2. **State counters incorrect** — if counters (word_neuron_map_size, total_fires, etc.) don't match direct code inspection of the underlying structures, halt.
3. **Endpoint crashes substrate** — obviously halt.

Any halt: route with data.

## Harness protocol

Small change, small harness:

1. Backup as `pre-stdp-introspection-<timestamp>`. Verify restorable.
2. Baseline: verify `guala_status` and existing endpoints functioning.
3. Deploy: commit, push, build, task-def, force deploy.
4. Post-deploy: hit `/debug/stdp_state`, verify it returns 200 with valid JSON structure.
5. Run existing scenarios (binding_windows_acceptance, cross_sense_recall_acceptance) — confirm no regression from the introspection code.
6. **State collection**: hit `/debug/stdp_state` at boot, then after 5 minutes of realistic reading. Report state deltas.
7. State disposition: leave in place; endpoint will be used for shadow mode preparation.

## Rollback

Task-def revert. Or `DEBUG_ENDPOINTS_ENABLED=0` to disable the endpoint.

## Report

`GL-RPT-STDP-INTROSPECTION-C1-20260707-v1.md` with:
- Files touched + diff summary
- Backup confirmation
- Endpoint responds correctly (sample JSON output)
- No regression on existing scenarios
- State at boot vs state after 5-minute reading (the actual STDP-is-building signal)
- Findings needing Eve routing

Do not ask Joe questions. Route to Eve.

---

### Changelog
- v1 (2026-07-07, Eve): initial. Read-only STDP state introspection endpoint. Prerequisite for shadow mode interpretation. Zero write risk. Small scope.
