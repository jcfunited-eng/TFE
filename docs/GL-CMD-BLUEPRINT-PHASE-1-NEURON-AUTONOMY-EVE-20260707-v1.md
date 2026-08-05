# GL-CMD-BLUEPRINT-PHASE-1-NEURON-AUTONOMY-EVE-20260707-v1

**doc_id:** GL-CMD-BLUEPRINT-PHASE-1-NEURON-AUTONOMY-EVE-20260707-v1
**Author:** Eve
**To:** c1
**Ordered by:** Joe (2026-07-07 session)
**Blueprint:** `GL-BLUEPRINT-AE-SUBSTRATE-EVE-20260707-v1` §3.1, §3.3, §4 Phase 1

## Verdict

Build the event-driven per-neuron autonomy foundation. Neurons stop being iterated. They react to spike arrivals. Between spikes they decay. There is no central tick. External callers inject input as spikes; a background spike bus delivers spikes to their targets as their propagation delays elapse; neurons update state and fire in response to arrivals; firing enqueues new spikes to coupled neighbors with computed delays.

Bounded scope: spike bus infrastructure, neuron event-handler transformation, external callsite migration to injection pattern, harness verification. No STDP, no lateral inhibition, no metabolism, no neuromodulation, no sleep-as-work, no seed rebuild. Those are later phases and MUST NOT be smuggled in.

## What's being built

### 1. Spike bus module

New file: `dsf_ai_service/substrate/spike_bus.py`

Central priority queue of pending spikes ordered by arrival time. A dedicated background thread drains the queue and delivers each spike to its target neuron when arrival time has elapsed.

```python
@dataclass(order=True)
class PendingSpike:
    arrival_time: float                # wall clock when this spike arrives
    target_neuron_id: str = field(compare=False)
    source_neuron_id: str = field(compare=False)
    weight: float = field(compare=False)
    metadata: dict = field(default_factory=dict, compare=False)


class SpikeBus:
    def __init__(self, neuron_registry):
        self._queue = queue.PriorityQueue()
        self._neuron_registry = neuron_registry
        self._stopping = threading.Event()
        self._thread = None

    def start(self):
        self._thread = threading.Thread(
            target=self._delivery_loop, daemon=True, name="spike_bus"
        )
        self._thread.start()

    def stop(self):
        self._stopping.set()
        if self._thread:
            self._thread.join(timeout=5.0)

    def inject(self, target_id: str, source_id: str, weight: float,
               arrival_delay_ms: float = 0.0, metadata: dict = None):
        arrival_time = time.monotonic() + arrival_delay_ms / 1000.0
        spike = PendingSpike(
            arrival_time=arrival_time,
            target_neuron_id=target_id,
            source_neuron_id=source_id,
            weight=weight,
            metadata=metadata or {},
        )
        self._queue.put(spike)

    def _delivery_loop(self):
        while not self._stopping.is_set():
            try:
                spike = self._queue.get(timeout=0.01)
            except queue.Empty:
                continue
            now = time.monotonic()
            wait = spike.arrival_time - now
            if wait > 0:
                # This spike is in the future — sleep until arrival
                # (or until stopping signal). Put it back and wait.
                if wait > 0.001:
                    self._queue.put(spike)
                    time.sleep(min(wait, 0.05))
                    continue
                # very close, just deliver
            target = self._neuron_registry.get(spike.target_neuron_id)
            if target is not None:
                try:
                    target.receive_spike(spike)
                except Exception:
                    log.exception("spike delivery failed", extra={"target": spike.target_neuron_id})
```

### 2. Neuron event-handler transformation

Modify `dsf_ai_service/loom_model/neuron.py`:

**Add fields to `LoomNeuron.__init__`:**
- `self.membrane_potential: float = 0.0` — current depolarization
- `self.membrane_rest: float = 0.0` — rest potential
- `self.membrane_threshold: float = 1.0` — firing threshold (Phase 5 will make this modulator-adjusted; Phase 1 keeps it static)
- `self.tau_m_ms: float = 20.0` — membrane time constant. HEURISTIC: biological range for cortical pyramidal neurons. Measurement plan: adjust if firing rates diverge from 1-4% population target after Phase 3.
- `self.refractory_period_ms: float = 2.0` — HEURISTIC: biological absolute refractory. Measurement plan: verify no neuron fires faster than 500Hz sustained; adjust if observed.
- `self.last_update_time_s: float = 0.0` — wall clock of last state update
- `self.refractory_until_s: float = 0.0` — wall clock until which further firing suppressed
- `self._neuron_lock: threading.Lock = threading.Lock()` — per-neuron state lock (spike arrivals concurrent from bus)

