# GL-CMD-BLUEPRINT-PHASE-1-MERGED-EVE-20260707-v1

**doc_id:** GL-CMD-BLUEPRINT-PHASE-1-MERGED-EVE-20260707-v1
**Author:** Eve
**To:** c1
**Ordered by:** Joe (2026-07-07 session — after c1's halt on GL-CMD-BLUEPRINT-PHASE-1-NEURON-AUTONOMY-EVE-20260707-v1)
**Blueprint:** `GL-BLUEPRINT-AE-SUBSTRATE-EVE-20260707-v2` §3.1, §3.3, §3.4, §4 Phase 1
**Supersedes:** `GL-CMD-BLUEPRINT-PHASE-1-NEURON-AUTONOMY-EVE-20260707-v1`. Do not execute that dispatch as written — its factoring was wrong. This dispatch preserves the safe half c1 already built (commit 53bdccd) and adds the missing bridge.

## Why this dispatch exists

c1 halted the prior Phase 1 dispatch correctly. The prior dispatch treated event-driven neurons and STDP synapses as separable phases and assumed the existing chi_atlas machinery would bridge recognition during the gap. Wrong on both counts:

1. **STDP is not optional.** Event-driven neurons produce firing patterns, but without STDP the synapses stay static and no learning happens. Recognition of repeated content requires the pathway to strengthen with exposure. Without STDP, the substrate looks alive but doesn't get faster or more selective with experience.

2. **Coverage-model chi_atlas can't bridge.** Recognition, recall, and emission currently read the chi_atlas as coverage-of-chi-regions. Event-driven neurons produce firing events, not coverage. Writing firing events into the atlas doesn't restore what the readers need — the readers need coverage semantics that the new mechanism doesn't produce.

The fix: Phase 1 becomes the whole substrate replacement. Event-driven firing PLUS STDP synapses PLUS emission-reads-membrane-state PLUS recall-walks-STDP-graph. When it lands, recognition works end-to-end because all the parts of recognition are present. The coverage-model chi_atlas gets deprecated at end of dispatch — no bridge needed because nothing reads it anymore.

## What's preserved from c1's parked work

Commit 53bdccd on origin/guala-live contains built and tested:
- `dsf_ai_service/substrate/spike_bus.py` — SpikeBus infrastructure, priority queue, background delivery thread, tested two-neuron signal pass
- Neuron modifications in `dsf_ai_service/loom_model/neuron.py` — receive_spike, _fire, membrane state fields, refractory handling, propagation delay computation

All of that is correct and stands. This dispatch preserves it and builds on top.

## What's being added

### 1. STDP synapse plasticity

Modify `dsf_ai_service/loom_model/neuron.py` `_fire` method and add spike-timing tracking.

**Add per-neuron recent presynaptic firing history:**
```python
# In __init__:
self._recent_presynaptic_fires: dict = {}
# Maps source_neuron_id -> list of (fire_time_s, contribution_weight)
# Bounded window; old entries pruned during receive_spike
```

**In `receive_spike`, before delivering the spike, record the presynaptic fire:**
```python
def receive_spike(self, spike):
    with self._neuron_lock:
        now = time.monotonic()
        source_id = spike.source_neuron_id
        # Record this presynaptic contribution for STDP window
        self._recent_presynaptic_fires.setdefault(source_id, []).append(
            (now, spike.weight)
        )
        # Prune entries older than STDP_WINDOW_MS
        cutoff = now - STDP_WINDOW_MS / 1000.0
        self._recent_presynaptic_fires[source_id] = [
            (t, w) for t, w in self._recent_presynaptic_fires[source_id]
            if t > cutoff
        ]
        # ... rest of existing receive_spike (decay, add potential, threshold check) ...
```

**HEURISTIC:** `STDP_WINDOW_MS = 40.0` — captures ±20ms potentiation and depression windows. Class: from-biology-reference. Measurement plan: verify learning curves show potentiation on repeat exposure; if learning is unstable, adjust window symmetrically.

**In `_fire`, apply STDP to incoming synapse weights based on recent presynaptic fires:**
```python
def _fire(self, now):
    # Reset membrane and set refractory (existing code)
    self.membrane_potential = self.membrane_rest
    self.refractory_until_s = now + self.refractory_period_ms / 1000.0

    # STDP update: for each recent presynaptic contribution, strengthen
    # the synapse from that source. This is the local learning rule.
    for source_id, fires in self._recent_presynaptic_fires.items():
        for fire_time, contribution in fires:
            dt_ms = (now - fire_time) * 1000.0
            if 0 < dt_ms <= STDP_POTENTIATION_WINDOW_MS:
                # Pre fired before post — strengthen the synapse
                delta = STDP_POTENTIATION_AMPLITUDE * math.exp(-dt_ms / STDP_TAU_MS)
                self._incoming_synapse_weights[source_id] = min(
                    self._incoming_synapse_weights.get(source_id, DEFAULT_SYNAPSE_WEIGHT) + delta,
                    MAX_SYNAPSE_WEIGHT,
                )

    # Depression: for outgoing synapses to neurons that fired before this one,
    # weaken those synapses. Handled by target-neuron side via _record_our_fire_downstream.
    self._notify_downstream_of_fire(now)

    # Emit spikes to coupled neighbors using CURRENT synapse weights
    # (which include any STDP updates just applied)
    for target_id, weight in self._get_outgoing_synapses():
        delay_ms = self._compute_propagation_delay_ms(target_id)
        self._spike_bus.inject(
            target_id=target_id,
            source_id=self.neuron_id,
            weight=weight,
            arrival_delay_ms=delay_ms,
        )

    # Bookkeeping to preserve substrate observability
    self._on_fire_bookkeeping(now)
```

**HEURISTIC:** `STDP_POTENTIATION_WINDOW_MS = 20.0`, `STDP_POTENTIATION_AMPLITUDE = 0.02`, `STDP_TAU_MS = 20.0`. Class: from-biology-reference. Measurement plan: measure synapse weight distribution after 5 minutes of reading; if weights saturate at max or stay near default, adjust amplitude proportionally.

**HEURISTIC:** `MAX_SYNAPSE_WEIGHT = 5.0`, `DEFAULT_SYNAPSE_WEIGHT = 0.05`. Class: from-design. Prevents runaway from unbounded potentiation. Measurement plan: monitor for saturation; adjust ceiling if learning plateaus.

**Depression:** implement via `_notify_downstream_of_fire` — when neuron A fires, it notifies each of its outgoing targets that "A just fired at time now". Each target checks whether IT fired recently; if it did, the A→target synapse gets depressed (target fired before source, wrong order for potentiation, so synapse weakens).

```python
def _notify_downstream_of_fire(self, now):
    """Tell each outgoing target that we just fired, so they can apply
    STDP depression if they fired before us."""
    for target_id, _ in self._get_outgoing_synapses():
        target = self._spike_bus.get_neuron(target_id)
        if target is not None:
            target._receive_upstream_fire_notification(self.neuron_id, now)


def _receive_upstream_fire_notification(self, source_id, source_fire_time):
    """A source fired; if we fired recently before source, weaken
    the source→us synapse (depression)."""
    with self._neuron_lock:
        if self._last_fire_time_s is not None:
            dt_ms = (source_fire_time - self._last_fire_time_s) * 1000.0
            if 0 < dt_ms <= STDP_DEPRESSION_WINDOW_MS:
                delta = STDP_DEPRESSION_AMPLITUDE * math.exp(-dt_ms / STDP_TAU_MS)
                current = self._incoming_synapse_weights.get(source_id, DEFAULT_SYNAPSE_WEIGHT)
                self._incoming_synapse_weights[source_id] = max(
                    current - delta,
                    MIN_SYNAPSE_WEIGHT,
                )
```

**HEURISTIC:** `STDP_DEPRESSION_WINDOW_MS = 20.0`, `STDP_DEPRESSION_AMPLITUDE = 0.015`, `MIN_SYNAPSE_WEIGHT = 0.0`. Class: from-biology-reference. Depression amplitude slightly less than potentiation to bias toward strengthening (biological asymmetry). Measurement plan: verify that novel exposures produce net-positive synapse changes on repeat.

**Track last fire time:**
```python
# In __init__:
self._last_fire_time_s: Optional[float] = None
# In _fire, before or after reset:
self._last_fire_time_s = now
```

**Store incoming synapse weights per neuron:**
```python
# In __init__:
self._incoming_synapse_weights: dict = {}
# Maps source_neuron_id -> current synapse weight from that source
# Initialized on first spike from that source
```

### 2. Membrane-state emission

Replace `_brain_emission_candidates` in `Guala`:

```python
def _brain_emission_candidates(self):
    """Emission candidates are neurons with elevated current membrane
    potential — they represent what the substrate is currently
    processing, not what's stored in a coverage log.
    """
    candidates = []
    for neuron in self._all_neurons():
        with neuron._neuron_lock:
            # Read current membrane state (decays automatically via
            # receive_spike; here we snapshot without disturbing state)
            now = time.monotonic()
            dt_ms = (now - neuron.last_update_time_s) * 1000.0
            if dt_ms > 0:
                decay = math.exp(-dt_ms / neuron.tau_m_ms)
                current_potential = (
                    neuron.membrane_rest
                    + (neuron.membrane_potential - neuron.membrane_rest) * decay
                )
            else:
                current_potential = neuron.membrane_potential

        if current_potential > EMISSION_THRESHOLD:
            associated_word = self._neuron_to_word(neuron)
            candidates.append((
                neuron.chi_position,
                current_potential,
                associated_word,
            ))

    return sorted(candidates, key=lambda x: x[1], reverse=True)[:TOP_K_EMISSION]
```

**HEURISTIC:** `EMISSION_THRESHOLD = 0.5`, `TOP_K_EMISSION = 20`. Class: from-design. Measurement plan: verify emission draws from neurons whose recent spike history matches the input context; adjust threshold if emission is too broad (lower threshold) or too silent (higher threshold).

`_neuron_to_word(neuron)` — reads the association between neurons and words. In Phase 1 this comes from the same source the current substrate uses (word-neuron mapping in existing code). Phase 6 (seed) will populate this from seed data; between now and then, live-experience associations get written by the same paths that currently write to chi_atlas (adjusted to write neuron-word rather than chi-word).

### 3. Membrane-state recall

Replace `recall_fast` and related recall paths:

```python
def _recall_from_cue(self, cue_chi_or_neuron):
    """Recall = inject a spike at the cue neuron; spike propagates via
    STDP-strengthened coupling graph; downstream neurons that were
    frequently co-active with the cue fire; their word associations
    ARE the recall result.
    """
    if isinstance(cue_chi_or_neuron, int):
        cue_neurons = self._chi_to_neurons(cue_chi_or_neuron)
    else:
        cue_neurons = [cue_chi_or_neuron]

    # Inject cue spikes
    injection_time = time.monotonic()
    for cue_neuron in cue_neurons:
        self._spike_bus.inject(
            target_id=cue_neuron.neuron_id,
            source_id="_recall_cue_",
            weight=RECALL_INJECTION_WEIGHT,
            arrival_delay_ms=0.0,
            metadata={"purpose": "recall"},
        )

    # Wait a short window for propagation to settle
    time.sleep(RECALL_PROPAGATION_WINDOW_MS / 1000.0)

    # Read the membrane state of ALL neurons; ones that were driven
    # up by the propagation are the recall result
    now = time.monotonic()
    activated = []
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

        if potential > RECALL_ACTIVATION_THRESHOLD:
            associated = self._neuron_to_word(neuron)
            activated.append((neuron.chi_position, potential, associated))

    return sorted(activated, key=lambda x: x[1], reverse=True)
```

**HEURISTIC:** `RECALL_INJECTION_WEIGHT = 2.0`, `RECALL_PROPAGATION_WINDOW_MS = 30.0`, `RECALL_ACTIVATION_THRESHOLD = 0.3`. Class: from-design. Measurement plan: verify recall from a familiar cue returns semantically related words after STDP has trained the coupling graph; adjust injection weight if recall is too broad or too narrow.

Existing callers of `recall_fast` (there are many) get the same function name and signature but the implementation is now the STDP-graph walk. Result format matches existing consumers.

### 4. Bridge between substrate write paths and new mechanisms

Existing substrate code writes to chi_atlas at multiple points (including neuron._on_fire_bookkeeping which c1's parked work already wires up). These writes were correct for coverage semantics. In Phase 1 they continue to run, but nothing reads from chi_atlas — emission and recall now go through membrane state and STDP.

The chi_atlas becomes append-only observability during Phase 1. At end of Phase 1 (deprecation step below), the writes are removed and the atlas is deleted.

**Word-to-neuron mapping:** the association currently held in `chi_atlas` entries (word X → chi Y) needs a separate lightweight mapping since Phase 1 doesn't use chi_atlas for recognition. Add:

```python
# In Guala.__init__:
self._word_neuron_map: dict = {}  # word -> set of neuron_ids that fire for this word
self._neuron_word_map: dict = {}  # neuron_id -> word (primary association)
```

When live input arrives that has a word attached, and neuron N fires in response, record the association:

```python
def _on_word_firing(self, word: str, neuron: LoomNeuron):
    self._word_neuron_map.setdefault(word, set()).add(neuron.neuron_id)
    if neuron.neuron_id not in self._neuron_word_map:
        self._neuron_word_map[neuron.neuron_id] = word
```

Called from `_on_fire_bookkeeping` when a word context is available. Phase 6 (seed) will populate this map at boot for seeded vocabulary.

### 5. Coverage-model chi_atlas deprecation

At end of Phase 1, once all callers of chi_atlas.match_score and chi_atlas.record have been migrated to the new mechanisms:

- Remove `chi_atlas.record` calls from `_on_fire_bookkeeping`
- Remove `chi_atlas.match_score` calls from any remaining code (grep-check)
- Mark `ChiAtlas` class as deprecated with a runtime warning
- Delete `ChiAtlas` in the next dispatch after Phase 1 confirmation

Do NOT delete `ChiAtlas` in Phase 1 itself. Keep it around, keep writes going (as observability), verify nothing reads it anymore. Delete in the follow-up cleanup dispatch after Phase 1 has stabilized in production.

### 6. LoomBrain.step and injection dispatch

Preserved from c1's parked work. `LoomBrain.step` becomes injection dispatch — signals become spikes injected into entry neurons, function returns immediately, propagation happens in background via SpikeBus.

Entry neuron selection: for input with a specific chi (from the shared krimelack that already runs for wave atlas writes), inject at neurons whose chi_position is near the input chi. For input without specific chi (multimodal), broadcast injection at a small random sample.

```python
def step(self, input_signal, tick, input_chi=None, modality=None):
    entry_neurons = self._select_entry_neurons(input_chi, modality)
    injection_weight = self._signal_to_weight(input_signal)
    for neuron in entry_neurons:
        self._spike_bus.inject(
            target_id=neuron.neuron_id,
            source_id="_input_injection_",
            weight=injection_weight,
            arrival_delay_ms=0.0,
            metadata={"input_tick": tick, "input_chi": input_chi},
        )
    return {"injected": len(entry_neurons), "tick": tick}


def _select_entry_neurons(self, input_chi, modality):
    """Select neurons to receive initial injection.

    Phase 1: chi-proximity selection if input_chi provided;
    otherwise a broad selection.
    Phase 2 will refine via lateral inhibition.
    """
    if input_chi is None:
        # No specific address — inject broadly (small random sample)
        return random.sample(self._all_neurons(), min(16, len(self._all_neurons())))
    # Select neurons whose chi_position is within ENTRY_CHI_BAND of input_chi
    candidates = [
        n for n in self._all_neurons()
        if abs(n.chi_position - input_chi) < ENTRY_CHI_BAND
    ]
    if not candidates:
        # No neurons in range — spawn or fall back to random sample
        return random.sample(self._all_neurons(), min(4, len(self._all_neurons())))
    return candidates
```

**HEURISTIC:** `ENTRY_CHI_BAND = 8` — how far in chi space input injection reaches. Class: from-design. Measurement plan: measure emission quality with different band widths; adjust if input isn't reaching relevant neurons.

## What is NOT in Phase 1

Strict boundary. Halt if any of these appear:
- Lateral inhibition (Phase 2)
- Metabolic energy budget (Phase 3)
- Neuromodulation broadcast (Phase 4)
- Sleep-as-work consolidation (Phase 5)
- Population-based seed content generation (Phase 6)

**Explicitly preserved untouched:**
- Wave atlas write path (Phase 1 doesn't modify wave atlas)
- Binding window formation
- Cross-sense binding logic

## Halt conditions

1. **Recognition doesn't emerge** — after ~5 minutes of repeated input, response speed and selectivity don't improve. Would mean STDP isn't strengthening the right synapses, or emission isn't reading the right state. Halt with data.
2. **Recall returns nothing** — STDP-walk from a cue produces no activated neurons. Would mean coupling graph doesn't propagate. Halt.
3. **Correctness regression on harness scenarios** beyond what's expected from the coverage → event-driven transition. Halt with specific scenario.
4. **Runaway firing** — total network activity grows without bound. STDP might be over-potentiating. Halt with data.
5. **Silent substrate** — no neurons fire at all after input. Would mean threshold/weight tuning is wrong for the current default parameters. Halt.
6. **Scope violation** — c1 finds self implementing Phase 2+ mechanism (lateral inhibition, metabolism, etc.) to make Phase 1 work. Halt immediately.

Any halt: route with data, do not extend scope unilaterally.

## Harness protocol

Standard six-step plus Phase-1-specific verification:

1. Backup as `pre-blueprint-phase1-merged-<timestamp>`. Verify restorable.
2. Baseline harness run: binding_windows_acceptance + cross_sense_recall_acceptance. Save baseline.
3. Deploy: commit (starting from 53bdccd), push, build, task-def, force deploy.
4. Post-deploy harness run: same scenarios. Save postdeploy.
5. Compare:
   - Event counts remain consistent (windows, entries)
   - Emission produces valid output (may differ in specifics — that's expected)
   - Recall returns semantically-related results after some exposure
   - `_autonomy_tick` drops to near-zero (event-driven active)
   - New events observed: spike propagation, STDP updates, membrane state changes
6. **Learning verification**:
   - Send the same word 20 times
   - Measure response latency per iteration
   - Should DROP as STDP strengthens the recognition pathway
   - Also verify: 5th vs 15th vs 20th response are increasingly selective (fewer other neurons firing, more concentrated on the specific pathway)
7. **Recall verification**:
   - After a passage has been read (a few minutes of live input), inject a cue that appeared in that passage
   - Recall should return words that co-occurred with the cue
   - Measure recall speed (should be fast — spike propagation window)
8. **State disposition**: leave in place unless Joe routes otherwise.

## Rollback

Task-def revert. Feature flag: `EVENT_DRIVEN_SUBSTRATE=0` falls back to iterative brain.step path.

## Report

`GL-RPT-BLUEPRINT-PHASE-1-MERGED-C1-20260707-v1.md` with:
- Files touched + diff summary
- Backup confirmation
- Baseline + postdeploy scenario results
- Learning verification data (response latency curve over 20 repeats)
- Recall verification data (recall speed, semantic relevance)
- HEURISTIC values that surfaced needing adjustment (with measurement data)
- Any scope-boundary concerns encountered
- Findings needing Eve routing

Do not ask Joe questions. Route to Eve.

---

### Changelog
- v1 (2026-07-07, Eve): initial merged Phase 1 dispatch after v1 (unmerged) halt. Preserves c1's parked spike bus and receive_spike/fire work (commit 53bdccd). Adds STDP synapse plasticity (potentiation + depression), membrane-state emission (candidates from current potential), membrane-state recall (STDP-graph walk from cue), word-neuron mapping to preserve associations, and coverage-model chi_atlas deprecation path.
