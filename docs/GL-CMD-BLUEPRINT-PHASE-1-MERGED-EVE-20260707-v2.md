# GL-CMD-BLUEPRINT-PHASE-1-MERGED-EVE-20260707-v2

**doc_id:** GL-CMD-BLUEPRINT-PHASE-1-MERGED-EVE-20260707-v2
**Author:** Eve
**To:** c1
**Ordered by:** Joe (2026-07-07 session)
**Blueprint:** `GL-BLUEPRINT-AE-SUBSTRATE-EVE-20260707-v2` §3.1, §3.3, §3.4, §4 Phase 1
**Supersedes:** `GL-CMD-BLUEPRINT-PHASE-1-MERGED-EVE-20260707-v1`. That dispatch had real design errors surfaced by dependency audit. Do not execute v1 as written.

## Why v2 exists

The research agent's audit of v1 found seven substantive issues that would have broken execution:

1. **The live recall path is `binding_atlas`-driven, not `chi_atlas`-driven.** `_recall_fast_resonant_spectral` (brain.py:441-472) iterates hemispheres × neurons and votes via `neuron.binding_atlas.recall_best(neuron.encode_state(query_signals, precomputed_lanes))`. `chi_atlas` is never touched in recall. v1's "replace chi_atlas recall" framing was based on a wrong understanding.

2. **Four production callers of `recall_fast` exist**, not one: recognition/surprise in `read_word` (line 1952), emission candidates (3528), single-word recall (4964), daydream associative walk (5019). Each must continue to receive a Counter of concept→votes with equivalent semantics.

3. **`LoomCluster._select_by_chi_familiarity`** (cluster.py:211-234) is a real live `chi_atlas` reader that gates which neurons participate in cluster.step. In production text chat it's currently a no-op because `input_chi=None` for pure text (see finding #6), but any migration touching `chi_atlas` must handle it.

4. **The write path via `experience_word` → `embryo.remember` → `neuron.experience_moment`** writes to `binding_atlas` per neuron directly, NEVER through `brain.step`. v1's "everything routes through brain.step" mental model was wrong for writes.

5. **The neuron-side half of the substrate rebuild is already built and uncommitted** (HEAD b91b692 + neuron.py +254/-69). c1 already implemented STDP potentiation/depression, membrane state fields, `set_spike_bus`/`set_word_firing_callback` hooks, and `_on_fire_bookkeeping` that writes chi_atlas as observability-only. This work stands.

6. **`input_chi` is `None` for pure text chat.** `_compute_input_chi` returns None when composite signal is empty, and language is deliberately excluded from composite (embryo.py:411-419). Only sensory-band path via `wave_summary.py` reliably computes non-None input_chi. So the chi-familiarity filter from earlier today is a no-op on text chat right now.

7. **`SpikeBus` construction expects `neuron_registry` upfront** (spike_bus.py:58-60). Guala needs a flat `{neuron_id: neuron}` dict built once after `self.organism` is constructed (post gualaloom_v5_engine.py:1731). No existing helper builds this — one must be added, mirroring brain.py:314's list-comprehension pattern.

v2 addresses all seven honestly. The bridge design that v1 skipped is now central.

## Approach: dual-write during transition, flag-gated read cutover

Phase 1 v2 runs both the existing (`binding_atlas` / `experience_moment` / current `recall_fast`) mechanism AND the new (STDP synapse graph / spike propagation / membrane-state) mechanism SIMULTANEOUSLY. Recognition and recall keep working via the existing mechanism throughout. The new mechanism builds its state in parallel. When both produce equivalent results on the same inputs, the read path flips via feature flag. The old mechanism stays as fallback until Phase 2 confirms and then gets deprecated in a follow-up dispatch.

This means Phase 1 does NOT delete binding_atlas, experience_moment, or the current recall_fast implementation. It ADDS the new mechanism, verifies equivalence, and enables cutover.

