"""
GL-CMD-MOOD-BROADCAST-C1-20260712-v1: unit tests for the global mood/
affect broadcast channel -- LoomNeuron.set_mood_source() /
_read_mood_modulation() / receive_spike()'s mood-scaled contribution, and
LoomBrain.wire_mood_broadcast().

Real-world grounding under test: a global neuromodulator broadcast
(arousal/valence) reaches the whole substrate at once and changes how
readily neurons respond, rather than each neuron computing its own local
mood independently. The real, already-computed global affect state is
gualaloom_v5_engine.py's Needs class (self.needs on the live Guala
engine, arousal()/valence() methods, unchanged) -- these tests import and
construct that REAL class directly (not a mock) to prove genuine
compatibility, plus a couple of synthetic adversarial sources to prove
the defensive bound-clamping holds even for inputs the real class could
never produce.

Five requirements this file (plus a manual git-diff check reported
alongside it) verifies:
  (a) zero behavior change with the kill switch off
  (b) neuron behavior real-measurably shifts with different real
      mood-state inputs, in a controlled A/B/C
  (c) the modulation is bounded -- both the raw multiplier and its
      effect on an existing bounded quantity (synapse weight)
  (d) this mechanism never calls anything on the mood source except its
      own zero-argument arousal()/valence() reads -- no write path back
      into the engine exists (static source-audit here; the
      complementary `git diff` check on gualaloom_v5_engine.py itself is
      reported separately, since this repo's shared working tree has
      unrelated concurrent WIP in that file this session did not author)
  (e) the existing cascade regression test is re-run separately (not
      duplicated here) -- see test_lateral_inhibition_cascade.py
"""

import inspect
import math
import os
import re
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from dsf_ai_service.loom_model.neuron import (
    LoomNeuron, MAX_SYNAPSE_WEIGHT, MIN_SYNAPSE_WEIGHT,
    MOOD_MODULATION_MAX_FRACTION, MOOD_BROADCAST_ENABLED_ENV,
    STDP_DEFAULT_SYNAPSE_WEIGHT,
)
from dsf_ai_service.substrate.spike_bus import PendingSpike
from dsf_ai_service.v4.gualaloom_v5_engine import Needs


def _spike(weight, source="_src", target="n1", metadata=None):
    return PendingSpike(arrival_time=time.monotonic(), target_neuron_id=target,
                         source_neuron_id=source, weight=weight, metadata=metadata or {})


def _real_needs(stability, novelty, connection):
    """A REAL Needs instance (gualaloom_v5_engine.py, unmodified) with its
    three raw dials set directly -- arousal()/valence() are then genuine
    Needs arithmetic, not fabricated numbers."""
    n = Needs()
    n.stability = stability
    n.novelty = novelty
    n.connection = connection
    return n


def _clear_switch():
    os.environ.pop(MOOD_BROADCAST_ENABLED_ENV, None)


# ---------------------------------------------------------------------------
# (a) zero behavior change with the kill switch off
# ---------------------------------------------------------------------------

def test_switch_off_by_default_env_absent():
    _clear_switch()
    n = LoomNeuron("n1")
    # Extreme real mood, wired -- should still be inert with the switch unset.
    n.set_mood_source(_real_needs(1.0, 1.0, 1.0))
    assert n._read_mood_modulation() == 1.0
    print("test_switch_off_by_default_env_absent: PASS")


def test_switch_explicit_zero_is_also_off():
    os.environ[MOOD_BROADCAST_ENABLED_ENV] = "0"
    try:
        n = LoomNeuron("n1")
        n.set_mood_source(_real_needs(0.0, 0.0, 0.0))
        assert n._read_mood_modulation() == 1.0
    finally:
        _clear_switch()
    print("test_switch_explicit_zero_is_also_off: PASS")