**Add method `receive_spike(spike)`:**

```python
def receive_spike(self, spike):
    """Called by spike bus when a spike arrives at this neuron.

    Updates membrane potential based on time since last update,
    adds the spike's weighted contribution, checks threshold,
    fires if crossed and not refractory.
    """
    with self._neuron_lock:
        now = time.monotonic()
        dt_ms = (now - self.last_update_time_s) * 1000.0
        # Exponential decay of membrane potential toward rest
        if dt_ms > 0:
            decay = math.exp(-dt_ms / self.tau_m_ms)
            self.membrane_potential = (
                self.membrane_rest
                + (self.membrane_potential - self.membrane_rest) * decay
            )
        # Add incoming spike contribution
        self.membrane_potential += spike.weight
        self.last_update_time_s = now

        # Refractory check
        if now < self.refractory_until_s:
            return  # absorbed but no firing

        # Threshold check
        if self.membrane_potential >= self.membrane_threshold:
            self._fire(now)


def _fire(self, now):
    """Neuron fires: reset membrane, set refractory, emit spikes to
    all coupled neighbors via spike bus with computed delays."""
    self.membrane_potential = self.membrane_rest
    self.refractory_until_s = now + self.refractory_period_ms / 1000.0

    # Emit spikes to coupled neighbors
    for target_id, weight in self._get_outgoing_synapses():
        delay_ms = self._compute_propagation_delay_ms(target_id)
        self._spike_bus.inject(
            target_id=target_id,
            source_id=self.neuron_id,
            weight=weight,
            arrival_delay_ms=delay_ms,
        )

    # Existing bookkeeping: record commit, update chi_atlas, etc.
    # These stay wired via existing mechanisms for now — Phase 2 will
    # transform chi_atlas into STDP synapse weights.
    self._on_fire_bookkeeping(now)
```

**Add method `_compute_propagation_delay_ms(target_id)`:**

```python
def _compute_propagation_delay_ms(self, target_id):
    """Delay is a function of chi-distance between source and target."""
    target = self._spike_bus._neuron_registry.get(target_id)
    if target is None:
        return DEFAULT_DELAY_MS
    chi_distance = abs(self.chi_position - target.chi_position)
    # HEURISTIC: linear scaling with chi-distance, 1-20ms range.
    # Class: from-design (chi-distance stands in for physical distance
    # since substrate has no literal physical positions).
    # Measurement plan: verify propagation patterns produce realistic
    # spike-timing distributions; adjust if temporal binding fails.
    delay = 1.0 + (chi_distance / MAX_CHI_DISTANCE) * 19.0
    return delay
```

**Add method `_get_outgoing_synapses()`:**

Returns list of `(target_id, weight)` tuples derived from the existing coupling structure. In Phase 1 this reads from the existing `CouplingsJij` structure (ring topology, 16 neighbors). Phase 2 will make the weights dynamic via STDP.

```python
def _get_outgoing_synapses(self):
    """Read current outgoing coupling weights from CouplingsJij."""
    # Phase 1: static weights from existing coupling structure
    # Phase 2: STDP-updated dynamic weights
    synapses = []
    for j_index, target_neuron in enumerate(self._coupled_neighbors):
        weight = self.couplings.J[j_index]
        if weight != 0.0:
            synapses.append((target_neuron.neuron_id, weight))
    return synapses
```

**Add method `_on_fire_bookkeeping(now)`:**

Records the fire event to the existing chi_atlas (chi unification from earlier today preserved), event stream, and any downstream consumer. This preserves current substrate observability without changing what those consumers see.

**Preserve `LoomNeuron.step`:**

Old `step(input_signal, tick)` method stays as a compatibility shim. When called (from unmigrated callers during transition), it injects a synthetic spike into itself and processes via the new event handler. Deprecation warning logged. Removed in Phase 2 when all callers have migrated.

