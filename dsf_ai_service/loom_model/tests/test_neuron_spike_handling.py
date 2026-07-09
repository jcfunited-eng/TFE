"""
GL-CMD-BLUEPRINT-PHASE-1-MERGED-EVE-20260707-v1 (supersedes v1's
NEURON-AUTONOMY dispatch): unit tests for LoomNeuron spike-handling +
STDP synapse plasticity + word-context bookkeeping. Isolated -- these
methods are wired into LoomBrain.step/Guala in this dispatch (see
test_loom_brain_injection.py / test_guala_lifecycle-adjacent tests for the
wired path); this file exercises LoomNeuron in isolation.

Convention: spike sources starting with "_" are EXTERNAL (unscaled,
no STDP bookkeeping) -- e.g. "_src", "_input_injection_". Sources without
that prefix (e.g. "n2") are treated as real neuron-to-neuron synapses,
subject to STDP scaling and potentiation/depression.
"""

import os
import sys
import time
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from dsf_ai_service.loom_model.neuron import (
    LoomNeuron, DEFAULT_DELAY_MS, STDP_DEFAULT_SYNAPSE_WEIGHT,
    STDP_POTENTIATION_AMPLITUDE, STDP_DEPRESSION_AMPLITUDE,
    MAX_SYNAPSE_WEIGHT, MIN_SYNAPSE_WEIGHT, STDP_WINDOW_MS,
    FIRE_BREAKER_WINDOW_N, FIRE_BREAKER_CEILING_HZ,
)
from dsf_ai_service.substrate.spike_bus import PendingSpike


def _spike(weight, source="_src", target="n1", metadata=None):
    return PendingSpike(arrival_time=time.monotonic(), target_neuron_id=target,
                         source_neuron_id=source, weight=weight, metadata=metadata or {})


# ---------------------------------------------------------------------------
# Membrane integration / firing / refractory / decay (external sources)
# ---------------------------------------------------------------------------

def test_receive_spike_adds_weight_to_membrane():
    n = LoomNeuron("n1")
    n.membrane_threshold = 10.0  # high enough not to fire
    n.receive_spike(_spike(0.3))
    assert abs(n.membrane_potential - 0.3) < 1e-9
    n.receive_spike(_spike(0.2))
    assert n.membrane_potential > 0.2
    print("test_receive_spike_adds_weight_to_membrane: PASS")


def test_receive_spike_fires_at_threshold():
    n = LoomNeuron("n1")
    n.membrane_threshold = 1.0
    n.membrane_rest = 0.0
    n.receive_spike(_spike(1.5))
    assert n.membrane_potential == 0.0, "fired neuron should reset to rest"
    assert n.refractory_until_s > time.monotonic()
    assert n._last_fire_time_s > 0
    print("test_receive_spike_fires_at_threshold: PASS")


def test_refractory_absorbs_without_firing():
    n = LoomNeuron("n1")
    n.membrane_threshold = 1.0
    n.membrane_rest = 0.0
    n.refractory_period_ms = 200.0
    n.receive_spike(_spike(1.5))  # fires, enters refractory
    assert n.membrane_potential == 0.0
    n.receive_spike(_spike(5.0))  # huge spike, but still refractory
    assert n.membrane_potential != 0.0
    assert n.membrane_potential < 5.5  # didn't re-fire
    print("test_refractory_absorbs_without_firing: PASS")


def test_membrane_decays_toward_rest_between_spikes():
    n = LoomNeuron("n1")
    n.membrane_threshold = 100.0
    n.membrane_rest = 0.0
    n.tau_m_ms = 5.0
    n.receive_spike(_spike(1.0))
    v1 = n.membrane_potential
    time.sleep(0.05)
    n.receive_spike(_spike(0.0))
    v2 = n.membrane_potential
    assert v2 < v1, f"expected decay toward rest, got v1={v1} v2={v2}"
    print("test_membrane_decays_toward_rest_between_spikes: PASS")


# ---------------------------------------------------------------------------
# Synapse / propagation (unchanged from prior dispatch)
# ---------------------------------------------------------------------------