def test_off_switch_produces_byte_identical_receive_spike_outcome():
    """Two neurons, identical setup; one wired to an extreme real mood
    source, one with no mood source at all. Switch OFF (unset). Feed both
    an identical real spike sequence (external + internal/STDP). Their
    resulting membrane_potential, fire state, and learned synapse weight
    must be EXACTLY identical -- not just close -- proving the addition
    is a true no-op with the switch off, not merely a small effect.

    Time is frozen (time.monotonic patched to a constant) for the
    duration of this comparison -- receive_spike()'s EXISTING, unrelated
    leaky membrane decay is itself a function of real wall-clock time
    (dt_ms since last_update_time_s), so two neurons stepped sequentially
    at genuinely different wall-clock instants would legitimately diverge
    by float noise from that pre-existing mechanism alone, independent of
    mood. Freezing time isolates exactly the one thing this test claims
    to measure: mood's own contribution to the arithmetic."""
    _clear_switch()

    def _make():
        n = LoomNeuron("n1")
        n.membrane_threshold = 50.0  # never actually fires; isolates contribution math
        return n

    baseline = _make()
    moody = _make()
    moody.set_mood_source(_real_needs(1.0, 1.0, 1.0))  # extreme real mood, ignored (switch off)

    import unittest.mock
    with unittest.mock.patch("dsf_ai_service.loom_model.neuron.time.monotonic", return_value=1000.0):
        for spike in [
            _spike(0.7, source="_input_injection_"),
            _spike(0.9, source="n2"),
            _spike(0.4, source="n3"),
            _spike(1.3, source="_input_injection_"),
        ]:
            baseline.receive_spike(spike)
            moody.receive_spike(spike)

    assert baseline.membrane_potential == moody.membrane_potential, (
        baseline.membrane_potential, moody.membrane_potential)
    assert baseline._incoming_synapse_weights == moody._incoming_synapse_weights
    assert baseline._last_fire_time_s == moody._last_fire_time_s == 0.0
    print("test_off_switch_produces_byte_identical_receive_spike_outcome: PASS "
          f"(membrane_potential={baseline.membrane_potential})")


# ---------------------------------------------------------------------------
# (b) real, measurable shift with different real mood-state inputs
# ---------------------------------------------------------------------------

def test_gain_is_neutral_at_real_needs_target():
    """A real Needs instance sitting exactly on its own TARGETS (no
    disequilibrium at all -- arousal()==0, valence()==0) must produce a
    gain_mult of EXACTLY 1.0, even with the switch ON. This is not an
    off-switch test -- it's confirming the broadcast itself is a true
    no-op at genuine homeostatic neutrality, not a hidden constant bias."""
    os.environ[MOOD_BROADCAST_ENABLED_ENV] = "1"
    try:
        from dsf_ai_service.v4.gualaloom_v5_engine import NEEDS_TARGET_V7
        needs = _real_needs(NEEDS_TARGET_V7, NEEDS_TARGET_V7, NEEDS_TARGET_V7)
        assert abs(needs.arousal() - 0.0) < 1e-9
        assert abs(needs.valence() - 0.0) < 1e-9
        n = LoomNeuron("n1")
        n.set_mood_source(needs)
        assert abs(n._read_mood_modulation() - 1.0) < 1e-9
    finally:
        _clear_switch()
    print("test_gain_is_neutral_at_real_needs_target: PASS")