```python
def step(self, input_signal, tick, input_chi=None):
    """DEPRECATED: use SpikeBus injection instead.

    Compatibility shim during Phase 1 migration. Converts input_signal
    into a synthetic spike and delivers directly via receive_spike.
    """
    log.warning("LoomNeuron.step called directly; migrate to SpikeBus.inject",
                stacklevel=2)
    synthetic_weight = self._legacy_input_to_weight(input_signal)
    synthetic_spike = PendingSpike(
        arrival_time=time.monotonic(),
        target_neuron_id=self.neuron_id,
        source_neuron_id="_legacy_step_",
        weight=synthetic_weight,
        metadata={"legacy_tick": tick, "input_chi": input_chi},
    )
    self.receive_spike(synthetic_spike)
    return self._legacy_result_snapshot()
```

### 3. LoomCluster and LoomBrain transformation

`LoomCluster.step` and `LoomBrain.step` currently iterate neurons. They become **injection dispatchers** that convert incoming signals into initial spike sets and hand them to the spike bus.

**LoomBrain.step:**

```python
def step(self, input_signal, tick, input_chi=None, modality=None):
    """Injects the input signal into the substrate via SpikeBus.

    Returns immediately. Actual neuron responses happen asynchronously
    as spikes propagate. Callers that need response data should either:
    - Poll the substrate state after allowing propagation time
    - Subscribe to the event stream for fire notifications
    - Use the emission API which reads current membrane state directly
    """
    # Determine which neurons receive the initial injection
    # (Phase 1: broad injection matching current behavior; Phase 3 will
    # narrow via sparse activity / lateral inhibition; Phase 5 will
    # further narrow via attentional modulation.)
    entry_neurons = self._select_entry_neurons(input_chi, modality)
    initial_weight = self._signal_to_weight(input_signal)

    for neuron in entry_neurons:
        self._spike_bus.inject(
            target_id=neuron.neuron_id,
            source_id="_input_injection_",
            weight=initial_weight,
            arrival_delay_ms=0.0,
        )
    return {"injected": len(entry_neurons), "tick": tick}
```

`LoomCluster.step` becomes a no-op with a deprecation log, kept for compatibility.

### 4. Spike bus lifecycle

The spike bus starts when the substrate boots and stops when the substrate shuts down.

Add to `Guala.__init__`:
```python
self._spike_bus = SpikeBus(neuron_registry=self._get_neuron_registry())
```

Add to substrate startup:
```python
self._spike_bus.start()
```

Add to substrate shutdown:
```python
self._spike_bus.stop()
```

Register every neuron with the spike bus's neuron registry so spike delivery can look them up by ID.

### 5. Emission integration

`_brain_emission_candidates` currently reads from `organism.recall_fast`. In Phase 1 this stays wired but reads the neuron membrane states directly rather than the coverage-model chi_atlas:

```python
def _brain_emission_candidates(self):
    """Read current highly-depolarized neurons as emission candidates."""
    candidates = []
    for neuron in self._get_all_neurons():
        if neuron.membrane_potential > EMISSION_THRESHOLD:
            candidates.append((neuron.chi_position,
                              neuron.membrane_potential,
                              neuron.get_associated_word()))
    return sorted(candidates, key=lambda x: x[1], reverse=True)[:TOP_K]
```

**HEURISTIC:** `EMISSION_THRESHOLD = 0.5` — half of firing threshold, captures neurons approaching fire. Class: from-design. Measurement plan: verify emission draws from actively-processing neurons; adjust if emission is too broad or too silent.

Emission does NOT wait for firing — it reads membrane state at query time. This is correct: an AE emitting is emitting from its current state, not from a fire event.

### 6. What is NOT being built (Phase 1 boundary — enforced)

**Explicitly not in Phase 1:**
- No STDP synapse weight updates (Phase 2)
- No lateral inhibition or sparse-activity enforcement (Phase 3)
- No metabolic energy budget (Phase 4)
- No neuromodulation broadcast (Phase 5)
- No sleep-as-work consolidation (Phase 6)
- No population-based seed content (Phase 7)

If any of these get "just a little" work in this dispatch, that's scope creep. c1 halts and routes.