def test_get_outgoing_synapses_reduces_j_vector_to_scalar():
    import numpy as np
    n = LoomNeuron("n1")
    n.couplings.neighbors = ["n2", "n3"]
    n.couplings.J = np.array([[0.5] * 16, [0.0] * 16])
    synapses = n._get_outgoing_synapses()
    assert synapses == [("n2", 0.5)], synapses
    print("test_get_outgoing_synapses_reduces_j_vector_to_scalar: PASS")


def test_propagation_delay_defaults_without_chi_position():
    n1 = LoomNeuron("n1")
    assert n1.chi_position is None
    delay = n1._compute_propagation_delay_ms("n2")
    assert delay == DEFAULT_DELAY_MS
    print("test_propagation_delay_defaults_without_chi_position: PASS")


def test_propagation_delay_scales_with_chi_distance_when_positions_set():
    from dsf_ai_service.loom_model.neuron import MAX_CHI_DISTANCE
    n1 = LoomNeuron("n1")
    n2 = LoomNeuron("n2")
    n1.chi_position = 0
    n2.chi_position = MAX_CHI_DISTANCE
    n1._spike_bus = SimpleNamespace(_neuron_registry={"n2": n2})
    delay = n1._compute_propagation_delay_ms("n2")
    assert abs(delay - 20.0) < 1e-6, delay
    print("test_propagation_delay_scales_with_chi_distance_when_positions_set: PASS")


def test_fire_emits_to_spike_bus_when_set():
    n1 = LoomNeuron("n1")
    n1.membrane_threshold = 1.0
    n1.couplings.neighbors = ["n2"]
    import numpy as np
    n1.couplings.J = np.array([[0.7] * 16])

    injected = []

    class _FakeBus:
        _neuron_registry = {}
        def inject(self, target_id, source_id, weight, arrival_delay_ms=0.0, metadata=None):
            injected.append((target_id, source_id, weight, arrival_delay_ms))

    n1.set_spike_bus(_FakeBus())
    n1.receive_spike(_spike(1.5))
    assert injected == [("n2", "n1", 0.7, DEFAULT_DELAY_MS)], injected
    print("test_fire_emits_to_spike_bus_when_set: PASS")


def test_fire_without_spike_bus_does_not_crash():
    n1 = LoomNeuron("n1")
    n1.membrane_threshold = 1.0
    n1.couplings.neighbors = ["n2"]
    import numpy as np
    n1.couplings.J = np.array([[0.7] * 16])
    assert n1._spike_bus is None
    n1.receive_spike(_spike(1.5))
    assert n1.membrane_potential == 0.0
    print("test_fire_without_spike_bus_does_not_crash: PASS")


def test_step_unchanged_by_additions():
    n = LoomNeuron("n1")
    result = n.step("hello", tick=1)
    assert set(result.keys()) == {"committed", "n_eff", "dsf", "spike_count",
                                   "match_score", "delta_eff"}
    print("test_step_unchanged_by_additions: PASS")


# ---------------------------------------------------------------------------
# STDP
# ---------------------------------------------------------------------------

def test_synaptic_spike_scaled_by_default_weight():
    """A real (non-external) source with no prior potentiation contributes
    weight * STDP_DEFAULT_SYNAPSE_WEIGHT, not raw weight."""
    n = LoomNeuron("n1")
    n.membrane_threshold = 100.0  # never fires
    n.receive_spike(_spike(1.0, source="n2"))
    assert abs(n.membrane_potential - STDP_DEFAULT_SYNAPSE_WEIGHT) < 1e-9, n.membrane_potential
    print("test_synaptic_spike_scaled_by_default_weight: PASS")


def test_external_spike_bypasses_stdp_scaling():
    n = LoomNeuron("n1")
    n.membrane_threshold = 100.0
    n.receive_spike(_spike(1.0, source="_input_injection_"))
    assert abs(n.membrane_potential - 1.0) < 1e-9, n.membrane_potential
    assert n._recent_presynaptic_fires == {}
    print("test_external_spike_bypasses_stdp_scaling: PASS")