def test_gain_shifts_measurably_and_in_the_reasoned_direction_across_real_moods():
    """Four REAL Needs states produce four DISTINCT, correctly-ordered
    gain_mult values, matching the documented real-world grounding:

      neutral (needs exactly at target) < mild real distress
        < severe real distress < needs genuinely well-exceeded

    This is not "good > neutral > bad" -- it is the real, honest shape of
    THIS substrate's own Needs arithmetic (see _read_mood_modulation's
    docstring): arousal (any real disequilibrium, good or bad) always
    pushes gain up a little, same real-world grounding as LC-NE arousal
    rising for salient events of either valence; valence's sign then
    further separates genuinely good real states from genuinely bad
    ones. Zero disequilibrium (exactly on target) is the one real state
    that is a true no-op even with the switch on."""
    os.environ[MOOD_BROADCAST_ENABLED_ENV] = "1"
    try:
        neutral = _real_needs(0.7, 0.7, 0.7)         # arousal=0.00, valence=+0.00 (real target)
        mild_distress = _real_needs(0.6, 0.6, 0.6)   # arousal=0.30, valence=-0.10
        severe_distress = _real_needs(0.0, 0.0, 0.0)  # arousal=1.00, valence=-0.70
        thriving = _real_needs(1.0, 1.0, 1.0)         # arousal=0.90, valence=+0.30

        neurons = {
            "neutral": neutral, "mild_distress": mild_distress,
            "severe_distress": severe_distress, "thriving": thriving,
        }
        gains = {}
        for label, needs in neurons.items():
            n = LoomNeuron(label)
            n.set_mood_source(needs)
            gains[label] = n._read_mood_modulation()

        print(f"  {gains}")
        assert (gains["neutral"] < gains["mild_distress"] < gains["severe_distress"]
                < gains["thriving"]), gains
        assert abs(gains["neutral"] - 1.0) < 1e-9
        # Real, not infinitesimal: each step covers a measurable fraction of the bound.
        ordered = [gains["neutral"], gains["mild_distress"], gains["severe_distress"], gains["thriving"]]
        for lo, hi in zip(ordered, ordered[1:]):
            assert (hi - lo) > MOOD_MODULATION_MAX_FRACTION * 0.05, (lo, hi)

        # End-to-end through receive_spike(): the SAME real spike sequence
        # produces a strictly ordered resulting membrane_potential across
        # the four real mood states (sub-threshold throughout, isolating
        # the contribution-scaling effect from any firing/reset noise).
        potentials = {}
        for label, needs in neurons.items():
            n = LoomNeuron(label)
            n.set_mood_source(needs)
            n.membrane_threshold = 100.0
            n.receive_spike(_spike(1.0, source="_input_injection_"))
            potentials[label] = n.membrane_potential
        print(f"  {potentials}")
        assert (potentials["neutral"] < potentials["mild_distress"] < potentials["severe_distress"]
                < potentials["thriving"]), potentials
    finally:
        _clear_switch()
    print("test_gain_shifts_measurably_and_in_the_reasoned_direction_across_real_moods: PASS")


def test_stdp_path_also_shifts_with_real_mood():
    """Same real-mood A/B, but through the non-external (STDP-scaled)
    branch of receive_spike -- confirms the broadcast reaches the learned
    synapse-weight path too, not just the raw external-injection path."""
    os.environ[MOOD_BROADCAST_ENABLED_ENV] = "1"
    try:
        good = _real_needs(1.0, 1.0, 1.0)
        low = _real_needs(0.6, 0.6, 0.6)
        n_good, n_low = LoomNeuron("g"), LoomNeuron("l")
        n_good.set_mood_source(good)
        n_low.set_mood_source(low)
        for n in (n_good, n_low):
            n.membrane_threshold = 100.0
            n.receive_spike(_spike(1.0, source="n2"))  # real (non-external) synaptic source
        assert n_good.membrane_potential > n_low.membrane_potential, (
            n_good.membrane_potential, n_low.membrane_potential)
        # Both still scaled off the same STDP_DEFAULT_SYNAPSE_WEIGHT baseline.
        assert n_good.membrane_potential > STDP_DEFAULT_SYNAPSE_WEIGHT * 0.9
    finally:
        _clear_switch()
    print("test_stdp_path_also_shifts_with_real_mood: PASS")


# ---------------------------------------------------------------------------
# (c) bounded: raw multiplier, AND its effect on an existing bounded quantity
# ---------------------------------------------------------------------------

class _AdversarialMood:
    """Synthetic mood source -- values a real Needs instance could never
    produce -- used only to prove the defensive clamp holds regardless of
    what's wired in, not just for well-behaved real inputs."""
    def __init__(self, arousal_val, valence_val):
        self._a = arousal_val
        self._v = valence_val
    def arousal(self):
        return self._a
    def valence(self):
        return self._v


class _RaisingMood:
    def arousal(self):
        raise RuntimeError("simulated stale/partially-restored mood source")
    def valence(self):
        return 0.0


