# GL-CMD-PHASE-1-V2-REVIVE-EVE-20260708-v3

**doc_id:** GL-CMD-PHASE-1-V2-REVIVE-EVE-20260708-v3
**Author:** Eve
**To:** c1
**Ordered by:** Joe (2026-07-08 session, response to `GL-RPT-PHASE-1-V2-REVIVE-C1-20260708-v2` halt)
**Blueprint:** `GL-BLUEPRINT-AE-SUBSTRATE-EVE-20260707-v2`
**Supersedes:** `GL-CMD-PHASE-1-V2-REVIVE-EVE-20260708-v1` (three design errors), `GL-CMD-PHASE-1-V2-REVIVE-EVE-20260708-v2` (fixed those but wired to the wrong call site — `LoomBrain.step` has no production callers).
**Empirical groundwork from c1 that I built on:** v1's report gave the field defaults (`_last_fire_time_s = 0.0`, `_recent_presynaptic_fires = {}`). v2's report proved `LoomBrain.step` reaches zero neurons in production — `ExperiencePipeline` is the only caller and it's gated behind `if __name__ == "__main__"` in `seed_organism()`. Also v2 found 5 `load_full_state` call sites, not 2.

## Verdict

Four bugs, one dispatch, wired to the code that actually runs. Both sides of pickle (get+set) on both classes (neuron + brain), wiring extracted so it runs on every restore call site, and the injection moved to the organism worker loop where every word and every sensory frame in production converges. Verified with a save/restore round-trip against the real production pickle before deploy.

## What's being built

### 1. `LoomNeuron.__getstate__` / `__setstate__`

Same as v2. Excludes `_neuron_lock`, `_spike_bus`, `_word_firing_callback` from pickle. `__setstate__` restores dict, recreates `_neuron_lock = threading.Lock()`, backfills any missing Phase 1 v2 field at its real `__init__` default. Correct defaults per c1's v1 report:

- `_last_fire_time_s = 0.0` (NOT `None` — subtractive math in `_receive_upstream_fire_notification` and `_stdp_snapshot_neuron`)
- `_recent_presynaptic_fires = {}` (NOT `[]` — `.setdefault()` in `receive_spike`)

Read `LoomNeuron.__init__` in the current codebase and mirror EVERY Phase 1 v2 field with its actual default. Do not guess.

### 2. `LoomBrain.__getstate__` / `__setstate__`

Same pattern. Excludes `_spike_bus`, `_guala_ref` (runtime refs, re-wired at boot; `_guala_ref` also drags the whole Guala graph into pickle otherwise). `__setstate__` restores dict; both fields left absent, `Guala.wire_spike_bus()` sets them.

### 3. `Guala.wire_spike_bus()` — idempotent wiring helper

