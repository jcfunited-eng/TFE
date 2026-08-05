# GL-CMD-PHASE-1-V2-REVIVE-EVE-20260708-v1

**doc_id:** GL-CMD-PHASE-1-V2-REVIVE-EVE-20260708-v1
**Author:** Eve
**To:** c1
**Ordered by:** Joe (2026-07-08 session — response to `GL-RPT-STDP-INTROSPECTION-C1-20260707-v1` finding 1)
**Blueprint:** `GL-BLUEPRINT-AE-SUBSTRATE-EVE-20260707-v2` §3.1, §3.3, §3.4
**Follows:** `GL-CMD-BLUEPRINT-PHASE-1-MERGED-EVE-20260707-v2` (Phase 1 v2), `GL-CMD-STDP-INTROSPECTION-EVE-20260707-v1` (endpoint that surfaced this)

## Verdict

Phase 1 v2 has been inert in production since deploy. Two bugs, both must close before the mechanism runs even once.

Bug A: every one of the 64 production neurons is missing every Phase 1 v2 field (`_neuron_lock`, `membrane_potential`, `_incoming_synapse_weights`, `chi_position`, and the rest). Root cause: `Embryo.load_full_state` restores via raw `pickle.load()`, which reconstructs `__dict__` directly and never calls `LoomNeuron.__init__`. Every subsequent save re-pickles the same broken objects. Self-perpetuating.

Bug B: `LoomBrain.step` gates the injection call on `input_chi is not None`. Pure text chat has `input_chi = None` by design (documented in `GL-CMD-BLUEPRINT-PHASE-1-MERGED-EVE-20260707-v2` finding 6). So every text interaction skips injection entirely. Even if Bug A were fixed, no spikes would fire on text traffic. Meanwhile `_select_entry_neurons` already handles `input_chi=None` via a `random.sample` fallback — the gate contradicts the fallback.

Fix both in one dispatch. Small, bounded, verifiable via the introspection endpoint that just landed.

## What's being built

### 1. `LoomNeuron.__setstate__`

Add to `dsf_ai_service/loom_model/neuron.py`:

```python
class LoomNeuron:
    # Phase 1 v2 fields that must be present on every neuron in memory.
    # Old pickles (pre-Phase-1-v2) restore without these; __setstate__
    # backfills them. If a future dispatch adds a new Phase-1-v2-class
    # field, add it here or restore will silently drop it again.
    _PHASE_1_V2_FIELDS = {
        'membrane_potential': 0.0,
        'membrane_rest': 0.0,
        'membrane_threshold': 1.0,
        'tau_m_ms': 20.0,
        'refractory_period_ms': 2.0,
        'last_update_time_s': 0.0,
        'refractory_until_s': 0.0,
        '_last_fire_time_s': None,
        'chi_position': None,
        # dict-typed and lock-typed fields handled explicitly in __setstate__
    }

    def __setstate__(self, state):
        """Backfill Phase 1 v2 fields missing from pre-Phase-1-v2 pickles.

        Pickle reconstructs __dict__ directly without calling __init__.
        Fields added to the class after a pickle was written are absent
        on restore. This method runs after __dict__ is populated and
        adds any missing Phase-1-v2 field at its __init__ default.
        """
        self.__dict__.update(state)

        # Scalar / None defaults from the table above
        for field, default in self._PHASE_1_V2_FIELDS.items():
            if not hasattr(self, field):
                setattr(self, field, default)

        # Types that can't sit in the class-level table
        if not hasattr(self, '_neuron_lock'):
            self._neuron_lock = threading.Lock()
        if not hasattr(self, '_incoming_synapse_weights'):
            self._incoming_synapse_weights = {}
        if not hasattr(self, '_recent_presynaptic_fires'):
            self._recent_presynaptic_fires = []
        # Hooks — set to None; set_spike_bus / set_word_firing_callback
        # in Guala.__init__ will populate them at boot
        if not hasattr(self, '_spike_bus'):
            self._spike_bus = None
        if not hasattr(self, '_word_firing_callback'):
            self._word_firing_callback = None
```

The exact field names above are illustrative — read the current `LoomNeuron.__init__` and mirror every field it sets, in the same defaults. If any field name here doesn't match what's actually in `__init__`, use `__init__`'s name and default. Do not guess.

### 2. `LoomBrain.step` — remove the `input_chi` gate

In `dsf_ai_service/loom_model/brain.py`, at the injection call site (~line 179 per `GL-CMD-BLUEPRINT-PHASE-1-MERGED-EVE-20260707-v2` §4):

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

`_inject_input_as_spikes` calls `_select_entry_neurons(input_chi, modality)`, which already returns a `random.sample` fallback when `input_chi is None` (per Phase 1 v2 dispatch §3, `ENTRY_SAMPLE_SIZE=16`). Removing this gate is what makes the fallback reachable.

## What's NOT being built