def test_gain_multiplier_never_exceeds_bound_for_extreme_real_needs():
    os.environ[MOOD_BROADCAST_ENABLED_ENV] = "1"
    try:
        extreme_high = _real_needs(1.0, 1.0, 1.0)
        extreme_low = _real_needs(0.0, 0.0, 0.0)
        for needs in (extreme_high, extreme_low):
            n = LoomNeuron("n1")
            n.set_mood_source(needs)
            g = n._read_mood_modulation()
            assert (1.0 - MOOD_MODULATION_MAX_FRACTION) - 1e-9 <= g <= (
                1.0 + MOOD_MODULATION_MAX_FRACTION) + 1e-9, g
    finally:
        _clear_switch()
    print("test_gain_multiplier_never_exceeds_bound_for_extreme_real_needs: PASS")


def test_gain_multiplier_clamped_for_adversarial_out_of_range_source():
    os.environ[MOOD_BROADCAST_ENABLED_ENV] = "1"
    try:
        for arousal_val, valence_val in [(1e9, 1e9), (-1e9, -1e9), (1e9, -1e9)]:
            n = LoomNeuron("n1")
            n.set_mood_source(_AdversarialMood(arousal_val, valence_val))
            g = n._read_mood_modulation()
            assert (1.0 - MOOD_MODULATION_MAX_FRACTION) - 1e-9 <= g <= (
                1.0 + MOOD_MODULATION_MAX_FRACTION) + 1e-9, (arousal_val, valence_val, g)
    finally:
        _clear_switch()
    print("test_gain_multiplier_clamped_for_adversarial_out_of_range_source: PASS")


def test_nan_inf_and_raising_source_degrade_to_pure_noop():
    os.environ[MOOD_BROADCAST_ENABLED_ENV] = "1"
    try:
        for arousal_val, valence_val in [(float("nan"), 0.0), (float("inf"), 0.0), (0.5, float("nan"))]:
            n = LoomNeuron("n1")
            n.set_mood_source(_AdversarialMood(arousal_val, valence_val))
            assert n._read_mood_modulation() == 1.0, (arousal_val, valence_val)

        n2 = LoomNeuron("n2")
        n2.set_mood_source(_RaisingMood())
        assert n2._read_mood_modulation() == 1.0
        # And receive_spike() itself must not raise or misbehave either.
        n2.membrane_threshold = 100.0
        n2.receive_spike(_spike(1.0, source="_input_injection_"))
        assert abs(n2.membrane_potential - 1.0) < 1e-9
    finally:
        _clear_switch()
    print("test_nan_inf_and_raising_source_degrade_to_pure_noop: PASS")


def test_effective_synapse_weight_clamped_to_existing_min_max_range():
    """The concrete, task-required check: even when a synapse weight is
    already AT MAX_SYNAPSE_WEIGHT and mood gain would push it up (or
    already at MIN_SYNAPSE_WEIGHT and gain would -- trivially -- push it
    further down), the mood-modulated effective weight actually used in
    receive_spike() never leaves [MIN_SYNAPSE_WEIGHT, MAX_SYNAPSE_WEIGHT]
    -- the SAME bound _apply_stdp_potentiation/_apply_subthreshold_
    potentiation/_receive_upstream_fire_notification already enforce for
    every other writer of this value."""
    os.environ[MOOD_BROADCAST_ENABLED_ENV] = "1"
    try:
        # Maximum possible gain_mult: real Needs cannot reach it, so use
        # the adversarial source to hit the FULL +MOOD_MODULATION_MAX_FRACTION
        # ceiling deterministically.
        n = LoomNeuron("n1")
        n.set_mood_source(_AdversarialMood(1.0, 1.0))  # arousal=1(centered=+1), valence=+1
        gain = n._read_mood_modulation()
        assert abs(gain - (1.0 + MOOD_MODULATION_MAX_FRACTION)) < 1e-9, gain

        n._incoming_synapse_weights["n2"] = MAX_SYNAPSE_WEIGHT  # already saturated
        n.membrane_threshold = 1000.0  # never fires -- isolates the weight math
        n.receive_spike(_spike(1.0, source="n2"))
        # Without the clamp this would be MAX_SYNAPSE_WEIGHT * gain > MAX_SYNAPSE_WEIGHT.
        assert n.membrane_potential <= MAX_SYNAPSE_WEIGHT + 1e-9, n.membrane_potential
        assert abs(n.membrane_potential - MAX_SYNAPSE_WEIGHT) < 1e-9, (
            f"expected exact clamp to MAX_SYNAPSE_WEIGHT={MAX_SYNAPSE_WEIGHT}, "
            f"got {n.membrane_potential}")
    finally:
        _clear_switch()
    print("test_effective_synapse_weight_clamped_to_existing_min_max_range: PASS")