**Explicitly preserved:**
- Existing chi_atlas continues to be written by `_on_fire_bookkeeping` (Phase 2 replaces it)
- Existing wave atlas write path continues (untouched)
- Existing binding windows continue (untouched)
- Existing cross-sense recall continues (untouched)
- Existing emission composition continues (candidates now come from membrane state)
- Existing coupling J matrix used as read-only source for outgoing synapse weights

## Halt conditions

1. **Spike bus doesn't scale** — spike queue depth grows without bound under realistic input load. This would indicate the delivery loop can't keep up with fire rates. Halt with queue depth measurements.
2. **Correctness regression** — harness scenarios show different event counts or emission behavior after transformation. Halt with specific scenario and observed vs expected.
3. **Deadlock or thread-safety issue** — spike bus thread and existing worker threads block each other, or per-neuron locks introduce hangs. Halt with reproduction.
4. **Membrane state divergence** — after equivalent input, event-driven substrate produces qualitatively different membrane patterns than the iterative one would have. Halt with data — this may indicate the migration missed a state variable.
5. **Scope violation** — c1 finds themselves implementing STDP, lateral inhibition, metabolism, or any Phase 2+ mechanism to make Phase 1 work. Halt immediately, route to Eve. The blueprint's phase boundaries are load-bearing.

Any halt: route with data, do NOT extend scope unilaterally.

## Harness protocol

Standard six-step plus a Phase-1-specific event-driven verification:

1. **Backup** — `pre-blueprint-phase1-<timestamp>`. Verify restorable.
2. **Baseline harness run** — binding_windows_acceptance + cross_sense_recall_acceptance. Save baseline.
3. **Deploy** — commit, push, build, task-def, force deploy.
4. **Post-deploy harness run** — same scenarios. Save postdeploy.
5. **Compare**:
   - Same event counts (window_opened, window_entry_added, window_closed, recall_query_executed)
   - Emission produces valid output
   - `_autonomy_tick` in event stream: SHOULD DROP TO NEAR ZERO or disappear (no central tick anymore)
   - Spike bus events observed (new event stream entries: `spike_injected`, `spike_delivered`, `neuron_fired`)
6. **Event-driven verification**:
   - Inject a single input; observe spike propagation through the coupled network in real time
   - Measure spike queue depth over 5 minutes of reading — should stay bounded, drain regularly
   - Verify neuron firing is asynchronous — no synchronized firing pattern that would indicate residual central-tick behavior
7. **State disposition** — leave in place unless Joe routes otherwise.

## Rollback

Task-def revert. Or `SPIKE_BUS_ENABLED=0` env var to fall back to legacy step iteration path (kept behind flag for one dispatch cycle then removed in Phase 2).

## Scope guardrails

Do NOT:
- Add STDP, lateral inhibition, metabolism, neuromodulation, sleep-as-work, or seed changes
- Modify the existing chi_atlas.record semantics (Phase 2 territory)
- Modify wave atlas or binding windows (Phase 1 doesn't touch them)
- Tune membrane parameters — HEURISTIC values stand until measurement warrants change
- Add caching or optimization beyond what the base implementation needs
- Rewrite emission logic beyond swapping the candidate source

If Phase 1 raises questions the blueprint doesn't answer, halt and route to Eve. Do not invent architectural decisions unilaterally.

## Report

`GL-RPT-BLUEPRINT-PHASE-1-NEURON-AUTONOMY-C1-20260707-v1.md` with:
- Files touched + diff summary
- Backup confirmation
- Baseline + postdeploy scenario results
- Event-driven verification results (spike propagation, queue depth, async firing)
- Contention measurement: `_autonomy_tick` presence/absence, response latency under load
- Any HEURISTIC values that surfaced needing adjustment (with measurement data)
- Any scope-boundary concerns encountered
- Findings needing Eve routing

Do not ask Joe questions. Route to Eve.

---

### Changelog
- v1 (2026-07-07, Eve): initial Phase 1 dispatch under `GL-BLUEPRINT-AE-SUBSTRATE-EVE-20260707-v1`. Event-driven per-neuron autonomy foundation. SpikeBus infrastructure, neuron receive_spike/fire/propagate methods, LoomBrain.step and LoomCluster.step transformed to injection dispatchers. All Phase 2+ mechanisms explicitly excluded and halt-triggered if attempted.
