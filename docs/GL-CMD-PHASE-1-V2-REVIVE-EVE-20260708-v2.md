# GL-CMD-PHASE-1-V2-REVIVE-EVE-20260708-v2

**doc_id:** GL-CMD-PHASE-1-V2-REVIVE-EVE-20260708-v2
**Author:** Eve
**To:** c1
**Ordered by:** Joe (2026-07-08 session, response to `GL-RPT-PHASE-1-V2-REVIVE-C1-20260708-v1` halt)
**Blueprint:** `GL-BLUEPRINT-AE-SUBSTRATE-EVE-20260707-v2`
**Supersedes:** `GL-CMD-PHASE-1-V2-REVIVE-EVE-20260708-v1` (halted; two wrong field defaults, missed the LoomBrain side, missed the save-path interaction). Do not execute v1.
**Empirical groundwork already done:** `GL-RPT-PHASE-1-V2-REVIVE-C1-20260708-v1` has the exact field lists (`neuron.py:582, :592`, others confirmed against real `__init__`), the exact call sites (`gualaloom_v5_engine.py:1787, :1798, :1799` for the wiring; `:9031` for the restore replacement; `app.py:1260, :1271` for the boot sequence), and a confirmed reproduction against the actual production pickle. Do not re-do that work. Build on it.

## Verdict

Four bugs, one dispatch, one round-trip verification. Both sides of pickle (get + set) on both classes (neuron + brain), the wiring extracted so it runs on both boot paths, and the injection gate removed. Verified against the actual current production pickle locally before any deploy.

## What's being built

### 1. `LoomNeuron.__getstate__` and `LoomNeuron.__setstate__`

```python
class LoomNeuron:
    def __getstate__(self):
        """Exclude unpicklable and runtime-only fields from pickle state.

        _neuron_lock: threading.Lock is not picklable in CPython.
        _spike_bus: runtime reference; re-wired at boot by Guala.
        _word_firing_callback: bound method into Guala; would drag the
            whole Guala object graph into the pickle. Re-wired at boot.
        """
        state = self.__dict__.copy()
        state.pop('_neuron_lock', None)
        state.pop('_spike_bus', None)
        state.pop('_word_firing_callback', None)
        return state

    def __setstate__(self, state):
        """Restore __dict__ and backfill any missing Phase 1 v2 fields.

        Old pickles (pre-Phase-1-v2) lack fields added to the class after
        the pickle was written. Backfill each at its real __init__ default.
        _neuron_lock is always recreated (excluded from pickle by __getstate__).
        """
        self.__dict__.update(state)
        self._neuron_lock = threading.Lock()

        # Backfill Phase 1 v2 scalar/dict fields against the real __init__
        # defaults confirmed in GL-RPT-PHASE-1-V2-REVIVE-C1-20260708-v1.
        # If __init__ changes, update this list. Grep-able marker:
        # PHASE_1_V2_BACKFILL.
        if not hasattr(self, 'membrane_potential'):
            self.membrane_potential = 0.0
        if not hasattr(self, 'membrane_rest'):
            self.membrane_rest = 0.0
        if not hasattr(self, 'membrane_threshold'):
            self.membrane_threshold = 1.0
        if not hasattr(self, 'tau_m_ms'):
            self.tau_m_ms = 20.0
        if not hasattr(self, 'refractory_period_ms'):
            self.refractory_period_ms = 2.0
        if not hasattr(self, 'last_update_time_s'):
            self.last_update_time_s = 0.0
        if not hasattr(self, 'refractory_until_s'):
            self.refractory_until_s = 0.0
        if not hasattr(self, '_last_fire_time_s'):
            self._last_fire_time_s = 0.0            # NOT None — see halt report finding 4
        if not hasattr(self, 'chi_position'):
            self.chi_position = None
        if not hasattr(self, '_incoming_synapse_weights'):
            self._incoming_synapse_weights = {}
        if not hasattr(self, '_recent_presynaptic_fires'):
            self._recent_presynaptic_fires = {}     # NOT [] — see halt report finding 4
```

