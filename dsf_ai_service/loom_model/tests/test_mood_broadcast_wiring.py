"""
GL-CMD-MOOD-BROADCAST-WIRE-C1-20260712: tests for the actual call site of
LoomBrain.wire_mood_broadcast() -- Guala.wire_spike_bus()
(gualaloom_v5_engine.py), the only place it is invoked in production, at
both construction (__init__, line ~2586) and post-restore
(load_full_state() -> wire_spike_bus(), line ~12078).

Context: c73bfd0 shipped LoomNeuron.set_mood_source()/
_read_mood_modulation() and LoomBrain.wire_mood_broadcast() kill-switch
OFF, well-tested in isolation (test_mood_broadcast.py) -- but
wire_mood_broadcast() had no caller anywhere outside its own test file /
docstring, confirmed by
GL-RPT-INERT-FEATURES-GRADUATION-PLAN-CODEX-20260712-v1: flipping
MOOD_BROADCAST_ENABLED in production was a byte-identical no-op, because
no real neuron's _mood_source was ever set to anything but None. This
file tests the fix: one line added at the end of
Guala.wire_spike_bus() -- `self.organism.brain.wire_mood_broadcast(self.needs)`
-- gated behind the SAME early-return as the rest of that method (with no
spike bus, receive_spike() -- the only place _mood_source is ever read --
is never called by anything, so wiring mood independently of the bus
would itself be a real no-op dressed as a live connection).

Four things verified here, matching the fix's required checks:
  (a) the wiring call actually happens at real construction, not just
      "callable" -- no manual wire_mood_broadcast()/set_mood_source()
      call anywhere in this file
  (b) switch OFF + real wiring connected == zero behavior change,
      byte-identical to the pre-fix (unwired) state
  (c) switch ON + real wiring => a real neuron's behavior genuinely,
      measurably shifts with real Needs state changes, driven through
      the actual wired path end-to-end (real SpikeBus delivery), never
      a manual set_mood_source() call
  (d) a real save/restore cycle re-establishes the wiring onto the NEW
      post-restore neuron objects, pointed at the same real Needs
      instance throughout (self.needs is never rebound by restore)

test_lateral_inhibition_cascade.py and test_mood_broadcast.py are the
two required pre-existing suites re-run separately alongside this file.
"""

import os
import sys
import shutil
import tempfile
import time
import unittest.mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

os.environ.setdefault("SUBSTRATE_MODE", "embedded")

from dsf_ai_service.loom_model.neuron import EXTERNAL_SOURCE_PREFIX, MOOD_BROADCAST_ENABLED_ENV
from dsf_ai_service.substrate.spike_bus import PendingSpike


def _fresh_guala():
    from dsf_ai_service.v4.gualaloom_v5_engine import Guala
    os.environ["EVENT_DRIVEN_SUBSTRATE"] = "1"
    return Guala()


def _clear_switch():
    os.environ.pop(MOOD_BROADCAST_ENABLED_ENV, None)


def _spike(weight, source="_src", target="n1"):
    return PendingSpike(arrival_time=time.monotonic(), target_neuron_id=target,
                         source_neuron_id=source, weight=weight, metadata={})


# ---------------------------------------------------------------------
# (a) wiring call actually happens at real construction
# ---------------------------------------------------------------------

def test_construction_wires_every_real_neuron_to_real_needs():
    """No manual wire_mood_broadcast()/set_mood_source() call anywhere in
    this test -- Guala.__init__'s own wire_spike_bus() call must already
    have done it, onto the real live Needs instance (self.needs), for
    every real neuron in the organism."""
    _clear_switch()
    g = _fresh_guala()
    try:
        neurons = g._all_neurons()
        assert len(neurons) >= 32, "expected the real multi-hemisphere organism"
        assert g.needs is not None
        unwired = [n.neuron_id for n in neurons if n._mood_source is not g.needs]
        assert not unwired, f"{len(unwired)}/{len(neurons)} real neurons not wired to g.needs"
        print(f"test_construction_wires_every_real_neuron_to_real_needs: PASS ({len(neurons)} neurons)")
    finally:
        g.shutdown()


