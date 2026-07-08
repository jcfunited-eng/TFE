"""
GL-CMD-PHASE-1-V2-REVIVE-EVE-20260708-v3: local unit tests for the
pickle __getstate__/__setstate__ pair on LoomNeuron and LoomBrain, the
idempotent Guala.wire_spike_bus() helper, and injection at the actual
production convergence point (the organism worker loop).

The load-bearing test against the real, downloaded production pickle
lives separately (see the dispatch's own harness protocol step 3) --
this file covers the individually-testable units.
"""

import os
import sys
import pickle
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

os.environ.setdefault("SUBSTRATE_MODE", "embedded")


def _fresh_guala(event_driven=True):
    from dsf_ai_service.v4.gualaloom_v5_engine import Guala
    os.environ["EVENT_DRIVEN_SUBSTRATE"] = "1" if event_driven else "0"
    return Guala()


# ---------------------------------------------------------------------
# LoomNeuron __getstate__/__setstate__
# ---------------------------------------------------------------------

def test_neuron_getstate_excludes_lock_and_runtime_refs():
    from dsf_ai_service.loom_model.neuron import LoomNeuron
    n = LoomNeuron("probe_n1")
    n.set_spike_bus(object())  # anything non-None; must not survive pickling
    n.set_word_firing_callback(lambda w, i: None)
    assert n._neuron_lock is not None
    assert n._spike_bus is not None
    assert n._word_firing_callback is not None

    blob = pickle.dumps(n)  # must not raise -- this is the bug the dispatch fixes
    restored = pickle.loads(blob)

    assert isinstance(restored._neuron_lock, type(threading.Lock()))
    assert restored._neuron_lock is not n._neuron_lock  # a NEW lock, not shared
    assert restored._spike_bus is None
    assert restored._word_firing_callback is None
    print("test_neuron_getstate_excludes_lock_and_runtime_refs: PASS")


def test_neuron_setstate_backfills_missing_fields():
    from dsf_ai_service.loom_model.neuron import LoomNeuron
    n = LoomNeuron("probe_n2")
    state = n.__getstate__()
    # Simulate a pre-Phase-1-v2 pickle: strip every Phase 1 v2 field.
    for field in (
        "membrane_potential", "membrane_rest", "membrane_threshold",
        "tau_m_ms", "refractory_period_ms", "last_update_time_s",
        "refractory_until_s", "chi_position", "_recent_presynaptic_fires",
        "_incoming_synapse_weights", "_last_fire_time_s",
    ):
        state.pop(field, None)

    restored = LoomNeuron.__new__(LoomNeuron)
    restored.__setstate__(state)

    assert restored.membrane_potential == 0.0
    assert restored.membrane_rest == 0.0
    assert restored.membrane_threshold == 1.0
    assert restored.tau_m_ms == 20.0
    assert restored.refractory_period_ms == 2.0
    assert restored.last_update_time_s == 0.0
    assert restored.refractory_until_s == 0.0
    assert restored.chi_position is None
    assert restored._recent_presynaptic_fires == {}
    assert isinstance(restored._recent_presynaptic_fires, dict)  # not [] -- see v1 halt report
    assert restored._incoming_synapse_weights == {}
    assert restored._last_fire_time_s == 0.0
    assert restored._last_fire_time_s is not None  # not None -- see v1 halt report
    assert isinstance(restored._neuron_lock, type(threading.Lock()))
    print("test_neuron_setstate_backfills_missing_fields: PASS")


# ---------------------------------------------------------------------
# LoomBrain __getstate__/__setstate__
# ---------------------------------------------------------------------

def test_brain_getstate_excludes_runtime_refs():
    from dsf_ai_service.loom_model.brain import LoomBrain
    b = LoomBrain(brain_seed=42, seed_size=8)
    b.set_spike_bus(object())
    b._guala_ref = object()

    blob = pickle.dumps(b)  # must not raise
    restored = pickle.loads(blob)

    assert not hasattr(restored, '_spike_bus') or restored.__dict__.get('_spike_bus') is None
    assert not hasattr(restored, '_guala_ref') or restored.__dict__.get('_guala_ref') is None
    print("test_brain_getstate_excludes_runtime_refs: PASS")


def test_brain_setstate_no_stale_refs():
    from dsf_ai_service.loom_model.brain import LoomBrain
    b = LoomBrain(brain_seed=42, seed_size=8)
    state = b.__getstate__()
    restored = LoomBrain.__new__(LoomBrain)
    restored.__setstate__(state)
    # __setstate__ deliberately leaves these absent -- wire_spike_bus() sets them.
    assert '_spike_bus' not in restored.__dict__ or restored._spike_bus is None
    assert '_guala_ref' not in restored.__dict__ or restored._guala_ref is None
    print("test_brain_setstate_no_stale_refs: PASS")


# ---------------------------------------------------------------------
# Guala.wire_spike_bus()
# ---------------------------------------------------------------------

def test_wire_spike_bus_idempotent():
    g = _fresh_guala()
    try:
        before_registry_size = len(g._spike_bus._neuron_registry)
        g.wire_spike_bus()
        g.wire_spike_bus()
        after_registry_size = len(g._spike_bus._neuron_registry)
        assert before_registry_size == after_registry_size
        assert g._spike_bus is g.organism.brain._spike_bus
        assert g.organism.brain._guala_ref is g
        n = g._all_neurons()[0]
        assert n._spike_bus is g._spike_bus
        print("test_wire_spike_bus_idempotent: PASS")
    finally:
        g.shutdown()


def test_wire_spike_bus_noop_when_bus_absent():
    g = _fresh_guala(event_driven=False)
    try:
        assert g._spike_bus is None
        g.wire_spike_bus()  # must not raise
        assert g._spike_bus is None
        print("test_wire_spike_bus_noop_when_bus_absent: PASS")
    finally:
        g.shutdown()


# ---------------------------------------------------------------------
# Injection at the real production convergence point (worker loop)
# ---------------------------------------------------------------------

def test_worker_loop_injects_on_word_item():
    g = _fresh_guala()
    try:
        before = g._spike_bus.injected_count
        g._enqueue_organism_remember("probeword")
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline and g._spike_bus.injected_count == before:
            time.sleep(0.05)
        assert g._spike_bus.injected_count > before, (
            "worker loop did not inject any spikes for a word item within 3s")
        print("test_worker_loop_injects_on_word_item: PASS")
    finally:
        g.shutdown()


def test_worker_loop_injects_on_sensory_item():
    g = _fresh_guala()
    try:
        before = g._spike_bus.injected_count
        hemi_id = g.organism.brain.hemispheres[0].hemi_id
        g._enqueue_organism_sensory(hemi_id, [0.1, 0.2, 0.3, 0.4], tick=1, input_chi=5)
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline and g._spike_bus.injected_count == before:
            time.sleep(0.05)
        assert g._spike_bus.injected_count > before, (
            "worker loop did not inject any spikes for a sensory item within 3s")
        print("test_worker_loop_injects_on_sensory_item: PASS")
    finally:
        g.shutdown()


if __name__ == "__main__":
    test_neuron_getstate_excludes_lock_and_runtime_refs()
    test_neuron_setstate_backfills_missing_fields()
    test_brain_getstate_excludes_runtime_refs()
    test_brain_setstate_no_stale_refs()
    test_wire_spike_bus_idempotent()
    test_wire_spike_bus_noop_when_bus_absent()
    test_worker_loop_injects_on_word_item()
    test_worker_loop_injects_on_sensory_item()
    print("ALL PASS: test_pickle_roundtrip_wiring")