- No change to `LoomNeuron.__init__` — only `__setstate__` added.
- No change to the pickle save path — the next save after `__setstate__` fires will naturally re-pickle the now-complete objects. No in-place repair of the existing `guala_organism.pkl.gz` needed.
- No change to `RECALL_BACKEND` default — stays `legacy`. Cutover is a follow-up dispatch after STDP state is observably accumulating.
- No change to `_select_entry_neurons` or its fallback.
- No new introspection metrics — the existing `/debug/stdp_state` is the acceptance signal.
- No change to any legacy path (`binding_atlas`, `experience_moment`, legacy `recall_fast`).

## Halt conditions

1. **`__setstate__` throws on unpickle.** Would break every restart. Halt with the traceback.
2. **Post-fix `neurons_snapshot_failed` still > 0.** Means a field wasn't in the backfill list. Halt, list the missing field name, route.
3. **Runaway firing.** If after the injection gate is removed, `fires_per_second_last_minute` grows without bound (say, past 1000/sec sustained), the fallback random-sample injection under text load is over-driving the substrate. Halt with the rate.
4. **Substrate crashes on boot after the fix.** Any AttributeError, threading error, or import-time failure — halt, route with logs.
5. **Scope violation.** If the fix starts requiring changes to `__init__`, save path, `_select_entry_neurons`, or any Phase 2+ mechanism to work — halt, route.

Any halt: route with data, do not extend scope.

## Harness protocol

1. **Backup** as `pre-phase1-v2-revive-<timestamp>`. Verify restorable via direct S3 listing (same depth as prior dispatches).
2. **Local test** — before deploying:
   - Add `test_neuron_setstate_backfills_phase1_v2_fields.py` that pickles a plain object with only the pre-Phase-1-v2 fields, unpickles as a `LoomNeuron`, verifies every backfilled field is present with its default.
   - Add a test that removes `_neuron_lock` from a live-created neuron via `del`, re-pickles, unpickles, verifies restored.
   - Existing `test_neuron_spike_handling.py` and `test_brain_dual_path.py` — run, verify no regression.
3. **Deploy** — commit, push, register task-def, force deploy.
4. **Post-deploy — endpoint boot check**:
   - Hit `GET /debug/stdp_state` immediately after `guala_status` reports save@tick > 0 (confirms boot completed).
   - Assert `diagnostics.neurons_snapshot_failed == 0`.
   - Assert `diagnostics.neurons_total == organism_population` from `guala_status`.
   - Assert per-neuron fields present in the sample.
5. **Post-deploy — 5-minute state collection**:
   - Wait 5 minutes of real production traffic.
   - Hit `/debug/stdp_state` again.
   - Compute deltas: `word_neuron_map_size`, `total_synapses_updated`, `synapses_strengthened`, `total_fire_events_since_boot`, `total_spikes_injected_since_boot`.
   - Report each delta. Any positive delta on `word_neuron_map_size` or `synapses_strengthened` is the "Phase 1 v2 is actually alive" signal.
6. **Regression harness** — the four `harness/scenarios/mechanism/` scenarios. Same known `presence` precondition gap expected. No new failure modes.
7. **State disposition** — leave in place. If step 5 shows real accumulation, Phase 1 v2 is genuinely live for the first time.

## Rollback

Task-def revert to `:556` (the STDP endpoint deploy, pre-revive). `__setstate__` is additive to a class — a revert simply loses the backfill behavior; the corrupted-in-memory neurons that got backfilled during the fix's lifetime will re-pickle in their now-complete form, so the pickle is actually IMPROVED by a temporary deploy even if reverted immediately. No data loss risk on rollback.

## Scope guardrails

Do NOT:
- Modify `LoomNeuron.__init__`
- Modify the pickle save path
- Modify `_select_entry_neurons` or its fallback
- Tune any HEURISTIC value
- Touch legacy `binding_atlas` / `experience_moment` / `recall_fast` paths
- Flip `RECALL_BACKEND` off `legacy`
- Add or remove any harness scenario
- Repair the existing `guala_organism.pkl.gz` in place (unnecessary — natural re-save handles it)

If any of the above becomes tempting, halt and route.

## Report

`GL-RPT-PHASE-1-V2-REVIVE-C1-20260708-v1.md` with:
- Files touched + diff summary
- Backup confirmation
- Local test results (new tests + regression sweep)
- Boot check: `neurons_snapshot_failed`, field presence sample
- 5-minute state collection: full pre/post JSON, computed deltas
- Regression harness verdicts
- Any HEURISTIC values that surfaced needing attention
- Any scope-boundary concerns
- Findings needing Eve routing

Do not ask Joe questions. Route to Eve.

---

### Changelog
- v1 (2026-07-08, Eve): initial. Two bugs, one dispatch. `__setstate__` on `LoomNeuron` to backfill Phase 1 v2 fields lost through pickle restore; injection-gate removal so text traffic actually injects. Acceptance signal is the existing `/debug/stdp_state` endpoint — non-zero deltas on word_neuron_map_size or synapses_strengthened over a 5-minute production window.