def test_effective_synapse_weight_never_goes_negative_at_min():
    """Global minimum of the gain formula: arousal clamps to 0.0 (it is
    used directly, never negative -- see _read_mood_modulation's
    docstring) and valence clamps to -1.0, so the lowest gain_mult this
    formula can ever produce, for ANY input, is
    1 - MOOD_MODULATION_MAX_FRACTION*0.5 = 0.95 -- inside, not at, the
    outer [1-MOOD_MODULATION_MAX_FRACTION, ...] safety clamp (the clamp
    is still real defense-in-depth for the upper bound, which the
    formula's own arithmetic DOES reach exactly -- see the adversarial
    bound test above). Confirms that minimum, and that it still can never
    push an already-MIN_SYNAPSE_WEIGHT synapse below MIN_SYNAPSE_WEIGHT
    (trivially true here since gain_mult > 0 always, but checked
    explicitly rather than assumed)."""
    os.environ[MOOD_BROADCAST_ENABLED_ENV] = "1"
    try:
        n = LoomNeuron("n1")
        n.set_mood_source(_AdversarialMood(-1e9, -1e9))  # clamps to arousal=0.0, valence=-1.0
        gain = n._read_mood_modulation()
        expected_floor = 1.0 - MOOD_MODULATION_MAX_FRACTION * 0.5
        assert abs(gain - expected_floor) < 1e-9, gain
        assert gain >= (1.0 - MOOD_MODULATION_MAX_FRACTION) - 1e-9, gain

        n._incoming_synapse_weights["n2"] = MIN_SYNAPSE_WEIGHT
        n.membrane_threshold = 1000.0
        n.receive_spike(_spike(1.0, source="n2"))
        assert n.membrane_potential >= MIN_SYNAPSE_WEIGHT - 1e-9
        assert abs(n.membrane_potential - MIN_SYNAPSE_WEIGHT) < 1e-9
    finally:
        _clear_switch()
    print("test_effective_synapse_weight_never_goes_negative_at_min: PASS")


# ---------------------------------------------------------------------------
# (d) one-way broadcast: static audit -- the only calls this mechanism ever
# makes on a mood source are the two documented zero-arg reads.
# ---------------------------------------------------------------------------