def test_wire_spike_bus_wires_mood_broadcast_noop_when_bus_absent():
    """Mirrors test_pickle_roundtrip_wiring.py's
    test_wire_spike_bus_noop_when_bus_absent -- with EVENT_DRIVEN_SUBSTRATE=0
    (no spike bus ever constructed), wire_spike_bus() must still hit its
    early return and do nothing, on this mechanism just as much as the
    pre-existing spike-bus wiring: no real neuron's _mood_source should
    be touched (still None, __init__'s own default)."""
    _clear_switch()
    os.environ["EVENT_DRIVEN_SUBSTRATE"] = "0"
    try:
        from dsf_ai_service.v4.gualaloom_v5_engine import Guala
        g = Guala()
        try:
            assert g._spike_bus is None
            neurons = g._all_neurons()
            assert len(neurons) >= 32
            assert all(n._mood_source is None for n in neurons)
            g.wire_spike_bus()  # must not raise, must remain a no-op
            assert all(n._mood_source is None for n in neurons)
            print("test_wire_spike_bus_wires_mood_broadcast_noop_when_bus_absent: PASS")
        finally:
            g.shutdown()
    finally:
        os.environ["EVENT_DRIVEN_SUBSTRATE"] = "1"


# ---------------------------------------------------------------------
# (a) + (d): wiring survives a real save/restore cycle, re-pointed at the
# NEW post-restore neuron objects, same real Needs instance throughout
# ---------------------------------------------------------------------

def test_restore_rewires_new_neurons_to_same_needs_instance():
    _clear_switch()
    g1 = _fresh_guala()
    tmpdir = tempfile.mkdtemp()
    try:
        g1.save_full_state(state_dir=tmpdir)

        g2 = _fresh_guala()
        try:
            g2._guala_identity = g1._guala_identity
            pre_restore_neuron_ids = {id(n) for n in g2._all_neurons()}
            needs_ref = g2.needs  # self.needs is constructed once in __init__,
                                   # never rebound thereafter (_apply_needs
                                   # mutates fields in place) -- verify that
                                   # real contract holds across restore too.

            g2.load_full_state(state_dir=tmpdir)

            post_restore_neurons = g2._all_neurons()
            assert len(post_restore_neurons) >= 32
            post_restore_neuron_ids = {id(n) for n in post_restore_neurons}
            # Restore genuinely replaced the neuron objects -- otherwise
            # this test would trivially pass without exercising the real
            # restore path at all.
            assert pre_restore_neuron_ids.isdisjoint(post_restore_neuron_ids), (
                "organism restore did not actually replace neuron objects -- "
                "this test isn't exercising what it claims to")

            assert g2.needs is needs_ref, (
                "self.needs was rebound by restore -- wiring the OLD "
                "reference would silently orphan it")
            unwired = [n.neuron_id for n in post_restore_neurons if n._mood_source is not g2.needs]
            assert not unwired, (
                f"{len(unwired)}/{len(post_restore_neurons)} post-restore neurons not "
                "wired to the real live Needs object -- wire_spike_bus()'s "
                "post-restore call did not re-establish mood-broadcast wiring")
            print("test_restore_rewires_new_neurons_to_same_needs_instance: PASS "
                  f"({len(post_restore_neurons)} post-restore neurons, "
                  f"{len(pre_restore_neuron_ids)} pre-restore neurons discarded)")
        finally:
            g2.shutdown()
    finally:
        g1.shutdown()
        shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------
# (b) switch OFF + real wiring connected == zero behavior change
# ---------------------------------------------------------------------

def test_switch_off_with_real_wiring_connected_is_byte_identical_to_unwired():
    """A real Guala()-constructed neuron -- proven wired to g.needs by
    construction alone, no manual set_mood_source() call in this test --
    fed an identical real spike sequence with the switch OFF, compared
    against the exact same neuron's transient state reset and rerun with
    its _mood_source reference temporarily nulled (this mechanism's
    pre-fix "wiring never happened" condition). g.needs is first pushed
    to its most extreme, most provocative real state, so this isn't a
    trivially-near-neutral comparison."""
    _clear_switch()
    g = _fresh_guala()
    try:
        n = g._all_neurons()[0]
        assert n._mood_source is g.needs, "neuron not wired by real construction"
        g.needs.stability = 0.0
        g.needs.novelty = 0.0
        g.needs.connection = 0.0  # most extreme real distress this class can produce

        n.membrane_threshold = 1e6  # never fires -- isolates the contribution arithmetic
        spikes = [
            _spike(0.7, source=f"{EXTERNAL_SOURCE_PREFIX}a", target=n.neuron_id),
            _spike(0.9, source="some_other_real_neuron_id", target=n.neuron_id),
            _spike(0.4, source="another_real_neuron_id", target=n.neuron_id),
            _spike(1.3, source=f"{EXTERNAL_SOURCE_PREFIX}b", target=n.neuron_id),
        ]

        def _run(mood_source):
            n.membrane_potential = n.membrane_rest
            n.last_update_time_s = 1000.0
            n._incoming_synapse_weights = {}
            n._recent_presynaptic_fires = {}
            n._last_fire_time_s = 0.0
            n._mood_source = mood_source
            with unittest.mock.patch("dsf_ai_service.loom_model.neuron.time.monotonic", return_value=1000.0):
                for sp in spikes:
                    n.receive_spike(sp)
            return n.membrane_potential, dict(n._incoming_synapse_weights)

        wired_result = _run(g.needs)  # real wiring, exactly as construction left it
        unwired_result = _run(None)   # this mechanism's pre-fix (never-wired) state

        n._mood_source = g.needs  # restore real wiring before returning the neuron to g

        assert wired_result == unwired_result, (wired_result, unwired_result)
        print("test_switch_off_with_real_wiring_connected_is_byte_identical_to_unwired: "
              f"PASS {wired_result}")
    finally:
        g.shutdown()
        _clear_switch()