## What's preserved from c1's parked work (HEAD b91b692 + uncommitted neuron.py)

- `dsf_ai_service/substrate/spike_bus.py` — SpikeBus infrastructure. Priority queue, delivery thread, tested.
- Neuron-side event handling: membrane_potential, membrane_rest, membrane_threshold, tau_m_ms, refractory_period_ms, _neuron_lock, chi_position fields.
- Neuron methods: receive_spike, _fire, _compute_propagation_delay_ms, _get_outgoing_synapses.
- STDP implementation: _apply_stdp_potentiation, _receive_upstream_fire_notification, _notify_downstream_of_fire, _recent_presynaptic_fires, _incoming_synapse_weights.
- Hooks: set_spike_bus, set_word_firing_callback.
- `_on_fire_bookkeeping(self, now, word=None)` — writes chi_atlas.record as observability-only, calls _word_firing_callback if set.

All of this stays. c1 should COMMIT the uncommitted +254/-69 in neuron.py as-is before starting the engine-side work.

## What's being built (engine side, new)

### 1. Guala.__init__ additions

At gualaloom_v5_engine.py:1600 (immediately after the existing `_word_to_chi_index`), add the word-neuron association maps:

```python
# GL-CMD-BLUEPRINT-PHASE-1-MERGED-EVE-20260707-v2: word ↔ neuron
# association maintained by _on_word_firing callback. Populated
# by live experience once spike bus is wired; replaces chi_atlas's
# implicit word→chi role for recognition and recall under the new
# event-driven substrate.
self._word_neuron_map: dict = {}  # word.lower() -> set of neuron_ids
self._neuron_word_map: dict = {}  # neuron_id -> word.lower() (primary)
```

Key on `word.lower()` matching the existing `_word_to_chi_index` and `_word_to_emission_sections` convention.

After `self.organism = _Embryo(...)` at gualaloom_v5_engine.py:1731, add the spike bus construction and wiring:

```python
# Build flat neuron registry mirroring brain.py:314's idiom
neuron_registry = {
    n.neuron_id: n
    for hemi in self.organism.brain.hemispheres
    for n in hemi.cluster.neurons
}

from dsf_ai_service.substrate.spike_bus import SpikeBus
self._spike_bus = SpikeBus(neuron_registry=neuron_registry)

# Wire each neuron to the shared bus + word-firing callback
for neuron in neuron_registry.values():
    neuron.set_spike_bus(self._spike_bus)
    neuron.set_word_firing_callback(self._on_word_firing)

# Start bus after wiring complete
if os.environ.get("EVENT_DRIVEN_SUBSTRATE", "1") == "1":
    self._spike_bus.start()
```

**HEURISTIC:** default `EVENT_DRIVEN_SUBSTRATE=1` (enabled). Class: from-design. Rollback path: set to `0` to bypass spike bus entirely and fall through to legacy iteration path.

Add shutdown hook to stop spike bus cleanly:

```python
def shutdown(self):
    # ... existing shutdown code ...
    if getattr(self, '_spike_bus', None) is not None:
        self._spike_bus.stop()
```

### 2. _on_word_firing callback

Add to Guala:

```python
def _on_word_firing(self, word: Optional[str], neuron_id: str) -> None:
    """Called by LoomNeuron._on_fire_bookkeeping when a word context
    is available at fire time. Maintains bidirectional word↔neuron
    association for the new event-driven recognition/recall path.
    """
    if word is None:
        return
    wl = word.lower()
    self._word_neuron_map.setdefault(wl, set()).add(neuron_id)
    # First neuron to fire for this word gets primary association
    if neuron_id not in self._neuron_word_map:
        self._neuron_word_map[neuron_id] = wl
```

The callback signature matches what c1's parked `_on_fire_bookkeeping` already calls at line 856-ish: `self._word_firing_callback(word, self.neuron_id)`.

### 3. Neuron enumeration helpers