def test_potentiation_strengthens_synapse_on_fire_shortly_after_presynaptic_spike():
    n = LoomNeuron("n1")
    n.membrane_threshold = 100.0  # don't let the presynaptic spike itself fire us
    n.receive_spike(_spike(0.1, source="n2"))  # presynaptic fire recorded
    assert "n2" in n._recent_presynaptic_fires

    n.membrane_threshold = 0.01  # now make us fire immediately
    n.receive_spike(_spike(1.0, source="_input_injection_"))  # external push over threshold
    assert n.membrane_potential == n.membrane_rest  # fired

    weight = n._incoming_synapse_weights.get("n2")
    assert weight is not None and weight > STDP_DEFAULT_SYNAPSE_WEIGHT, weight
    print("test_potentiation_strengthens_synapse_on_fire_shortly_after_presynaptic_spike: PASS")


def test_potentiation_clamped_to_max():
    n = LoomNeuron("n1")
    n._incoming_synapse_weights["n2"] = MAX_SYNAPSE_WEIGHT - 0.001
    n._recent_presynaptic_fires["n2"] = [(time.monotonic(), 1.0)]
    n._apply_stdp_potentiation(time.monotonic())
    assert n._incoming_synapse_weights["n2"] <= MAX_SYNAPSE_WEIGHT
    print("test_potentiation_clamped_to_max: PASS")


def test_presynaptic_history_pruned_outside_window():
    n = LoomNeuron("n1")
    old_time = time.monotonic() - (STDP_WINDOW_MS / 1000.0) - 1.0
    n._recent_presynaptic_fires["n2"] = [(old_time, 1.0)]
    n._prune_presynaptic_history("n2", time.monotonic())
    assert "n2" not in n._recent_presynaptic_fires
    print("test_presynaptic_history_pruned_outside_window: PASS")


def test_depression_weakens_synapse_when_we_fire_before_source():
    """Classic STDP anti-causal case: downstream neuron fires, THEN
    upstream source fires -- source->downstream synapse weakens."""
    downstream = LoomNeuron("down")
    downstream._incoming_synapse_weights["up"] = 1.0  # start above default/min
    downstream._last_fire_time_s = time.monotonic()  # "we" (downstream) fired first
    time.sleep(0.005)
    source_fire_time = time.monotonic()  # source fires shortly after
    downstream._receive_upstream_fire_notification("up", source_fire_time)
    assert downstream._incoming_synapse_weights["up"] < 1.0
    print("test_depression_weakens_synapse_when_we_fire_before_source: PASS")


def test_depression_clamped_to_min():
    n = LoomNeuron("n1")
    n._incoming_synapse_weights["up"] = MIN_SYNAPSE_WEIGHT + 0.0001
    n._last_fire_time_s = time.monotonic()
    time.sleep(0.001)
    n._receive_upstream_fire_notification("up", time.monotonic())
    assert n._incoming_synapse_weights["up"] >= MIN_SYNAPSE_WEIGHT
    print("test_depression_clamped_to_min: PASS")


def test_notify_downstream_skips_self_loop_no_deadlock():
    n = LoomNeuron("n1")
    n.couplings.neighbors = ["n1"]  # pathological self-loop
    import numpy as np
    n.couplings.J = np.array([[0.5] * 16])
    n.set_spike_bus(SimpleNamespace(_neuron_registry={"n1": n}))
    # must return promptly, not deadlock on its own lock
    n._notify_downstream_of_fire(time.monotonic())
    print("test_notify_downstream_skips_self_loop_no_deadlock: PASS")


def test_two_neuron_stdp_end_to_end_via_real_bus():
    """Real SpikeBus, two real neurons: n1 fires, spike reaches n2 which
    also fires shortly after -- n2's incoming weight for n1 should
    potentiate, and n2's synchronous notification back to n1 (n1 has no
    incoming synapse from n2 recorded yet, so this just exercises the
    notification path without asserting a change there)."""
    import numpy as np
    from dsf_ai_service.substrate.spike_bus import SpikeBus

    n1 = LoomNeuron("n1")
    n2 = LoomNeuron("n2")
    n1.membrane_threshold = 1.0
    n2.membrane_threshold = 0.01  # fires on virtually any input
    n1.couplings.neighbors = ["n2"]
    n1.couplings.J = np.array([[2.0] * 16])  # strong enough to push n2 over threshold

    registry = {"n1": n1, "n2": n2}
    bus = SpikeBus(neuron_registry=registry)
    n1.set_spike_bus(bus)
    n2.set_spike_bus(bus)
    bus.start()
    try:
        bus.inject(target_id="n1", source_id="_input_injection_", weight=1.5, arrival_delay_ms=0.0)
        deadline = time.time() + 2.0
        while bus.delivered_count < 2 and time.time() < deadline:
            time.sleep(0.01)
        assert bus.delivered_count == 2, bus.delivered_count
        assert n2._last_fire_time_s > 0, "n2 should have fired"
        weight = n2._incoming_synapse_weights.get("n1")
        assert weight is not None and weight > STDP_DEFAULT_SYNAPSE_WEIGHT, weight
    finally:
        bus.stop()
    print("test_two_neuron_stdp_end_to_end_via_real_bus: PASS")