# ---------------------------------------------------------------------
# (c) switch ON => real, measurable, end-to-end response through the
# actual wired path (real SpikeBus delivery, never a synthetic bypass)
# ---------------------------------------------------------------------

def test_switch_on_real_neuron_responds_through_actual_wired_path_via_spike_bus():
    """Drives the REAL SpikeBus (g._spike_bus.inject() -> background
    delivery thread -> neuron.receive_spike()), on a neuron whose
    _mood_source was set purely by Guala() construction's own
    wire_spike_bus() call -- set_mood_source()/wire_mood_broadcast() are
    never called directly anywhere in this test."""
    g = _fresh_guala()
    try:
        os.environ[MOOD_BROADCAST_ENABLED_ENV] = "1"
        n = g._all_neurons()[0]
        assert n._mood_source is g.needs, "neuron not wired by real construction"
        bus = g._spike_bus
        assert bus is not None, "organism must be wired to a real SpikeBus"

        n.membrane_threshold = 1e6  # never fires -- isolates the contribution measurement

        def _inject_and_wait(label):
            n.membrane_potential = n.membrane_rest
            before = bus.delivered_count
            bus.inject(target_id=n.neuron_id, source_id=f"{EXTERNAL_SOURCE_PREFIX}moodtest_{label}",
                       weight=1.0, arrival_delay_ms=0.0)
            deadline = time.monotonic() + 3.0
            while time.monotonic() < deadline and bus.delivered_count == before:
                time.sleep(0.02)
            assert bus.delivered_count > before, "spike bus never delivered the test spike"
            return n.membrane_potential

        from dsf_ai_service.v4.gualaloom_v5_engine import NEEDS_TARGET_V7
        g.needs.stability = NEEDS_TARGET_V7
        g.needs.novelty = NEEDS_TARGET_V7
        g.needs.connection = NEEDS_TARGET_V7
        assert abs(g.needs.arousal() - 0.0) < 1e-9  # real target: zero disequilibrium
        neutral_potential = _inject_and_wait("neutral")

        g.needs.stability = 0.0
        g.needs.novelty = 0.0
        g.needs.connection = 0.0
        assert g.needs.arousal() > 0.5  # real, severe disequilibrium
        distress_potential = _inject_and_wait("distress")

        # At the real target, gain_mult is exactly 1.0 (no hidden constant
        # bias) -- see test_mood_broadcast.py's own
        # test_gain_is_neutral_at_real_needs_target for the isolated check;
        # this confirms the same fact end-to-end through the real bus.
        assert abs(neutral_potential - 1.0) < 1e-9, neutral_potential
        assert distress_potential > neutral_potential, (distress_potential, neutral_potential)
        print("test_switch_on_real_neuron_responds_through_actual_wired_path_via_spike_bus: "
              f"PASS (neutral={neutral_potential}, distress={distress_potential})")
    finally:
        _clear_switch()
        g.shutdown()


if __name__ == "__main__":
    test_construction_wires_every_real_neuron_to_real_needs()
    test_wire_spike_bus_wires_mood_broadcast_noop_when_bus_absent()
    test_restore_rewires_new_neurons_to_same_needs_instance()
    test_switch_off_with_real_wiring_connected_is_byte_identical_to_unwired()
    test_switch_on_real_neuron_responds_through_actual_wired_path_via_spike_bus()
    print("ALL PASS: test_mood_broadcast_wiring")