Add to Guala (methods, not new fields):

```python
def _all_neurons(self):
    """Flat iterator over every neuron in the substrate.
    Mirrors brain.py:314's list-comprehension idiom.
    """
    return [
        n
        for hemi in self.organism.brain.hemispheres
        for n in hemi.cluster.neurons
    ]

def _neuron_to_word(self, neuron) -> Optional[str]:
    """Return primary word associated with this neuron, if any."""
    return self._neuron_word_map.get(neuron.neuron_id)

def _chi_to_neurons(self, chi: int, band: int = None):
    """Return neurons whose chi_position is within `band` of `chi`."""
    if band is None:
        band = ENTRY_CHI_BAND
    return [
        n for n in self._all_neurons()
        if abs(n.chi_position - chi) <= band
    ]

def _select_entry_neurons(self, input_chi: Optional[int], modality: Optional[str] = None):
    """Select neurons to receive initial spike injection for a given
    input. Phase 1 uses chi-proximity if input_chi provided;
    otherwise falls back to a small random sample.
    """
    if input_chi is not None:
        candidates = self._chi_to_neurons(input_chi)
        if candidates:
            return candidates
    # No chi anchor or empty proximity — small sample of all neurons
    import random
    all_neurons = self._all_neurons()
    return random.sample(all_neurons, min(ENTRY_SAMPLE_SIZE, len(all_neurons)))
```

**HEURISTIC:** `ENTRY_CHI_BAND = 8` — how far chi injection reaches. Class: from-design. Measurement plan: verify entry neurons cover a plausible neighborhood; adjust if injection is too narrow (recognition fails) or too broad (specificity lost).

**HEURISTIC:** `ENTRY_SAMPLE_SIZE = 16` — fallback random injection size. Class: from-design. Measurement plan: measure recognition quality under fallback path; adjust if too silent or too broad.

### 4. Injection dispatcher (LoomBrain.step transformation)

Modify `LoomBrain.step` (brain.py:120) to be a hybrid: keep the current iteration path (called from `_feed_and_fold` in embryo.py:373-379 for growth cascade), BUT add a spike injection call BEFORE the iteration:

```python
def step(self, input_signal, tick, input_chi: Optional[int] = None,
         modality: Optional[str] = None) -> Dict:
    # NEW: dual-write. If spike bus available, inject the input as spikes.
    # This runs in ADDITION to the existing iteration path during Phase 1
    # transition. Old path continues to update binding_atlas via
    # experience_moment (embryo.remember); new path builds STDP synapse
    # weights and word-neuron map via spike propagation and _fire.
    if getattr(self, '_spike_bus', None) is not None and input_chi is not None:
        self._inject_input_as_spikes(input_signal, input_chi, modality)

    # EXISTING: iteration path continues, unchanged
    return self._legacy_step_iteration(input_signal, tick, input_chi)


def _inject_input_as_spikes(self, input_signal, input_chi, modality):
    """Convert input signal into initial spike injections at entry
    neurons. Runs alongside legacy iteration during Phase 1 transition.
    """
    from .injection_weight import signal_to_injection_weight
    weight = signal_to_injection_weight(input_signal)
    entry_neurons = self._select_entry_neurons_local(input_chi, modality)
    for neuron in entry_neurons:
        self._spike_bus.inject(
            target_id=neuron.neuron_id,
            source_id="_input_injection_",
            weight=weight,
            arrival_delay_ms=0.0,
            metadata={"input_chi": input_chi, "modality": modality},
        )
```

`_select_entry_neurons_local` is a version of `_select_entry_neurons` that works from `LoomBrain` scope (uses `self.hemispheres`). Or `LoomBrain` gains a reference to the spike bus and Guala provides a callback.

Cleanest wiring: LoomBrain gets `set_spike_bus(bus)` method (mirroring neuron.set_spike_bus), and Guala calls it after constructing the bus.