**Field list source of truth:** the real `LoomNeuron.__init__` in the current codebase. c1's halt report confirmed field names at `neuron.py:582` and `:592`; the rest are per Phase 1 v2 dispatch spec. Read `__init__` and add any Phase 1 v2 field the above list misses. Do not guess.

### 2. `LoomBrain.__getstate__` and `LoomBrain.__setstate__`

Same pattern, applied to `LoomBrain`:

```python
class LoomBrain:
    def __getstate__(self):
        """Exclude runtime references. Wiring is re-run at boot."""
        state = self.__dict__.copy()
        state.pop('_spike_bus', None)
        state.pop('_guala_ref', None)
        return state

    def __setstate__(self, state):
        """Restore __dict__ and backfill Phase 1 v2 fields.

        _spike_bus and _guala_ref are re-wired at boot by Guala's
        wire_spike_bus() — see item 3. Left absent here on purpose.
        """
        self.__dict__.update(state)
        # PHASE_1_V2_BACKFILL: match real LoomBrain.__init__ defaults.
        # Per Phase 1 v2 dispatch, brain-level Phase 1 v2 fields are
        # _spike_bus and _guala_ref only; both are re-wired externally,
        # so no backfill here besides ensuring the attributes don't
        # accidentally survive as stale references.
```

If `LoomBrain.__init__` (at `brain.py:115-123` per halt report) sets other Phase 1 v2 fields beyond `_spike_bus` and `_guala_ref`, read `__init__` and mirror them. c1's report names only those two; verify by reading.

### 3. `Guala.wire_spike_bus()` — extracted helper

Extract the wiring block currently in `Guala.__init__` (lines 1787, 1798, 1799 per halt report) into a method:

```python
def wire_spike_bus(self):
    """Wire the SpikeBus onto every neuron and onto LoomBrain.

    Invariant: after this returns, self._spike_bus is set, every neuron
    in self.organism.brain has _spike_bus and _word_firing_callback
    attached, and self.organism.brain has _spike_bus and _guala_ref
    attached. Idempotent — safe to call after fresh construction OR
    after load_full_state().
    """
    # Ensure SpikeBus exists (constructed in __init__; if this method
    # is somehow reached without one, that's a real bug and we crash
    # loudly instead of silently.)
    assert self._spike_bus is not None, \
        "wire_spike_bus called before _spike_bus was constructed"

    # Rebuild the flat neuron registry against the current organism.
    # After load_full_state, self.organism has been replaced, so we
    # cannot reuse a registry from __init__.
    neuron_registry = {
        n.neuron_id: n
        for hemi in self.organism.brain.hemispheres
        for n in hemi.cluster.neurons
    }

    # Update the SpikeBus's own registry pointer if it exposes one.
    # (If SpikeBus stores neuron_registry as a captured constructor
    # arg only, we may need to reconstruct SpikeBus here instead.
    # Read spike_bus.py to confirm which case we're in.)
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

Then in `Guala.__init__`, replace the existing wiring block (lines 1787-1799 area) with a call to `self.wire_spike_bus()`. This preserves current fresh-boot behavior byte-for-byte.

### 4. Call `wire_spike_bus()` after restore

The restore path is in `app.py:_gl_init()` at lines 1260, 1271 per halt report — where `g.load_full_state(STATE_DIR)` is called. Immediately after that call returns, before the substrate accepts any input, call `g.wire_spike_bus()`. That closes the "restored organism has no spike bus wiring" gap.

If there's more than one call site for `load_full_state()`, the same follow-up is needed at each. Grep confirms.

### 5. Remove the `input_chi is not None` gate

In `LoomBrain.step` (per Phase 1 v2 dispatch §4, around brain.py:179):

Change:
```python
if getattr(self, '_spike_bus', None) is not None and input_chi is not None:
    self._inject_input_as_spikes(input_signal, input_chi, modality)
