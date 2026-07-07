"""
GL-CMD-BLUEPRINT-PHASE-1-NEURON-AUTONOMY-EVE-20260707-v1: unit tests for
the additive LoomNeuron spike-handling methods (receive_spike, _fire,
_compute_propagation_delay_ms, _get_outgoing_synapses). Isolated -- these
methods are not called from step() or any existing path, so this test
file is the only current exerciser.
"""

import os
import sys
import time
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from dsf_ai_service.loom_model.neuron import LoomNeuron, DEFAULT_DELAY_MS
from dsf_ai_service.substrate.spike_bus import PendingSpike


def _spike(weight, source="src", target="n1", metadata=None):
    return PendingSpike(arrival_time=time.monotonic(), target_neuron_id=target,
                         source_neuron_id=source, weight=weight, metadata=metadata or {})


def test_receive_spike_adds_weight_to_membrane():
    n = LoomNeuron("n1")
    n.membrane_threshold = 10.0  # high enough not to fire
    n.receive_spike(_spike(0.3))
    assert abs(n.membrane_potential - 0.3) < 1e-9
    n.receive_spike(_spike(0.2))
    # some decay happened between calls (dt>0), but weight still added on top
    assert n.membrane_potential > 0.2
    print("test_receive_spike_adds_weight_to_membrane: PASS")


def test_receive_spike_fires_at_threshold():
    n = LoomNeuron("n1")
    n.membrane_threshold = 1.0
    n.membrane_rest = 0.0
    n.receive_spike(_spike(1.5))
    assert n.membrane_potential == 0.0, "fired neuron should reset to rest"
    assert n.refractory_until_s > time.monotonic()
    print("test_receive_spike_fires_at_threshold: PASS")


def test_refractory_absorbs_without_firing():
    n = LoomNeuron("n1")
    n.membrane_threshold = 1.0
    n.membrane_rest = 0.0
    n.refractory_period_ms = 200.0  # long refractory for a deterministic test
    n.receive_spike(_spike(1.5))  # fires, enters refractory
    assert n.membrane_potential == 0.0
    n.receive_spike(_spike(5.0))  # huge spike, but still refractory
    assert n.membrane_potential != 0.0, "spike should still integrate into membrane"
    assert n.membrane_potential < 5.5  # didn't re-fire (would reset to 0.0 rest)
    # confirm it did NOT reset to rest again (i.e. did not fire a second time)
    print("test_refractory_absorbs_without_firing: PASS")


def test_membrane_decays_toward_rest_between_spikes():
    n = LoomNeuron("n1")
    n.membrane_threshold = 100.0  # never fires
    n.membrane_rest = 0.0
    n.tau_m_ms = 5.0  # fast decay for a fast test
    n.receive_spike(_spike(1.0))
    v1 = n.membrane_potential
    time.sleep(0.05)  # 50ms >> tau_m_ms=5ms
    n.receive_spike(_spike(0.0))  # zero-weight spike just to trigger decay update
    v2 = n.membrane_potential
    assert v2 < v1, f"expected decay toward rest, got v1={v1} v2={v2}"
    print("test_membrane_decays_toward_rest_between_spikes: PASS")


def test_get_outgoing_synapses_reduces_j_vector_to_scalar():
    import numpy as np
    n = LoomNeuron("n1")
    n.couplings.neighbors = ["n2", "n3"]
    n.couplings.J = np.array([[0.5] * 16, [0.0] * 16])  # n2: nonzero, n3: all-zero
    synapses = n._get_outgoing_synapses()
    assert synapses == [("n2", 0.5)], synapses  # n3 filtered out (zero weight)
    print("test_get_outgoing_synapses_reduces_j_vector_to_scalar: PASS")


def test_propagation_delay_defaults_without_chi_position():
    n1 = LoomNeuron("n1")
    assert n1.chi_position is None  # Phase 1: never populated, see neuron.py note
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
    assert abs(delay - 20.0) < 1e-6, delay  # max distance -> 1 + 1*19 = 20ms
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
    n1.receive_spike(_spike(1.5))  # should fire, skip emission, not raise
    assert n1.membrane_potential == 0.0
    print("test_fire_without_spike_bus_does_not_crash: PASS")


def test_step_unchanged_by_additions():
    """Sanity: the existing step() path (krimelack/DSF/psi_lattice) is
    completely untouched by these additions -- still callable, still
    returns the same shape of result."""
    n = LoomNeuron("n1")
    result = n.step("hello", tick=1)
    assert set(result.keys()) == {"committed", "n_eff", "dsf", "spike_count",
                                   "match_score", "delta_eff"}
    print("test_step_unchanged_by_additions: PASS")


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
    print("ALL PASS: test_neuron_spike_handling")