**HEURISTIC:** `signal_to_injection_weight` computes weight from input signal magnitude. For word inputs (string), returns a constant. For numeric inputs, returns normalized L2 magnitude clamped to `[0, MAX_INJECTION_WEIGHT=2.0]`. Class: from-design. Measurement plan: observe whether injection weights produce first-neuron firing consistently; adjust if injection is too weak (silent) or too strong (runaway).

### 5. recall_fast: dual-path implementation

Modify `LoomBrain.recall_fast` (brain.py:259) to dispatch based on feature flag:

```python
def recall_fast(self, query_signals: Dict[str, Any]) -> "Counter":
    """Population-vote recall.

    Dispatches to STDP-graph or legacy binding_atlas backend based on
    RECALL_BACKEND env var. During Phase 1 transition, both backends
    run in shadow to verify equivalence before cutover.
    """
    from collections import Counter

    backend = os.environ.get("RECALL_BACKEND", "legacy")

    if backend == "stdp":
        # New path: STDP graph walk
        return self._recall_fast_stdp(query_signals)
    elif backend == "shadow":
        # Shadow mode: run both, log discrepancies, return legacy result
        legacy_votes = self._recall_fast_legacy(query_signals)
        try:
            stdp_votes = self._recall_fast_stdp(query_signals)
            self._log_recall_shadow_comparison(legacy_votes, stdp_votes, query_signals)
        except Exception:
            log.exception("stdp shadow recall failed")
        return legacy_votes
    else:
        # Default: legacy path unchanged
        return self._recall_fast_legacy(query_signals)


def _recall_fast_legacy(self, query_signals):
    """Existing recall_fast logic, preserved verbatim."""
    if self.observable == "resonant_spectral":
        return self._recall_fast_resonant_spectral(query_signals)
    # ... rest of existing recall_fast body ...
```

**HEURISTIC:** default `RECALL_BACKEND=legacy` for production safety. Phase 1 transition sequence:
1. Deploy with `RECALL_BACKEND=legacy` — verify substrate boots, STDP builds state via injection
2. After ~1 hour of live reading, flip a test service to `RECALL_BACKEND=shadow` — measure equivalence
3. When equivalence confirmed, flip production to `RECALL_BACKEND=shadow` for logging
4. When shadow log shows consistent agreement, flip to `RECALL_BACKEND=stdp` — cutover
5. Follow-up dispatch deletes legacy path

### 6. _recall_fast_stdp: the new recall

Add to LoomBrain:

```python
def _recall_fast_stdp(self, query_signals: Dict[str, Any]) -> "Counter":
    """STDP-graph recall. Given query signals, inject cue spikes at
    neurons associated with the query components, allow propagation
    window to elapse, read activated neurons, aggregate their word
    associations into a vote Counter matching legacy signature.
    """
    from collections import Counter
    import time

    votes = Counter()
    if getattr(self, '_spike_bus', None) is None:
        return votes  # spike bus not available, no STDP recall possible

    # Resolve query into cue neuron_ids via Guala's word_neuron_map
    guala = getattr(self, '_guala_ref', None)
    if guala is None:
        return votes

    cue_neuron_ids = set()
    language_q = query_signals.get("language")
    if isinstance(language_q, str):
        for nid in guala._word_neuron_map.get(language_q.lower(), set()):
            cue_neuron_ids.add(nid)

    # For non-language modalities, resolve via chi if possible
    for mod, sig in query_signals.items():
        if mod == "language" or sig is None:
            continue
        # Compute chi for the signal via shared krimelack (matches the
        # upstream chi computation used elsewhere)
        try:
            chi = self._compute_query_chi(sig)
        except Exception:
            continue
        if chi is None:
            continue
        for n in guala._chi_to_neurons(chi):
            cue_neuron_ids.add(n.neuron_id)

    if not cue_neuron_ids:
        return votes

    # Inject cue spikes
    now = time.monotonic()
    for nid in cue_neuron_ids:
        self._spike_bus.inject(
            target_id=nid,
            source_id="_recall_cue_",
            weight=RECALL_INJECTION_WEIGHT,
            arrival_delay_ms=0.0,
            metadata={"purpose": "recall"},
        )

    # Wait for propagation window
    time.sleep(RECALL_PROPAGATION_WINDOW_MS / 1000.0)

    # Read activated neurons via current membrane potential
    now = time.monotonic()
    for neuron in guala._all_neurons():
        with neuron._neuron_lock:
            dt_ms = (now - neuron.last_update_time_s) * 1000.0
            if dt_ms > 0:
                import math
                decay = math.exp(-dt_ms / neuron.tau_m_ms)
                potential = (
                    neuron.membrane_rest
                    + (neuron.membrane_potential - neuron.membrane_rest) * decay
                )
            else:
                potential = neuron.membrane_potential

        if potential > RECALL_ACTIVATION_THRESHOLD:
            associated_word = guala._neuron_to_word(neuron)
            if associated_word is not None:
                # Vote weighted by activation strength (integer weight)
                weight_votes = max(1, int(potential * VOTE_SCALE))
                votes[associated_word] += weight_votes

    return votes
```