```

To:
```python
if getattr(self, '_spike_bus', None) is not None:
    self._inject_input_as_spikes(input_signal, input_chi, modality)
```

`_select_entry_neurons` already handles `input_chi=None` via random-sample fallback.

## What's NOT being built

- No change to `LoomNeuron.__init__` or `LoomBrain.__init__` — only the get/set-state pair on each.
- No modification of the pickle SAVE call (`save_full_state()`). The `__getstate__` additions make the save resilient to the newly-populated Phase 1 v2 fields without touching the save path itself.
- No in-place repair of the existing `guala_organism.pkl.gz`. The natural next save after the fix deploys writes a clean-shape pickle.
- No change to `RECALL_BACKEND` default — stays `legacy`.
- No change to `_select_entry_neurons` or its fallback.
- No new introspection metrics.
- No change to any legacy path (`binding_atlas`, `experience_moment`, legacy `recall_fast`).
- No new harness scenarios.

## Halt conditions

1. **Real `__init__` has fields not in the backfill list.** Halt, list them, route. Do not extend the list unilaterally without confirming defaults.
2. **`spike_bus.py` uses a captured `neuron_registry` that can't be updated post-construction.** `wire_spike_bus()` may need to reconstruct the SpikeBus. Halt on that finding, route with the code path.
3. **`load_full_state()` has additional call sites beyond `_gl_init()`.** Halt, list them, route.
4. **Save round-trip fails locally against the actual production pickle** (see harness protocol). Halt, route with the traceback and the failing field.
5. **Post-deploy endpoint check shows `neurons_snapshot_failed > 0`.** Halt, root-cause the missing case, route.
6. **Runaway firing after gate removal.** If `fires_per_second_last_minute` grows past 1000/sec sustained, injection under text load is over-driving. Halt with the rate.
7. **Substrate crashes on boot.** Any error — halt, route with logs.
8. **Scope violation.** If the fix requires changes beyond items 1-5 above — halt, route.

Any halt: route with data. Do not extend scope.

## Harness protocol

The verification order matters. Local first, against real production state, then deploy.

1. **Backup** as `pre-phase1-v2-revive-v2-<timestamp>`. Verify restorable via direct S3 listing.
2. **Local unit tests**:
   - `test_neuron_getstate_excludes_lock_and_runtime_refs`: pickle-dumps a fully-`__init__`'d neuron with lock/spike_bus/callback set; confirms dump succeeds and unpickled object regains a fresh `Lock()` via `__setstate__`.
   - `test_neuron_setstate_backfills_missing_fields`: constructs a state dict with only pre-Phase-1-v2 fields, unpickles as `LoomNeuron`, asserts every backfilled field has the correct default.
   - `test_brain_getstate_excludes_runtime_refs`: same pattern for `LoomBrain`.
   - `test_brain_setstate_backfills_missing_fields`: same pattern for brain-level Phase 1 v2 fields.
   - `test_wire_spike_bus_idempotent`: calls `wire_spike_bus()` twice on the same `Guala`, asserts no error and no attribute duplication.
   - Existing `test_neuron_spike_handling.py` and `test_brain_dual_path.py` — regression sweep, must remain green.
3. **Local production-pickle round-trip test — the one that catches Bug C class**:
   - Download the current `guala_organism.pkl.gz` from S3 (whatever the freshest backup is, referenced by direct S3 URI in the test log) to a scratchpad.
   - Construct a fresh `Guala()`; call `load_full_state()` against the downloaded pickle.
   - Assert every neuron has all backfilled Phase 1 v2 fields.
   - Call `g.wire_spike_bus()`.
   - Assert `g._spike_bus is g.organism.brain._spike_bus`.
   - Assert `g.organism.brain._guala_ref is g`.
   - Inject a probe spike via `g.organism.brain._inject_input_as_spikes("test_probe", input_chi=None, modality="language")`.
   - Assert non-zero delivery (via SpikeBus counters).
   - Save via `g.save_full_state()` to a scratch path.
   - Delete the downloaded state.
   - Re-load from the scratch save. Repeat the assertions. Confirms the save/restore round-trip converges to a working state.
   - Delete the scratch save.
   - This is the load-bearing local check. If it passes, deploy. If any assertion fails, halt and route with the trace.
4. **Deploy**: commit, push, register task-def, force deploy.
5. **Boot check**:
   - Wait for `guala_status` to report save@tick > 0.
   - Hit `GET /debug/stdp_state`.
   - Assert `diagnostics.neurons_snapshot_failed == 0`.
   - Assert `diagnostics.neurons_total == organism_population` from `guala_status`.
   - Assert per-neuron sample has real values (potential, refractory, incoming synapse counts) — not null.
6. **5-minute state collection**:
   - Wait 5 minutes of real production traffic.
   - Hit `/debug/stdp_state` again.
   - Compute deltas: `word_neuron_map_size`, `total_synapses_updated`, `synapses_strengthened`, `total_fire_events_since_boot`, `total_spikes_injected_since_boot`.
   - Report each delta. Any positive delta on `word_neuron_map_size` or `synapses_strengthened` is Phase 1 v2 alive.
7. **Regression harness**: the four `harness/scenarios/mechanism/` scenarios. Same known `presence` precondition gap expected. No new failure modes acceptable.
8. **Post-deploy save verification**: after the substrate has run for ~5 minutes and a scheduled save has occurred, confirm the newly-written `guala_organism.pkl.gz` is loadable (via `guala_status` reporting last_save_tick advancing normally; no need for a second download-and-test unless the save log shows an error).

## Rollback

Task-def revert. If a `LoomNeuron` in memory has a `_neuron_lock` at the moment of revert, the next save under the reverted (Phase 1 v2 v0) code base could fail. Mitigation: keep the task-def revert AND explicitly restart the substrate immediately after revert so the in-memory objects are re-loaded from the pre-existing (lockless) pickle. This is a normal ECS force-deploy of the reverted task-def.

## Scope guardrails

Do NOT:
- Modify `LoomNeuron.__init__` or `LoomBrain.__init__`
- Modify the pickle save call itself (`save_full_state`)
- Modify `_select_entry_neurons` or its fallback
- Tune any HEURISTIC value
- Touch legacy `binding_atlas` / `experience_moment` / `recall_fast` paths
- Flip `RECALL_BACKEND` off `legacy`
- Add or remove any harness scenario
- Perform in-place repair of the existing `guala_organism.pkl.gz` (the natural post-fix save handles it)
- Introduce any new backup, snapshot, or persistence mechanism

If any of the above becomes tempting, halt and route.

## Report

`GL-RPT-PHASE-1-V2-REVIVE-C1-20260708-v2.md` with:
- Files touched + diff summary
- Backup confirmation
- Local unit test results (new tests + regression sweep)
- Production-pickle round-trip test result — full trace of assertions, save/restore convergence
- Boot check output
- 5-minute state collection output (pre/post JSON, computed deltas)
- Regression harness verdicts
- Any HEURISTIC values that surfaced needing attention
- Any scope-boundary concerns
- Findings needing Eve routing

Do not ask Joe questions. Route to Eve.

---

### Changelog
- v2 (2026-07-08, Eve): rewritten after v1 halted with three real problems. Scopes in `LoomBrain.__setstate__`, `__getstate__` on both classes to handle Lock and runtime-ref exclusion, wiring extracted into an idempotent `Guala.wire_spike_bus()` called from both `__init__` and after `load_full_state()`. Field defaults corrected per c1's halt report (`_last_fire_time_s = 0.0`, `_recent_presynaptic_fires = {}`). Adds the load-bearing production-pickle round-trip local test as the pre-deploy gate — same method that caught v1's problems.
- v1 (2026-07-08, Eve): superseded. Two wrong field defaults would have shipped fresh crashes. Missed the LoomBrain side, so injection stays no-op post-restore. Missed the threading.Lock unpicklability, so first save after fix would have broken the whole organism pickle.