# ---------------------------------------------------------------------------
# Word-context bookkeeping (dispatch item 4/5)
# ---------------------------------------------------------------------------

def test_word_firing_callback_invoked_for_external_word_injection():
    n = LoomNeuron("n1")
    n.membrane_threshold = 0.5
    calls = []
    n.set_word_firing_callback(lambda word, neuron_id: calls.append((word, neuron_id)))
    n.receive_spike(_spike(1.0, source="_input_injection_", metadata={"word": "dog"}))
    assert calls == [("dog", "n1")], calls
    print("test_word_firing_callback_invoked_for_external_word_injection: PASS")


def test_word_firing_callback_not_invoked_without_word_metadata():
    n = LoomNeuron("n1")
    n.membrane_threshold = 0.5
    calls = []
    n.set_word_firing_callback(lambda word, neuron_id: calls.append((word, neuron_id)))
    n.receive_spike(_spike(1.0, source="_input_injection_"))  # no word in metadata
    assert calls == []
    print("test_word_firing_callback_not_invoked_without_word_metadata: PASS")


def test_word_firing_callback_not_invoked_for_propagated_synaptic_fire():
    """Word context is only recorded at direct external entry points, not
    propagated through the network -- a fire triggered by a real synaptic
    spike (not external) shouldn't call the word callback even if we
    somehow set threshold low enough to fire from it."""
    n = LoomNeuron("n1")
    n.membrane_threshold = 0.01
    calls = []
    n.set_word_firing_callback(lambda word, neuron_id: calls.append((word, neuron_id)))
    n.receive_spike(_spike(1.0, source="n2"))  # real synaptic source, no "_" prefix
    assert calls == []
    print("test_word_firing_callback_not_invoked_for_propagated_synaptic_fire: PASS")


def test_chi_atlas_written_on_fire():
    n = LoomNeuron("n1")
    n.membrane_threshold = 0.5
    before = len(n.chi_atlas.entries)
    n.receive_spike(_spike(1.0, source="_input_injection_", metadata={"word": "dog"}))
    after = len(n.chi_atlas.entries)
    assert after > before
    print("test_chi_atlas_written_on_fire: PASS")


# ---------------------------------------------------------------------------
# Phase 1 delivery plan Step 2: fire-rate circuit breaker
#
# Real incident (2026-07-08/09): one neuron fired continuously at
# ~3800/sec for an unknown duration before being caught by chance. These
# tests drive _fire() directly with controlled `now` values (real-time
# sleeps would be flaky/slow for a ~3800Hz reproduction) to exercise the
# breaker's own decision function precisely, plus one end-to-end test
# through the real receive_spike() -> _fire() call path.
# ---------------------------------------------------------------------------

class _RecordingBus:
    """Fake SpikeBus: records every inject() call, does not deliver
    anything -- isolates the breaker's propagation-skip decision from
    real spike delivery/threading."""
    _neuron_registry = {}

    def __init__(self):
        self.injected = []

    def inject(self, target_id, source_id, weight, arrival_delay_ms=0.0, metadata=None):
        self.injected.append((target_id, source_id, weight, arrival_delay_ms))


def _wire_single_target_neuron(n, target_id="n2", weight=0.7):
    import numpy as np
    n.couplings.neighbors = [target_id]
    n.couplings.J = np.array([[weight] * 16])
    bus = _RecordingBus()
    n.set_spike_bus(bus)
    return bus