**HEURISTIC:** `RECALL_INJECTION_WEIGHT = 2.0` — enough to prime propagation without saturating. Class: from-design. Measurement plan: verify cue injection produces propagation; adjust if recall is too silent or too broad.

**HEURISTIC:** `RECALL_PROPAGATION_WINDOW_MS = 30.0` — allows several spike hops. Class: from-design. Measurement plan: measure recall latency vs recall completeness; adjust if window is too short (partial results) or too long (blocking).

**HEURISTIC:** `RECALL_ACTIVATION_THRESHOLD = 0.3` — captures neurons meaningfully activated. Class: from-design. Measurement plan: verify recall returns semantically-related concepts; adjust threshold if too broad or too narrow.

**HEURISTIC:** `VOTE_SCALE = 5` — converts membrane potential (float) to vote weight (int). Class: from-design. Measurement plan: verify votes distribution matches legacy shape enough for the four callers to work; adjust scale if top-concept selection differs qualitatively.

### 7. Shadow-mode logging

Add helper:

```python
def _log_recall_shadow_comparison(self, legacy_votes, stdp_votes, query):
    """Log discrepancies between legacy and STDP recall for later analysis.
    Used during RECALL_BACKEND=shadow phase.
    """
    legacy_top = legacy_votes.most_common(3)
    stdp_top = stdp_votes.most_common(3)

    log.info("recall_shadow", extra={
        "query": {k: str(v)[:32] for k, v in query.items()},
        "legacy_top3": [(str(w), c) for w, c in legacy_top],
        "stdp_top3": [(str(w), c) for w, c in stdp_top],
        "legacy_total": sum(legacy_votes.values()),
        "stdp_total": sum(stdp_votes.values()),
        "top_match": (legacy_top and stdp_top
                      and legacy_top[0][0] == stdp_top[0][0]),
    })
```

### 8. _brain_emission_candidates: also dual-path

Currently at gualaloom_v5_engine.py:3468. Modify to check `RECALL_BACKEND`:

```python
def _brain_emission_candidates(self, input_words):
    if os.environ.get("RECALL_BACKEND", "legacy") == "stdp":
        return self._brain_emission_candidates_membrane(input_words)
    return self._brain_emission_candidates_legacy(input_words)


def _brain_emission_candidates_membrane(self, input_words):
    """Emission candidates from current neuron membrane state.
    Reads current membrane_potential (with decay applied) across
    all neurons, returns top-K by activation.
    """
    import math
    import time
    now = time.monotonic()
    candidates = []
    for neuron in self._all_neurons():
        with neuron._neuron_lock:
            dt_ms = (now - neuron.last_update_time_s) * 1000.0
            if dt_ms > 0:
                decay = math.exp(-dt_ms / neuron.tau_m_ms)
                potential = (
                    neuron.membrane_rest
                    + (neuron.membrane_potential - neuron.membrane_rest) * decay
                )
            else:
                potential = neuron.membrane_potential

        if potential > EMISSION_THRESHOLD:
            associated_word = self._neuron_to_word(neuron)
            if associated_word:
                candidates.append((neuron.chi_position, potential, associated_word))

    return sorted(candidates, key=lambda x: x[1], reverse=True)[:TOP_K_EMISSION]
```

Preserve `_brain_emission_candidates_legacy` as the existing implementation renamed.

**HEURISTIC:** `EMISSION_THRESHOLD = 0.5`, `TOP_K_EMISSION = 20`. Class: from-design. Measurement plan: verify emission candidates match legacy top candidates in shadow mode; adjust if quality degrades.

### 9. _select_by_chi_familiarity: no change in Phase 1