def test_mood_source_is_never_written_to_static_audit():
    """Scans this mechanism's own source (neuron.py's LoomNeuron class +
    brain.py's wire_mood_broadcast) for any attribute WRITE or method call
    on a mood/needs reference other than the two documented reads,
    .arousal() and .valence(). A regression guard: if a future edit ever
    adds e.g. `self._mood_source.stability = ...` or
    `mood_source.tick_drift()`, this test fails."""
    import dsf_ai_service.loom_model.neuron as neuron_mod
    import dsf_ai_service.loom_model.brain as brain_mod

    # Scoped to exactly the four methods that ever touch a mood reference
    # (not the whole ~1900-line neuron.py / LoomNeuron class, which has
    # unrelated local variables that could false-positive a whole-class
    # regex scan). This is where the local variable names actually used
    # for the mood reference in this real code are drawn from.
    read_modulation_src = inspect.getsource(neuron_mod.LoomNeuron._read_mood_modulation)
    set_mood_source_src = inspect.getsource(neuron_mod.LoomNeuron.set_mood_source)
    receive_spike_src = inspect.getsource(neuron_mod.LoomNeuron.receive_spike)
    wire_broadcast_src = inspect.getsource(brain_mod.LoomBrain.wire_mood_broadcast)

    # _read_mood_modulation is the ONLY method that ever calls anything on
    # the wired mood object -- via its local alias `source = self._mood_source`.
    # Every call made on that local alias must be one of the two documented
    # zero-argument reads.
    calls = re.findall(r"\bsource\.([A-Za-z_][A-Za-z0-9_]*)\(\)", read_modulation_src)
    assert calls, "expected to find at least the arousal()/valence() calls"
    assert set(calls) <= {"arousal", "valence"}, (
        f"found an unexpected method call on the mood source: {set(calls) - {'arousal', 'valence'}}")
    # No attribute assignment on that alias anywhere in this method.
    assert not re.search(r"\bsource\.[A-Za-z_][A-Za-z0-9_]*\s*=", read_modulation_src), (
        "found a write to an attribute on the mood source -- one-way broadcast violated")

    # set_mood_source/wire_mood_broadcast only ever ASSIGN the reference
    # itself (self._mood_source = mood_source / neuron.set_mood_source(...));
    # they must never call or write an attribute ON the mood object.
    for label, snippet in [("set_mood_source", set_mood_source_src),
                            ("wire_mood_broadcast", wire_broadcast_src)]:
        assert not re.search(r"mood_source\.[A-Za-z_]", snippet), (
            f"{label} touches an attribute/method on mood_source -- expected only "
            f"a bare reference assignment/pass-through")

    # receive_spike() never touches the mood source reference directly at
    # all -- it only ever uses the already-computed float mood_gain_mult
    # returned by _read_mood_modulation(). (Docstring prose mentioning
    # set_mood_source by name, or "a mood source is wired", is fine --
    # only an actual `self._mood_source` attribute access would matter.)
    assert "self._mood_source" not in receive_spike_src
    print("test_mood_source_is_never_written_to_static_audit: PASS")


def test_wire_mood_broadcast_reaches_every_neuron():
    """LoomBrain.wire_mood_broadcast() (the ready-to-flip bulk wiring
    helper, not auto-invoked in this dispatch) actually reaches every
    neuron in the brain, and only ever WRITES the reference (never reads
    anything off it at wiring time)."""
    from dsf_ai_service.loom_model.brain import LoomBrain
    b = LoomBrain(brain_seed=7)
    sentinel = _real_needs(0.5, 0.5, 0.5)
    b.wire_mood_broadcast(sentinel)
    all_neurons = [nrn for hemi in b.hemispheres for nrn in hemi.cluster.neurons]
    assert len(all_neurons) > 0
    assert all(nrn._mood_source is sentinel for nrn in all_neurons)
    # Idempotent / clearable.
    b.wire_mood_broadcast(None)
    assert all(nrn._mood_source is None for nrn in all_neurons)
    print(f"test_wire_mood_broadcast_reaches_every_neuron: PASS ({len(all_neurons)} neurons)")


if __name__ == "__main__":
    test_switch_off_by_default_env_absent()
    test_switch_explicit_zero_is_also_off()
    test_off_switch_produces_byte_identical_receive_spike_outcome()
    test_gain_is_neutral_at_real_needs_target()
    test_gain_shifts_measurably_and_in_the_reasoned_direction_across_real_moods()
    test_stdp_path_also_shifts_with_real_mood()
    test_gain_multiplier_never_exceeds_bound_for_extreme_real_needs()
    test_gain_multiplier_clamped_for_adversarial_out_of_range_source()
    test_nan_inf_and_raising_source_degrade_to_pure_noop()
    test_effective_synapse_weight_clamped_to_existing_min_max_range()
    test_effective_synapse_weight_never_goes_negative_at_min()
    test_mood_source_is_never_written_to_static_audit()
    test_wire_mood_broadcast_reaches_every_neuron()
    print("ALL PASS: test_mood_broadcast")