def test_fire_rate_breaker_trips_on_runaway_pattern():
    """Reproduces the real incident's own numbers: drives _fire() at a
    ~3800/sec interval for exactly FIRE_BREAKER_WINDOW_N fires. The fire
    that fills the window must trip the breaker -- outgoing spike
    propagation skipped -- while membrane reset, refractory, and
    _last_fire_time_s bookkeeping still happen on that same fire."""
    n = LoomNeuron("n1")
    bus = _wire_single_target_neuron(n)
    n.membrane_rest = 0.0

    interval_s = 1.0 / 3800.0
    now = time.monotonic()
    # Fill the window to one short of full -- these all propagate normally
    # (not enough history yet for the breaker to judge a rate).
    for _ in range(FIRE_BREAKER_WINDOW_N - 1):
        now += interval_s
        n.membrane_potential = 5.0
        n._fire(now)
    injected_before_trip = len(bus.injected)
    assert n._fire_breaker_trip_count == 0
    assert injected_before_trip == FIRE_BREAKER_WINDOW_N - 1

    # This fire fills the window at ~3800Hz -- must trip.
    now += interval_s
    n.membrane_potential = 5.0  # nonzero, to prove _fire() still resets it
    n._fire(now)

    assert n._fire_breaker_trip_count == 1, n._fire_breaker_trip_count
    assert len(bus.injected) == injected_before_trip, (
        "tripped fire must not add a new outgoing spike-bus injection")
    assert n.membrane_potential == 0.0, "membrane must still reset on a tripped fire"
    assert n.refractory_until_s > now, "refractory must still be set on a tripped fire"
    assert n._last_fire_time_s == now
    print("test_fire_rate_breaker_trips_on_runaway_pattern: PASS")


def test_fire_rate_breaker_keeps_tripping_while_runaway_persists():
    """Not a one-shot latch: every fire past the window filling keeps
    tripping (and keeps skipping propagation) as long as the pathological
    rate continues."""
    n = LoomNeuron("n1")
    bus = _wire_single_target_neuron(n)
    n.membrane_rest = 0.0

    interval_s = 1.0 / 3800.0
    now = time.monotonic()
    extra = 10
    for _ in range(FIRE_BREAKER_WINDOW_N + extra):
        now += interval_s
        n.membrane_potential = 5.0
        n._fire(now)

    assert n._fire_breaker_trip_count == extra + 1, n._fire_breaker_trip_count
    # Only the fires before the window first filled ever propagated;
    # every fire from the window filling onward tripped and skipped.
    assert len(bus.injected) == FIRE_BREAKER_WINDOW_N - 1, len(bus.injected)
    print("test_fire_rate_breaker_keeps_tripping_while_runaway_persists: PASS")


def test_fire_rate_breaker_not_tripped_before_window_fills():
    """Fewer than FIRE_BREAKER_WINDOW_N fires ever -- even at a
    pathological rate -- must not trip: not enough history yet to judge
    a rate (matches _check_fire_rate_breaker's documented guard)."""
    n = LoomNeuron("n1")
    bus = _wire_single_target_neuron(n)
    n.membrane_rest = 0.0

    interval_s = 1.0 / 3800.0
    now = time.monotonic()
    for _ in range(FIRE_BREAKER_WINDOW_N - 1):
        now += interval_s
        n.membrane_potential = 5.0
        n._fire(now)

    assert n._fire_breaker_trip_count == 0
    assert len(bus.injected) == FIRE_BREAKER_WINDOW_N - 1
    print("test_fire_rate_breaker_not_tripped_before_window_fills: PASS")


def test_fire_rate_breaker_never_trips_at_realistic_stdp_rate():
    """A neuron firing at a realistic, generously-below-ceiling sustained
    rate (20 Hz -- well under the ~50Hz realistic-need bound reasoned
    from tau_m_ms=20.0, and >10x under FIRE_BREAKER_CEILING_HZ) must
    never trip, even run for several multiples of the window size."""
    n = LoomNeuron("n1")
    bus = _wire_single_target_neuron(n)
    n.membrane_rest = 0.0

    interval_s = 1.0 / 20.0
    now = time.monotonic()
    total_fires = FIRE_BREAKER_WINDOW_N * 3
    for _ in range(total_fires):
        now += interval_s
        n.membrane_potential = 5.0
        n._fire(now)

    assert n._fire_breaker_trip_count == 0, n._fire_breaker_trip_count
    assert len(bus.injected) == total_fires
    print("test_fire_rate_breaker_never_trips_at_realistic_stdp_rate: PASS")