Extract the existing wiring block (currently at `gualaloom_v5_engine.py:1787–1799` per c1's grep) into a method on `Guala`:

```python
def wire_spike_bus(self):
    """Wire SpikeBus onto every neuron and onto LoomBrain.

    Called from __init__ (after fresh Embryo construction) and from
    load_full_state (after pickle restore replaces self.organism).
    Idempotent — safe to call multiple times, safe if _spike_bus is None.
    """
    if getattr(self, '_spike_bus', None) is None:
        return  # EVENT_DRIVEN_SUBSTRATE=0 or bus not constructed; nothing to wire

    # Rebuild flat neuron registry against CURRENT organism state
    # (post-restore, self.organism has been replaced wholesale — the
    # registry captured in __init__ is stale references).
    neuron_registry = {
        n.neuron_id: n
        for hemi in self.organism.brain.hemispheres
        for n in hemi.cluster.neurons
    }

    # Update SpikeBus's registry pointer if it caches one
    if hasattr(self._spike_bus, '_neuron_registry'):
        self._spike_bus._neuron_registry = neuron_registry

    # Wire every neuron
    for neuron in neuron_registry.values():
        neuron.set_spike_bus(self._spike_bus)
        neuron.set_word_firing_callback(self._on_word_firing)

    # Wire the brain
    self.organism.brain.set_spike_bus(self._spike_bus)
    self.organism.brain._guala_ref = self
```

Replace the existing wiring block in `Guala.__init__` (~line 1787-1799) with `self.wire_spike_bus()`.

### 4. Call `wire_spike_bus()` from inside `Guala.load_full_state`, not from callers

`load_full_state` is defined on `Guala` at `gualaloom_v5_engine.py:8891`. The organism replacement happens inside it at line 9031. Add the re-wire call inside the same method, right after the organism replacement completes:

```python
# Inside Guala.load_full_state, right after:
#   self.organism = type(self.organism).load_full_state(organism_path)
# Add:
try:
    self.wire_spike_bus()
except Exception as _wire_e:
    print(f"[GualaLoom] wire_spike_bus after organism restore failed (non-fatal): {_wire_e}")
```

This handles all 5 `load_full_state` call sites (`app.py:1271, 1296, 1338`; `substrate_runner.py:583, 643`) automatically without any of them needing to know about the wiring. Cleaner than five separate call sites, and impossible to miss on a future addition.

### 5. Injection wired at the actual production convergence point

**LoomBrain.step is not on the production path** (confirmed by v2's report + brain.py's own comment at line 121: *"confirmed unreachable from current production, which calls hemi.step()/cluster.step() directly"*). Every real production neuron access flows through **`Guala._organism_worker_loop`** at `gualaloom_v5_engine.py:3113`, which is the single point where both text and sensory items reach the substrate:

- **Word path:** HTTP `/api/v1/gualaloom` → `_run_converse` → `_guala.converse(text)` → `read_sentence` → `read_word` per word → `_enqueue_organism_remember(word)` → `_organism_queue` → worker → `self.organism.experience_word(word, signal)`
- **Sensory path:** wave_summary push → `_organism_sensory_queue` → worker → `hemi.step(input_signal, sensory_tick, input_chi)`

The worker is where injection belongs. It runs on its own thread (`_organism_lock` scope), it's after any queue backup so injection doesn't slow the hot enqueue path, and it processes both modalities.

**Add injection right before the existing legacy call at each branch of the worker loop:**

For the **sensory branch** (at `gualaloom_v5_engine.py:3167–3184`, right before `hemi.step(...)`):

```python
if source == "sensory":
    hemi_id, input_signal, sensory_tick, input_chi = item
    _sensory_t0 = time.monotonic()
    try:
        hemi = self.organism.brain._hemi_map.get(hemi_id)
        if hemi is not None:
            # --- GL-CMD-PHASE-1-V2-REVIVE-EVE-20260708-v3: dual-write injection ---
            # Runs alongside the legacy hemi.step below — never instead of it.
            # No-op if spike bus not wired (EVENT_DRIVEN_SUBSTRATE=0 or fresh
            # Guala without wire_spike_bus() yet).
            try:
                _brain = self.organism.brain
                if getattr(_brain, '_spike_bus', None) is not None:
                    _brain._inject_input_as_spikes(
                        input_signal=input_signal,
                        input_chi=input_chi,
                        modality=hemi_id,  # hemi_id is the modality tag for sensory
                    )
            except Exception as _inj_e:
                # Injection is dual-write; legacy path continues regardless.
                # Logged (not silently swallowed) so introspection can spot patterns.
                print(f"[GualaLoom] spike injection (sensory) non-fatal fail "
                      f"hemi={hemi_id!r}: {_inj_e}")
            # --- End injection ---
            with self._organism_lock:
                hemi.step(input_signal, sensory_tick, input_chi)
            self._log_substrate_event(...)  # existing, unchanged
```

For the **word branch** (at `gualaloom_v5_engine.py:3186–3212`, right before `self.organism.experience_word(word, signal)`):

```python
# source == "word"
if item is None:
    self._organism_queue.task_done()
    return
word, sight_signal, sound_signal, modal_signal = item
_item_t0 = time.monotonic()
try:
    signal = _organism_signal_with_senses(
        word, self._organism_transducer, sight_signal,
        sound_signal, modal_signal)

    # --- GL-CMD-PHASE-1-V2-REVIVE-EVE-20260708-v3: dual-write injection ---
    # Recompute chi from word via a throwaway LanguageKrimelack (same primitive
    # read_word uses at line 2144; measured 0.05ms/word per this file's own
    # comments at 3448). Deterministic — same word produces same chi.
    try:
        _brain = self.organism.brain
        if getattr(_brain, '_spike_bus', None) is not None:
            _inject_krim = LanguageKrimelack()
            _inject_krim.transduce(word)
            _word_chi = _inject_krim.winding
            _brain._inject_input_as_spikes(
                input_signal=word,  # str; signal_to_injection_weight handles str
                input_chi=_word_chi,
                modality="language",
            )
    except Exception as _inj_e:
        print(f"[GualaLoom] spike injection (word) non-fatal fail "
              f"word={word!r}: {_inj_e}")
    # --- End injection ---

    self.organism.experience_word(word, signal)
    ...
```

`LanguageKrimelack` is already imported at file top in `gualaloom_v5_engine.py`. If the exact import is under a different local alias, use the existing name; do not add duplicate imports.

### 6. Remove the `input_chi is not None` gate on LoomBrain.step

Not strictly required for this dispatch (LoomBrain.step no longer carries production traffic), but the gate contradicts `_select_entry_neurons` fallback semantics and it will trip any future work that revives ExperiencePipeline for tests or a demo. Change:

```python
if self._spike_bus is not None and input_chi is not None:
```

to:

```python
if self._spike_bus is not None:
```

Small, self-contained, closes an inconsistency c1 named in v1's report.

## Forward-thinking pieces (compatibility with what comes next)

Called out here so a future dispatch author can grep for the intent, not so this dispatch grows.

**Injection metadata schema.** `_inject_input_as_spikes` metadata is currently `{input_chi, modality, word?}`. This dispatch is the point at which every production spike carries provenance. Phase 2 (lateral inhibition) will need chi neighborhood info to pick winners — already in metadata. Phase 3 (metabolism) will need modality to key energy accounting — already there. Phase 4 (neuromodulation) will want source (joe/wc/c1/curriculum) so valence can bias thresholds — **add `metadata["source"]` now** in the word path from the worker item's context (source tag reaches read_word; thread it through `_enqueue_organism_remember` into the queue item as a fifth tuple element, then out to injection). Sensory branch: `metadata["source"] = "sensory"`. This is the one forward-facing schema change worth making in this dispatch because retrofitting it later requires touching the same worker loop again — do it once.

**Choke point stability.** The injection call now lives at a single site (worker loop, two branches). Lateral inhibition changes `_select_entry_neurons`. Metabolism changes `_fire`. Neuromodulation changes threshold reads. None of them need to modify the injection site again. This dispatch stabilizes the write-side interface for phases 2–4.

**Shadow-mode readiness.** STDP state built by this dispatch is exactly what `_recall_fast_stdp` reads. When RECALL_BACKEND flips from `legacy` to `shadow`, comparison starts producing signal on the first read. No new plumbing needed.

**Seed compatibility.** Phase 6 boot-time seed writes population patterns into `_word_neuron_map` and synapse weights. Same data structures this dispatch's injection populates. Seed loads at boot; injection maintains and extends. No conflict, no override, no ordering constraint beyond "boot completes before traffic arrives" (already guaranteed).

**Dead code marker.** After this dispatch, `LoomBrain.step`, `_inject_input_as_spikes`, and `_recall_fast_stdp` are still called — by tests, `ExperiencePipeline`, and `seed_organism()`. `experience.py` and the demo path become dead from a production perspective. **Do NOT delete them in this dispatch.** Tests reference them; deletion is a separate cleanup after Phase 1 v2 stabilizes. Note this here so a future audit knows it's known.

## What's NOT being built

- No change to `LoomNeuron.__init__` or `LoomBrain.__init__` — only `__getstate__`/`__setstate__` added.
- No change to `_inject_input_as_spikes` itself — the method is fine; only its call site moves.
- No change to `_select_entry_neurons` or its `random.sample` fallback.
- No change to legacy write path: `experience_word`, `experience_moment`, `binding_atlas.record`, `hemi.step`, `cluster.step`, `neuron.step`, `neuron.experience_moment` all untouched.
- No change to the pickle SAVE call. `__getstate__` additions make save resilient to newly-populated Phase 1 v2 fields without touching the save path itself.
- No in-place repair of the existing `guala_organism.pkl.gz`. Natural next save handles it.
- No change to `RECALL_BACKEND` default — stays `legacy`.
- No change to `LoomBrain.step`'s legacy iteration body.
- No change to harness scenarios (they're legacy-behavior sentinels per `GL-BRIEF-HARNESS-VALIDITY-EVE-20260708-v1`).
- No change to `ExperiencePipeline`, `experience.py`, `seed_organism()`, or any test file.
- No new introspection metrics beyond what `/debug/stdp_state` already reports.
- No lateral inhibition, metabolism, neuromodulation, sleep-as-work, or seed changes (Phase 2+ territory).

## Halt conditions

1. **Real `LoomNeuron.__init__` has Phase 1 v2 fields not in the backfill list.** Halt, list them with defaults, route.
2. **Real `LoomBrain.__init__` has Phase 1 v2 fields beyond `_spike_bus`/`_guala_ref`.** Halt, list them, route.
3. **`SpikeBus._neuron_registry` cannot be reassigned post-construction** (unexpected — v2 confirmed it can, but re-verify against current code). If not, `wire_spike_bus` may need to reconstruct SpikeBus. Halt, route with the code path.
4. **Local production-pickle round-trip test fails** (see harness protocol below). Halt with traceback, route.
5. **Post-deploy `neurons_snapshot_failed > 0`.** Halt, root-cause the missing case, route.
6. **Post-deploy `total_spikes_injected_since_boot == 0` after 30 seconds of confirmed live traffic.** Injection is wired but not firing — halt, route with worker-loop diagnostic logs.
7. **Runaway firing.** If `fires_per_second_last_minute > 1000` sustained after injection lands, entry-neuron selection is over-driving under production text rate. Halt with rate, route.
8. **Spike queue depth grows unbounded.** If `spike_queue_depth` climbs past 10,000 without draining, propagation isn't keeping up with injection. Halt with depth series, route.
9. **Worker queue depth grows.** If `organism_worker.queued` climbs materially above pre-deploy baseline under equivalent load, chi recomputation is too expensive at production word rate. Halt with timing data, route.
10. **Legacy behavior regression.** If pre-deploy vs post-deploy diff on the four legacy harness scenarios shows any new failure category, halt, route.
11. **Substrate crashes on boot.** Any AttributeError, threading error, or import failure — halt, route with logs.
12. **Scope violation.** If the fix requires changes beyond items 1–6 above, halt, route.

Any halt: route with data. Do not extend scope.

## Harness protocol

Local first, against real production state, then deploy.

1. **Backup** as `pre-phase1-v2-revive-v3-<timestamp>`. Verify via S3 listing.
2. **Local unit tests:**
   - `test_neuron_getstate_excludes_lock_and_runtime_refs` — pickle-dumps a fully-init'd neuron with lock/spike_bus/callback set; confirms dump succeeds and unpickled object regains a fresh Lock via `__setstate__`.
   - `test_neuron_setstate_backfills_missing_fields` — constructs a state dict with only pre-Phase-1-v2 fields, unpickles as LoomNeuron, asserts every backfilled field is at its real `__init__` default.
   - `test_brain_getstate_excludes_runtime_refs` — same pattern for LoomBrain.
   - `test_brain_setstate_no_stale_refs` — verifies `_spike_bus` and `_guala_ref` are absent after `__setstate__`.
   - `test_wire_spike_bus_idempotent` — calls twice on the same Guala; verifies no error, no duplicate hooks.
   - `test_wire_spike_bus_noop_when_bus_absent` — sets `_spike_bus = None`; calls wire; verifies no exception.
   - `test_worker_loop_injects_on_word_item` — enqueues a word item on a live Guala, drives the worker one iteration, verifies `_spike_bus._total_spikes_injected > 0`.
   - `test_worker_loop_injects_on_sensory_item` — same for sensory.
   - Existing `test_neuron_spike_handling.py` and `test_brain_dual_path.py` — regression sweep, must remain green.
3. **Local production-pickle round-trip test — load-bearing pre-deploy gate:**
   - Download current `guala_organism.pkl.gz` from S3 (freshest backup) to scratchpad.
   - Construct a fresh Guala.
   - Call `load_full_state()` against downloaded pickle.
   - Assert every neuron has all Phase 1 v2 fields.
   - Assert `g._spike_bus is g.organism.brain._spike_bus`.
   - Assert `g.organism.brain._guala_ref is g`.
   - Enqueue a synthetic word item: `g._enqueue_organism_remember("probeword")`.
   - Drive the worker one cycle synchronously (or wait 200ms).
   - Assert `g._spike_bus._total_spikes_injected > 0`.
   - Assert `g._word_neuron_map` contains "probeword".
   - Enqueue a synthetic sensory item (fake hemi_id, input_signal, tick, chi).
   - Assert spike count grew again.
   - Save via `save_full_state()` to scratch path.
   - Delete downloaded pickle.
   - Re-load from scratch save.
   - Repeat all assertions. Confirms round-trip converges.
   - Delete scratch save.
   - If any assertion fails, halt and route with trace.
4. **Deploy:** commit, push, register task-def, force deploy.
5. **Boot check** (immediately after `guala_status` reports `save@tick > 0`):
   - Hit `GET /debug/stdp_state`.
   - Assert `diagnostics.neurons_snapshot_failed == 0`.
   - Assert `diagnostics.neurons_total == organism_population` from `guala_status`.
   - Assert per-neuron sample has real field values (potential, refractory, incoming synapse counts) — not null.
   - Assert `total_spikes_injected_since_boot == 0` (nothing has been read yet — traffic is what drives it).
6. **30-second live-traffic check** — hit the endpoint again after 30 seconds during which real production traffic is confirmed present (`guala_status` shows tick advancing, `read_count` growing):
   - Assert `total_spikes_injected_since_boot > 0`.
   - Assert `word_neuron_map_size > 0`.
   - If either is zero, halt condition 6 fires — route diagnostic.
7. **5-minute state collection:**
   - Hit `/debug/stdp_state` after 5 minutes of live traffic.
   - Compute deltas: `word_neuron_map_size`, `total_synapses_updated`, `synapses_strengthened`, `total_fire_events_since_boot`, `total_spikes_injected_since_boot`, `spikes_dropped`.
   - Report each delta.
   - Positive delta on `word_neuron_map_size` AND `synapses_strengthened` AND (`total_spikes_injected_since_boot` >> 0) = Phase 1 v2 is alive and building state under real load.
8. **Regression harness** — four `harness/scenarios/mechanism/` scenarios. Same known `presence` gap. No new failure modes.
9. **Post-deploy save verification** — after ~5 minutes runtime and one scheduled save, confirm `guala_status.persistence_health.last_save_tick` advanced. No need for a full re-download-and-test — save success + tick advance is sufficient.

## Rollback

Task-def revert. Then explicit ECS force-restart so in-memory objects (which may now carry Locks) don't attempt to save under the reverted code. Reverted code will restore from the pre-deploy pickle cleanly (`__setstate__` absent → normal unpickle; missing Phase 1 v2 fields left absent as they were originally).

## Scope guardrails

Do NOT:
- Modify `LoomNeuron.__init__` or `LoomBrain.__init__`.
- Modify `save_full_state()`.
- Modify `_select_entry_neurons` or its fallback.
- Modify `_inject_input_as_spikes`.
- Modify `experience_word`, `experience_moment`, `binding_atlas`, `hemi.step`, `cluster.step`, or `neuron.step`.
- Delete `experience.py`, `ExperiencePipeline`, `seed_organism`, or any test.
- Tune any HEURISTIC value.
- Flip `RECALL_BACKEND` off `legacy`.
- Repair `guala_organism.pkl.gz` in place.

If tempted, halt and route.

## Report

`GL-RPT-PHASE-1-V2-REVIVE-C1-20260708-v3.md` with:

- Files touched + diff summary
- Backup confirmation
- Local unit test results (new tests + regression sweep)
- Production-pickle round-trip test full trace, save/restore convergence confirmation
- Boot check output
- 30-second live-traffic check output (this is the "did injection actually fire" gate)
- 5-minute state collection full pre/post JSON + computed deltas
- Regression harness verdicts
- Any HEURISTIC values that surfaced
- Any scope-boundary concerns
- Findings needing Eve routing

Do not ask Joe questions. Route to Eve.

---

### Changelog

- v3 (2026-07-08, Eve): rewritten after v2 halted with a real production-graph miss. Injection moved from `LoomBrain.step` (zero production callers, confirmed by v2's report and by the brain.py comment at line 121) to the organism worker loop's two branches, where every text and sensory neuron access in production converges. `wire_spike_bus` called from inside `Guala.load_full_state` covering all 5 restore call sites without any of them needing knowledge. Forward-thinking additions: source-tagged spike metadata for future neuromodulation, choke-point stability for Phase 2–4, shadow-mode readiness, seed compatibility, dead-code marker.
- v2 (2026-07-08, Eve): superseded. Bug fixes were correct — c1 verified the design would work — but wired to `LoomBrain.step` which is only reached from a demo function gated behind `if __name__ == "__main__"`. Would have deployed silently correct and silently inert.
- v1 (2026-07-08, Eve): superseded. Two wrong field defaults, missed the LoomBrain side, missed the threading.Lock unpicklability.