`LoomCluster._select_by_chi_familiarity` (cluster.py:211-234) continues to run. It reads `chi_atlas.match_score` which is still populated by `_on_fire_bookkeeping` (as observability, per c1's preserved work).

In production text chat this is a no-op (`input_chi=None`). On the sensory-band path where `input_chi` is real, it continues to filter by chi familiarity as it does today.

Migration to strength-based filter (reading STDP synapse weights instead of chi_atlas entries) is a **Phase 2** concern, aligned with lateral inhibition. Do NOT modify in Phase 1.

### 10. experience_word / experience_moment / binding_atlas write path: unchanged in Phase 1

The write path via `Guala._enqueue_organism_remember` → `_organism_worker_loop` → `self.organism.experience_word` → `embryo.remember` → `neuron.experience_moment` → `neuron.binding_atlas` remains fully intact and unchanged.

This is what legacy recall_fast reads. Preserving this path keeps recognition working via the legacy backend throughout Phase 1 transition.

The new mechanism (spike propagation → STDP synapse weights → word_neuron_map) runs in ADDITION via the injection path in `LoomBrain.step`. Both write paths run in parallel.

At end of Phase 1, if STDP recall proves equivalent, a follow-up dispatch deprecates the binding_atlas write path.

## What is NOT in Phase 1 (strict boundary)

Halt if any of these appear:
- Lateral inhibition (Phase 2)
- Metabolic energy budget (Phase 3)
- Neuromodulation broadcast (Phase 4)
- Sleep-as-work consolidation (Phase 5)
- Population-based seed content generation (Phase 6)
- Deletion of binding_atlas, experience_moment, or legacy recall_fast (follow-up cleanup dispatch, not this one)
- Migration of `_select_by_chi_familiarity` (Phase 2)

## Halt conditions

1. **Boot failure** — substrate crashes on startup after wiring the spike bus. Halt with logs.
2. **Legacy recall regression** — with `RECALL_BACKEND=legacy` (default), harness scenarios show different behavior than before Phase 1 v2 lands. Would mean the injection path or spike bus is contaminating legacy operation. Halt.
3. **STDP shadow divergence** — in shadow mode, STDP top-vote disagrees with legacy top-vote on >50% of queries after ~1 hour of live substrate. Would mean STDP mechanism produces different memory than binding_atlas. Halt with data.
4. **Runaway firing** — spike bus queue depth grows without bound OR total neuron fires per second grows without bound. STDP over-potentiation is a likely cause. Halt.
5. **Silent substrate** — no neurons fire despite input injection. Would mean thresholds/weights aren't right for defaults. Halt.
6. **Word-neuron association not accumulating** — `_word_neuron_map` stays empty despite input. Would mean the callback wiring is broken. Halt.
7. **Scope violation** — c1 finds self implementing Phase 2+ mechanism. Halt.

Any halt: route with data. Do NOT extend scope unilaterally.

## Harness protocol

1. **Backup** as `pre-blueprint-phase1-merged-v2-<timestamp>`. Verify restorable.
2. **Commit c1's parked neuron.py changes** (+254/-69) as a separate commit before starting engine work. Docstring: "commit c1's parked neuron-side Phase 1 work per GL-CMD-BLUEPRINT-PHASE-1-MERGED-EVE-20260707-v2 preamble."
3. **Baseline harness run** — binding_windows_acceptance + cross_sense_recall_acceptance. Save baseline.
4. **Build engine-side changes** per this dispatch. Commit incrementally.
5. **Deploy** with `RECALL_BACKEND=legacy`. Force deploy.
6. **Post-deploy harness run** — same scenarios. Confirm LEGACY BEHAVIOR UNCHANGED (this is the critical safety check — the new mechanism should not affect legacy operation).
7. **STDP state build verification** — after ~5 minutes of live input:
   - `_word_neuron_map` non-empty
   - STDP synapse weights show non-default values on neurons that fired
   - Spike queue drains regularly (bounded depth)
8. **Shadow mode test** — deploy to test service with `RECALL_BACKEND=shadow`. Run 20 minutes of realistic reading. Compare legacy vs STDP top-vote agreement rate. Report percentage.
9. **State disposition** — leave production on `RECALL_BACKEND=legacy`. Shadow measurement drives the future cutover decision, not this dispatch.

## Rollback

- Task-def revert
- `EVENT_DRIVEN_SUBSTRATE=0` — disables spike bus injection entirely, falls back to pure legacy path
- `RECALL_BACKEND=legacy` — already default; explicit fallback if `shadow` or `stdp` causes issues

## Scope guardrails

Do NOT:
- Delete binding_atlas, experience_moment, or any part of the legacy recall path
- Migrate `_select_by_chi_familiarity`
- Add lateral inhibition, metabolism, neuromodulation, sleep-as-work, or seed changes
- Modify the wave atlas write path
- Change any harness or scenario
- Tune HEURISTIC values beyond dispatch-specified starting values
- Flip production to `RECALL_BACKEND=stdp` (that's a follow-up dispatch after shadow verification)

If any of the above becomes tempting, halt and route to Eve.

## Report

`GL-RPT-BLUEPRINT-PHASE-1-MERGED-C1-20260707-v2.md` with:
- Files touched + diff summary
- Backup + neuron-parked-work-commit confirmation
- Baseline + postdeploy scenario results (must show legacy unchanged)
- STDP state build verification (word_neuron_map size, synapse weight distribution, spike queue depth over time)
- Shadow mode results if attempted (agreement rate between legacy and STDP)
- Any HEURISTIC values that surfaced needing adjustment (with measurement data)
- Any scope-boundary concerns encountered
- Findings needing Eve routing

Do not ask Joe questions. Route to Eve.

---

### Changelog
- v2 (2026-07-07, Eve): rewritten after dependency audit surfaced seven substantive errors in v1. Dual-write dual-read design: legacy `binding_atlas` / `experience_moment` / `recall_fast` path preserved throughout Phase 1; new STDP / spike / membrane / word_neuron_map mechanism runs in parallel; `RECALL_BACKEND` env var gates read cutover; shadow mode enables verification before production flip. Cluster's `_select_by_chi_familiarity` untouched (Phase 2). All four `recall_fast` callers preserved via unchanged legacy default. c1's parked neuron-side work (b91b692 + uncommitted +254/-69) preserved as-is.
- v1 (2026-07-07, Eve): superseded. Design errors: treated `chi_atlas` as recall backing (wrong — it's `binding_atlas`); missed three of four `recall_fast` callers; skipped bridge design for `experience_word` write path; skipped `_select_by_chi_familiarity` as chi_atlas reader; assumed helper methods existed that didn't; didn't account for c1's parked work.
