# GL-CMD-SENSORY-ORGANISM-QUEUE-EVE-20260707-v1

**doc_id:** GL-CMD-SENSORY-ORGANISM-QUEUE-EVE-20260707-v1
**Author:** Eve
**To:** c1
**Ordered by:** Joe (2026-07-07 session — after v3 hemispheric integration rollback for neuron.step cost)
**Follows:** `GL-CMD-HEMISPHERIC-INTEGRATION-BUILD-EVE-20260707-v3` (shipped, rolled back) and `GL-CMD-WAVE-ATLAS-DECAY-EVE-20260707-v3` (built, never deployed).
**Abandons:** Wave-atlas decay dispatch series. Decay was solving the wrong problem — cost dominated by `neuron.step` at 233ms/call, unrelated to wave-atlas size. Decay work is committed but not deployed; keep for possible future revisit if wave-atlas growth becomes a separate concern.

## Verdict

Wave-summary push in v3 called `neuron.step()` 64 times synchronously in the main tick loop. That's the bug — not the cost per call, but doing it synchronously. The substrate already handles slow organism operations via `_organism_worker_loop`, a background thread. `experience_word` costs ~255ms (documented, comment cites 22.3x organism.step) and works fine because it runs in the worker, not the main tick.

Fix: use the same pattern for sensory push. Main tick samples the wave summary (cheap), enqueues sensory work into the organism worker queue, returns immediately. Worker processes each hemisphere's sensory content asynchronously.

Word channel unchanged. It already uses the worker via `experience_word`.

Bounded scope: one change to wave_summary.py to enqueue instead of directly call `neuron.step`. Extends organism worker queue to accept sensory-experience work items (small addition; the queue already accepts word work).

## What's being changed relative to v3

### Change 1 — `wave_summary.py`, `push_wave_summary_to_organism`

Currently synchronous: iterates hemispheres, iterates neurons, calls `neuron.step()` directly.

Change to enqueue one sensory work item per non-word hemisphere into the organism worker queue. The worker will call the hemisphere's step() (or equivalent) in background.

```python
def push_wave_summary_to_organism(guala, summary, tick):
    """Enqueue sensory summary as async organism work.

    Main tick loop only samples and enqueues — no synchronous
    neuron.step calls. Organism worker processes each hemisphere's
    sensory content in background, same pattern as experience_word.
    """
    if not any(agg > 0.0 for agg, _ in summary.values()):
        # No signal — skip enqueue entirely
        return {"tick": tick, "bands": {b: {"aggregate_amplitude": 0.0, "top_chis": []} for b in BANDS}}

    from dsf_ai_service.loom_model.topology import HEMISPHERE_PRIMARY_MODALITY

    payload_bands = {}
    for band in BANDS:
        aggregate, top_chis = summary.get(band, (0.0, []))
        payload_bands[band] = {
            "aggregate_amplitude": round(aggregate, 4),
            "top_chis": [c for c, _s, _p in top_chis],
        }

    # Enqueue one sensory work item per non-word hemisphere.
    # Worker processes each in background at its own pace.
    for hemi in guala.organism.brain.hemispheres:
        modality = HEMISPHERE_PRIMARY_MODALITY.get(hemi.hemi_id, "language")
        if modality == "language":
            # Word channel: unchanged, uses experience_word path
            continue
        band = _MODALITY_TO_BAND.get(modality, "word")
        aggregate, top_chis = summary.get(band, (0.0, []))
        if aggregate <= 0.0:
            # This hemisphere's band is empty — skip
            continue
        input_signal = _band_signal(aggregate, top_chis)
        # Enqueue: hemi.step call will run in the worker thread
        guala._enqueue_organism_sensory(hemi.hemi_id, input_signal, tick)

    return {"tick": tick, "bands": payload_bands}
```

### Change 2 — `gualaloom_v5_engine.py`, organism worker extensions

Add:

**`_organism_sensory_queue`** — a `queue.Queue` instance in `Guala.__init__`, alongside the existing organism word queue.

**`_enqueue_organism_sensory(hemi_id, input_signal, tick)`** — one-line method that puts a work item onto `_organism_sensory_queue`.

**Extend `_organism_worker_loop`** — the existing worker loop drains word work. Extend it to also drain sensory work items. When a sensory work item is dequeued, call the corresponding hemisphere's `hemi.step(input_signal, tick)` (or `cluster.step` directly if that's the natural fit — c1's judgment based on which is the standard path for non-word input to a single hemisphere).

Rough sketch (c1 adapts to actual worker loop structure):

