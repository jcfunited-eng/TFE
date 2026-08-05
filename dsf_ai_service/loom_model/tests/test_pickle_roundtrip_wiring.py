"""Pickle and spike-bus wiring proofs for LoomNeuron, LoomBrain, and Guala.

The former typed-word injection test is intentionally absent. Production
correctly retires word-derived synthetic sensory fields; only physically
custodied sensory activity may enter the sensory spike path.
"""

import os
import pickle
import sys
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

os.environ.setdefault("SUBSTRATE_MODE", "embedded")


def _fresh_guala(event_driven=True):
    from dsf_ai_service.v4.gualaloom_v5_engine import Guala

    os.environ["EVENT_DRIVEN_SUBSTRATE"] = "1" if event_driven else "0"
    return Guala()


def test_neuron_getstate_excludes_lock_and_runtime_refs():
    from dsf_ai_service.loom_model.neuron import LoomNeuron

    neuron = LoomNeuron("probe_n1")
    neuron.set_spike_bus(object())
    assert neuron._neuron_lock is not None
    assert neuron._spike_bus is not None
    assert "_word_firing_callback" not in neuron.__dict__

    blob = pickle.dumps(neuron)
    restored = pickle.loads(blob)

    assert isinstance(restored._neuron_lock, type(threading.Lock()))
    assert restored._neuron_lock is not neuron._neuron_lock
    assert restored._spike_bus is None
    assert "_word_firing_callback" not in restored.__dict__


def test_neuron_setstate_backfills_missing_fields():
    from dsf_ai_service.loom_model.neuron import LoomNeuron

    neuron = LoomNeuron("probe_n2")
    state = neuron.__getstate__()
    for field in (
        "membrane_potential",
        "membrane_rest",
        "membrane_threshold",
        "tau_m_ms",
        "refractory_period_ms",
        "last_update_time_s",
        "refractory_until_s",
        "chi_position",
        "_recent_presynaptic_fires",
        "_incoming_synapse_weights",
        "_last_fire_time_s",
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
    assert isinstance(restored._recent_presynaptic_fires, dict)
    assert restored._incoming_synapse_weights == {}
    assert restored._last_fire_time_s == 0.0
    assert restored._last_fire_time_s is not None
    assert isinstance(restored._neuron_lock, type(threading.Lock()))


def test_brain_getstate_excludes_runtime_refs():
    from dsf_ai_service.loom_model.brain import LoomBrain

    brain = LoomBrain(brain_seed=42, seed_size=8)
    brain.set_spike_bus(object())
    brain._guala_ref = object()

    blob = pickle.dumps(brain)
    restored = pickle.loads(blob)

    assert (
        not hasattr(restored, "_spike_bus")
        or restored.__dict__.get("_spike_bus") is None
    )
    assert (
        not hasattr(restored, "_guala_ref")
        or restored.__dict__.get("_guala_ref") is None
    )


def test_brain_setstate_no_stale_refs():
    from dsf_ai_service.loom_model.brain import LoomBrain

    brain = LoomBrain(brain_seed=42, seed_size=8)
    state = brain.__getstate__()
    restored = LoomBrain.__new__(LoomBrain)
    restored.__setstate__(state)

    assert "_spike_bus" not in restored.__dict__ or restored._spike_bus is None
    assert "_guala_ref" not in restored.__dict__ or restored._guala_ref is None


def test_wire_spike_bus_idempotent():
    guala = _fresh_guala()
    try:
        before_registry_size = len(guala._spike_bus._neuron_registry)
        guala.wire_spike_bus()
        guala.wire_spike_bus()
        after_registry_size = len(guala._spike_bus._neuron_registry)
        assert before_registry_size == after_registry_size
        assert guala._spike_bus is guala.organism.brain._spike_bus
        assert guala.organism.brain._guala_ref is guala
        neuron = guala._all_neurons()[0]
        assert neuron._spike_bus is guala._spike_bus
    finally:
        guala.shutdown()


def test_wire_spike_bus_noop_when_bus_absent():
    guala = _fresh_guala(event_driven=False)
    try:
        assert guala._spike_bus is None
        guala.wire_spike_bus()
        assert guala._spike_bus is None
    finally:
        guala.shutdown()


def test_worker_loop_delivers_physical_sensory_item_to_neurons():
    """The worker advances neurons from a numeric sensory waveform."""

    os.environ["SENSORY_SPIKE_INJECTION_ENABLED"] = "1"
    try:
        guala = _fresh_guala()
        try:
            hemisphere_id = guala.organism.brain.hemispheres[0].hemi_id
            neuron = (
                guala.organism.brain.hemispheres[0].cluster.neurons[0]
            )
            guala._enqueue_organism_sensory(
                hemisphere_id,
                [0.1, 0.2, 0.3, 0.4],
                tick=1,
                input_chi=5,
            )
            deadline = time.monotonic() + 3.0
            while (
                time.monotonic() < deadline
                and neuron._tick != 1
            ):
                time.sleep(0.05)
            assert neuron._tick == 1, (
                "worker loop did not deliver a physical sensory item "
                "within 3s"
            )
            assert neuron._last_dsf is not None
        finally:
            guala.shutdown()
    finally:
        os.environ.pop("SENSORY_SPIKE_INJECTION_ENABLED", None)
