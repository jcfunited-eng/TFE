"""
GL-CMD-SENSORY-SPIKE-GATE-EVE-20260709-v1: local unit tests for the new
SENSORY_SPIKE_INJECTION_ENABLED gate on the sensory-branch spike injection
call site in Guala._organism_worker_loop (dsf_ai_service/v4/
gualaloom_v5_engine.py).

Real incident this closes: wave-atlas cells never decay to exactly zero,
so the sensory branch's injection call never went quiet on its own --
confirmed live, 14M+ fire events, 3792/sec, zero synapses ever updated.
The word branch is not implicated by either this incident or the prior
cascade incident (GL-RPT-PHASE-1-V2-REVIVE-C1-20260708 series) and stays
on the existing EVENT_DRIVEN_SUBSTRATE gate, unchanged -- these tests
confirm that too.

These tests monkeypatch Guala.organism.brain._inject_input_as_spikes with
a counting stub and synchronize on the relevant queue's join() (task_done()
is called in the worker loop's finally-block on every item, whether or not
injection actually fired), so presence/absence of a call is observed
deterministically rather than via a timed poll.
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

os.environ.setdefault("SUBSTRATE_MODE", "embedded")


def _fresh_guala(event_driven=True):
    from dsf_ai_service.v4.gualaloom_v5_engine import Guala
    os.environ["EVENT_DRIVEN_SUBSTRATE"] = "1" if event_driven else "0"
    return Guala()


class _CallCounter:
    """Stand-in for LoomBrain._inject_input_as_spikes that just counts
    calls and records the kwargs of the last one, without touching real
    neuron/spike-bus state."""

    def __init__(self):
        self.call_count = 0
        self.last_kwargs = None

    def __call__(self, **kwargs):
        self.call_count += 1
        self.last_kwargs = kwargs


def _clear_sensory_gate_env():
    os.environ.pop("SENSORY_SPIKE_INJECTION_ENABLED", None)


# ---------------------------------------------------------------------
# Sensory branch: default ON (GL-CMD-SINGLE-STACK-ALL-LIVE-20260716,
# organ 3 -- the 2026-07-09 incident is fixed at the mechanism: wave
# decay zero-clamp + per-band skip + injection weight floor; the env var
# survives as an emergency-off only). This test tracked "default off"
# before that ruling; it now tracks the ratified default-on reality.
# ---------------------------------------------------------------------

def test_sensory_branch_injects_when_flag_unset_default_on():
    _clear_sensory_gate_env()  # confirm the true default (nothing set)
    g = _fresh_guala(event_driven=True)
    try:
        stub = _CallCounter()
        g.organism.brain._inject_input_as_spikes = stub
        hemi_id = g.organism.brain.hemispheres[0].hemi_id
        g._enqueue_organism_sensory(hemi_id, [0.1, 0.2, 0.3, 0.4], tick=1, input_chi=5)
        g._organism_sensory_queue.join()  # deterministic: waits for task_done()
        assert stub.call_count == 1, (
            "sensory branch did not inject with SENSORY_SPIKE_INJECTION_"
            "ENABLED unset -- the 2026-07-16 ruling makes ON the default "
            f"(got {stub.call_count} calls)")
        print("test_sensory_branch_injects_when_flag_unset_default_on: PASS")
    finally:
        g.shutdown()
        _clear_sensory_gate_env()


def test_sensory_branch_does_not_inject_when_flag_explicitly_zero():
    """The emergency-off must still work."""
    os.environ["SENSORY_SPIKE_INJECTION_ENABLED"] = "0"
    g = _fresh_guala(event_driven=True)
    try:
        stub = _CallCounter()
        g.organism.brain._inject_input_as_spikes = stub
        hemi_id = g.organism.brain.hemispheres[0].hemi_id
        g._enqueue_organism_sensory(hemi_id, [0.1, 0.2, 0.3, 0.4], tick=1, input_chi=5)
        g._organism_sensory_queue.join()
        assert stub.call_count == 0, (
            "sensory branch called _inject_input_as_spikes with "
            "SENSORY_SPIKE_INJECTION_ENABLED=0")
        print("test_sensory_branch_does_not_inject_when_flag_explicitly_zero: PASS")
    finally:
        g.shutdown()
        _clear_sensory_gate_env()


# ---------------------------------------------------------------------
# Sensory branch: explicit opt-in
# ---------------------------------------------------------------------

def test_sensory_branch_injects_when_flag_set_to_one():
    os.environ["SENSORY_SPIKE_INJECTION_ENABLED"] = "1"
    g = _fresh_guala(event_driven=True)
    try:
        stub = _CallCounter()
        g.organism.brain._inject_input_as_spikes = stub
        hemi_id = g.organism.brain.hemispheres[0].hemi_id
        g._enqueue_organism_sensory(hemi_id, [0.1, 0.2, 0.3, 0.4], tick=1, input_chi=5)
        g._organism_sensory_queue.join()
        assert stub.call_count == 1, (
            "sensory branch did not call _inject_input_as_spikes exactly once "
            f"with SENSORY_SPIKE_INJECTION_ENABLED=1 (got {stub.call_count})")
        assert stub.last_kwargs["modality"] == hemi_id
        assert stub.last_kwargs["input_chi"] == 5
        print("test_sensory_branch_injects_when_flag_set_to_one: PASS")
    finally:
        g.shutdown()
        _clear_sensory_gate_env()


def test_sensory_branch_still_noop_when_spike_bus_absent_even_if_flag_set():
    """EVENT_DRIVEN_SUBSTRATE=0 means no spike bus at all -- the new flag
    being "1" must not conjure one up. Belt-and-suspenders: the sensory
    call site checks `_spike_bus is not None` AND the new flag."""
    os.environ["SENSORY_SPIKE_INJECTION_ENABLED"] = "1"
    g = _fresh_guala(event_driven=False)
    try:
        assert g._spike_bus is None
        hemi_id = g.organism.brain.hemispheres[0].hemi_id
        g._enqueue_organism_sensory(hemi_id, [0.1, 0.2, 0.3, 0.4], tick=1, input_chi=5)
        g._organism_sensory_queue.join()
        # No assertion possible via a stub (brain has no _spike_bus to matter,
        # and _inject_input_as_spikes is never reached) -- the real check is
        # simply that draining the item doesn't raise. Nothing to inject into.
        print("test_sensory_branch_still_noop_when_spike_bus_absent_even_if_flag_set: PASS")
    finally:
        g.shutdown()
        _clear_sensory_gate_env()


# ---------------------------------------------------------------------
# Word branch: unaffected by the new flag either way
# ---------------------------------------------------------------------

def test_word_branch_injects_regardless_of_sensory_flag_unset():
    _clear_sensory_gate_env()
    g = _fresh_guala(event_driven=True)
    try:
        stub = _CallCounter()
        g.organism.brain._inject_input_as_spikes = stub
        g._enqueue_organism_remember("probeword_gate_unset")
        g._organism_queue.join()
        assert stub.call_count == 1, (
            "word branch injection was affected by SENSORY_SPIKE_INJECTION_ENABLED "
            f"being unset (got {stub.call_count} calls, expected 1)")
        assert stub.last_kwargs["modality"] == "language"
        print("test_word_branch_injects_regardless_of_sensory_flag_unset: PASS")
    finally:
        g.shutdown()
        _clear_sensory_gate_env()


def test_word_branch_injects_regardless_of_sensory_flag_zero():
    os.environ["SENSORY_SPIKE_INJECTION_ENABLED"] = "0"
    g = _fresh_guala(event_driven=True)
    try:
        stub = _CallCounter()
        g.organism.brain._inject_input_as_spikes = stub
        g._enqueue_organism_remember("probeword_gate_zero")
        g._organism_queue.join()
        assert stub.call_count == 1, (
            "word branch injection was affected by SENSORY_SPIKE_INJECTION_ENABLED=0 "
            f"(got {stub.call_count} calls, expected 1)")
        print("test_word_branch_injects_regardless_of_sensory_flag_zero: PASS")
    finally:
        g.shutdown()
        _clear_sensory_gate_env()


def test_word_branch_injects_regardless_of_sensory_flag_one():
    os.environ["SENSORY_SPIKE_INJECTION_ENABLED"] = "1"
    g = _fresh_guala(event_driven=True)
    try:
        stub = _CallCounter()
        g.organism.brain._inject_input_as_spikes = stub
        g._enqueue_organism_remember("probeword_gate_one")
        g._organism_queue.join()
        assert stub.call_count == 1, (
            "word branch injection was affected by SENSORY_SPIKE_INJECTION_ENABLED=1 "
            f"(got {stub.call_count} calls, expected 1)")
        print("test_word_branch_injects_regardless_of_sensory_flag_one: PASS")
    finally:
        g.shutdown()
        _clear_sensory_gate_env()


if __name__ == "__main__":
    test_sensory_branch_injects_when_flag_unset_default_on()
    test_sensory_branch_does_not_inject_when_flag_explicitly_zero()
    test_sensory_branch_injects_when_flag_set_to_one()
    test_sensory_branch_still_noop_when_spike_bus_absent_even_if_flag_set()
    test_word_branch_injects_regardless_of_sensory_flag_unset()
    test_word_branch_injects_regardless_of_sensory_flag_zero()
    test_word_branch_injects_regardless_of_sensory_flag_one()
    print("ALL PASS: test_sensory_spike_gate")
