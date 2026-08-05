"""Deterministic gate proofs for physical sensory spike injection.

The sensory gate is enabled by default, can be explicitly disabled, and cannot
conjure a spike bus when event-driven substrate is disabled.

Typed-word branch cases are intentionally absent. Production correctly retires
word-derived synthetic sensory fields.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

os.environ.setdefault("SUBSTRATE_MODE", "embedded")


def _fresh_guala(event_driven=True):
    from dsf_ai_service.v4.gualaloom_v5_engine import Guala

    os.environ["EVENT_DRIVEN_SUBSTRATE"] = "1" if event_driven else "0"
    return Guala()


class _CallCounter:
    def __init__(self):
        self.call_count = 0
        self.last_kwargs = None

    def __call__(self, **kwargs):
        self.call_count += 1
        self.last_kwargs = kwargs


def _clear_sensory_gate_env():
    os.environ.pop("SENSORY_SPIKE_INJECTION_ENABLED", None)


def test_sensory_branch_injects_when_flag_unset_default_on():
    _clear_sensory_gate_env()
    guala = _fresh_guala(event_driven=True)
    try:
        stub = _CallCounter()
        guala.organism.brain._inject_input_as_spikes = stub
        hemisphere_id = guala.organism.brain.hemispheres[0].hemi_id
        guala._enqueue_organism_sensory(
            hemisphere_id,
            [0.1, 0.2, 0.3, 0.4],
            tick=1,
            input_chi=5,
        )
        guala._organism_sensory_queue.join()
        assert stub.call_count == 1, (
            "sensory branch did not inject with "
            "SENSORY_SPIKE_INJECTION_ENABLED unset"
        )
    finally:
        guala.shutdown()
        _clear_sensory_gate_env()


def test_sensory_branch_does_not_inject_when_flag_explicitly_zero():
    os.environ["SENSORY_SPIKE_INJECTION_ENABLED"] = "0"
    guala = _fresh_guala(event_driven=True)
    try:
        stub = _CallCounter()
        guala.organism.brain._inject_input_as_spikes = stub
        hemisphere_id = guala.organism.brain.hemispheres[0].hemi_id
        guala._enqueue_organism_sensory(
            hemisphere_id,
            [0.1, 0.2, 0.3, 0.4],
            tick=1,
            input_chi=5,
        )
        guala._organism_sensory_queue.join()
        assert stub.call_count == 0
    finally:
        guala.shutdown()
        _clear_sensory_gate_env()


def test_sensory_branch_injects_when_flag_set_to_one():
    os.environ["SENSORY_SPIKE_INJECTION_ENABLED"] = "1"
    guala = _fresh_guala(event_driven=True)
    try:
        stub = _CallCounter()
        guala.organism.brain._inject_input_as_spikes = stub
        hemisphere_id = guala.organism.brain.hemispheres[0].hemi_id
        guala._enqueue_organism_sensory(
            hemisphere_id,
            [0.1, 0.2, 0.3, 0.4],
            tick=1,
            input_chi=5,
        )
        guala._organism_sensory_queue.join()
        assert stub.call_count == 1
        assert stub.last_kwargs["modality"] == hemisphere_id
        assert stub.last_kwargs["input_chi"] == 5
    finally:
        guala.shutdown()
        _clear_sensory_gate_env()


def test_sensory_branch_still_noop_when_spike_bus_absent_even_if_flag_set():
    os.environ["SENSORY_SPIKE_INJECTION_ENABLED"] = "1"
    guala = _fresh_guala(event_driven=False)
    try:
        assert guala._spike_bus is None
        hemisphere_id = guala.organism.brain.hemispheres[0].hemi_id
        guala._enqueue_organism_sensory(
            hemisphere_id,
            [0.1, 0.2, 0.3, 0.4],
            tick=1,
            input_chi=5,
        )
        guala._organism_sensory_queue.join()
        assert guala._spike_bus is None
    finally:
        guala.shutdown()
        _clear_sensory_gate_env()