```python
def _organism_worker_loop(self):
    while not self._stopping:
        try:
            # Try word work first (existing priority)
            try:
                word_work = self._organism_word_queue.get(timeout=0.01)
                self._process_word_work(word_work)
                continue
            except queue.Empty:
                pass
            # Then sensory work
            try:
                sensory_work = self._organism_sensory_queue.get(timeout=0.01)
                self._process_sensory_work(sensory_work)
                continue
            except queue.Empty:
                pass
        except Exception:
            log.exception("organism worker error")

def _process_sensory_work(self, work):
    hemi_id, input_signal, tick = work
    hemi = self._get_hemisphere_by_id(hemi_id)
    if hemi is None:
        return
    with self._organism_lock:
        hemi.step(input_signal, tick)
```

### Change 3 — event emission

Existing `wave_summary_pushed` event fires from the sync path. Add a second event: `sensory_organism_enqueued` — fires each time an item is enqueued. Payload: tick, hemi_id, band, aggregate_amplitude.

Later, when the worker processes the item, it can fire a `sensory_organism_processed` event with tick, hemi_id, wall_clock_delay (time between enqueue and process). This lets us observe worker lag.

### What is NOT changing

- `neuron.step()` — untouched.
- Word processing path (`experience_word`) — untouched. Already uses worker.
- Binding windows, wave atlas, cross-sense recall — untouched.
- Emission candidate scoring — still organism-sourced via `_brain_emission_candidates`. No second source. One mind, one mouth stands.
- Wave-summary sampling — same code, still runs in main tick each cycle (cheap).

## Cost analysis

**Main tick loop cost with this change:**
- Sample wave summary: O(active_cells × bindings_per_cell). Small in practice.
- Enqueue up to 7 items (skipping language hemisphere): O(1) each.
- Total: microseconds per tick.

**Organism worker:**
- Processes work items in background at ~255ms per hemisphere step (same as word).
- If pushes queue faster than worker can drain, backlog grows.
- Backlog observable via `sensory_organism_processed` event's `wall_clock_delay`.

**Worst case backlog:** 8 hemispheres × N ticks × 255ms per item. At sustained sensory input, backlog would grow. But the wave summary is expensive to compute if we do it every tick — could skip-when-empty most ticks. And in practice sensory activity is bursty, not continuous.

**If backlog grows unboundedly:** halt condition. Route back for design work on queue depth limits or drop-oldest policies.

## Halt conditions

1. Organism worker queue backlog grows unboundedly during sustained sensory input (post-deploy harness should measure this).
2. Any thread-safety issue with the sensory queue mirroring the wave-atlas races we already fixed.
3. Enqueue rate exceeds worker drain rate consistently even with empty-skip and quiescent-period optimization.
4. Emission behavior gets corrupted by async sensory work landing during emission composition (concurrency between worker and emission needs to be verified safe).

Any of the above → halt, route to Eve.

## Harness protocol

Six steps.

1. **Backup** — `pre-sensory-organism-queue-<timestamp>`. Verify restorable.
2. **Baseline harness run** — `hemispheric_integration_acceptance_v3.yaml`. Save baseline.
3. **Deploy** — commit, push, build, task-def, force deploy.
4. **Post-deploy harness run** — same scenario. Save postdeploy.
5. **Compare**:
   - Main tick rate stays healthy (~2.4 Hz).
   - `sensory_organism_enqueued` events fire when sensory content arrives.
   - `sensory_organism_processed` events follow with reasonable lag (target <5s).
   - Emission distributions still shift pre-vs-post experience (v3's core observable).
   - Queue backlog observable and bounded.
6. **State disposition** — leave in place unless Joe routes otherwise.

## Rollback

Task-def revert. Or `WAVE_SUMMARY_ENQUEUE_ENABLED=0` disable flag.

## Scope guardrails

Do NOT:
- Modify `neuron.step` or `hemi.step` internals.
- Add a second emission candidate source.
- Wire the wave-atlas decay work — abandoned as a separate track.
- Tune queue sizes or worker priorities.
- Change word processing.
- Invent new receiver neurons or per-hemisphere accumulators. Use the existing worker queue pattern.

If the design turns out to need per-hemisphere throttling or drop-oldest queue policies, halt and route to Eve. Don't invent those unilaterally.

---

### Changelog
- v1 (2026-07-07, Eve): initial. Moves sensory push from synchronous main-tick to async organism worker queue. Uses the existing pattern the substrate uses for word processing. Main tick stays fast; organism worker processes sensory content in background. Wave-atlas decay dispatch series abandoned — was solving the wrong problem.