def test_fire_rate_breaker_end_to_end_via_receive_spike():
    """Exercises the real production call path (receive_spike -> _fire),
    not just direct _fire() calls -- confirms the wiring. A tight
    in-process Python loop calling receive_spike back-to-back easily
    exceeds FIRE_BREAKER_CEILING_HZ (250 Hz = one fire per 4ms) in real
    wall-clock time on any real machine, so this reliably trips."""
    n = LoomNeuron("n1")
    bus = _wire_single_target_neuron(n)
    n.membrane_threshold = 1.0
    n.membrane_rest = 0.0
    n.refractory_period_ms = 0.0  # let receive_spike's refractory check pass every call

    for _ in range(FIRE_BREAKER_WINDOW_N + 5):
        n.receive_spike(_spike(1.5, source="_input_injection_"))

    assert n._fire_breaker_trip_count > 0, (
        "a tight in-process loop firing back-to-back should easily "
        "exceed FIRE_BREAKER_CEILING_HZ and trip the breaker"
    )
    print("test_fire_rate_breaker_end_to_end_via_receive_spike: PASS")


def test_fire_rate_breaker_bounded_memory():
    """_recent_fire_timestamps never grows past FIRE_BREAKER_WINDOW_N no
    matter how many times the neuron fires -- the memory-bounded
    requirement."""
    n = LoomNeuron("n1")
    _wire_single_target_neuron(n)
    n.membrane_rest = 0.0

    now = time.monotonic()
    for i in range(FIRE_BREAKER_WINDOW_N * 5):
        now += 0.05  # 20Hz, realistic, non-tripping
        n.membrane_potential = 5.0
        n._fire(now)
        assert len(n._recent_fire_timestamps) <= FIRE_BREAKER_WINDOW_N
    assert len(n._recent_fire_timestamps) == FIRE_BREAKER_WINDOW_N
    print("test_fire_rate_breaker_bounded_memory: PASS")


if __name__ == "__main__":
    test_receive_spike_adds_weight_to_membrane()
    test_receive_spike_fires_at_threshold()
    test_refractory_absorbs_without_firing()
    test_membrane_decays_toward_rest_between_spikes()
    test_get_outgoing_synapses_reduces_j_vector_to_scalar()
    test_propagation_delay_defaults_without_chi_position()
    test_propagation_delay_scales_with_chi_distance_when_positions_set()
    test_fire_emits_to_spike_bus_when_set()
    test_fire_without_spike_bus_does_not_crash()
    test_step_unchanged_by_additions()
    test_synaptic_spike_scaled_by_default_weight()
    test_external_spike_bypasses_stdp_scaling()
    test_potentiation_strengthens_synapse_on_fire_shortly_after_presynaptic_spike()
    test_potentiation_clamped_to_max()
    test_presynaptic_history_pruned_outside_window()
    test_depression_weakens_synapse_when_we_fire_before_source()
    test_depression_clamped_to_min()
    test_notify_downstream_skips_self_loop_no_deadlock()
    test_two_neuron_stdp_end_to_end_via_real_bus()
    test_word_firing_callback_invoked_for_external_word_injection()
    test_word_firing_callback_not_invoked_without_word_metadata()
    test_word_firing_callback_not_invoked_for_propagated_synaptic_fire()
    test_chi_atlas_written_on_fire()
    test_fire_rate_breaker_trips_on_runaway_pattern()
    test_fire_rate_breaker_keeps_tripping_while_runaway_persists()
    test_fire_rate_breaker_not_tripped_before_window_fills()
    test_fire_rate_breaker_never_trips_at_realistic_stdp_rate()
    test_fire_rate_breaker_end_to_end_via_receive_spike()
    test_fire_rate_breaker_bounded_memory()
    print("ALL PASS: test_neuron_spike_handling")
