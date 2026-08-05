"""
GL-CMD-BLUEPRINT-PHASE-1-MERGED-EVE-20260707-v2: unit tests for LoomBrain's
dual-write step() and dual-read recall_fast() dispatcher. Covers both the
"nothing wired" backward-compat path (bare LoomBrain(), matching every
existing test/probe) and the wired dual-path behavior via stub objects.
"""

import os
import sys
import time
from collections import Counter
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from dsf_ai_service.loom_model.brain import LoomBrain


def test_bare_brain_step_unaffected_no_spike_bus():
    """No spike bus wired (every existing test/probe's construction
    pattern) -- step() must behave exactly as before: legacy iteration
    only, no injection attempted, no crash."""
    brain = LoomBrain(brain_seed=42, seed_size=8)
    assert brain._spike_bus is None
    result = brain.step([0.0] * 8, tick=1, input_chi=5)
    assert set(result.keys()) == {h.hemi_id for h in brain.hemispheres}
    print("test_bare_brain_step_unaffected_no_spike_bus: PASS")


def test_step_no_injection_without_input_chi():
    """Spike bus IS wired but input_chi is None -- dual-write gate
    requires both conditions, so no injection should be attempted even
    with a bus present."""
    brain = LoomBrain(brain_seed=42, seed_size=8)
    injected = []

    class _FakeBus:
        def inject(self, **kwargs):
            injected.append(kwargs)

    brain.set_spike_bus(_FakeBus())
    brain._guala_ref = SimpleNamespace(_select_entry_neurons=lambda chi, mod: [])
    brain.step("hello", tick=1, input_chi=None)
    assert injected == []
    print("test_step_no_injection_without_input_chi: PASS")


def test_step_injects_when_bus_and_chi_present_then_runs_legacy():
    """Both conditions met: injection happens AND the legacy iteration
    still runs (dual-write, not either/or)."""
    brain = LoomBrain(brain_seed=42, seed_size=8)
    injected = []

    class _FakeBus:
        def inject(self, **kwargs):
            injected.append(kwargs)

    entry_neuron = SimpleNamespace(neuron_id="fake_entry_1")
    brain.set_spike_bus(_FakeBus())
    brain._guala_ref = SimpleNamespace(
        _select_entry_neurons=lambda chi, mod: [entry_neuron])

    legacy_ran = {"called": False}
    orig_legacy = brain._legacy_step_iteration
    def _wrapped(*a, **kw):
        legacy_ran["called"] = True
        return orig_legacy(*a, **kw)
    brain._legacy_step_iteration = _wrapped

    result = brain.step("dog", tick=7, input_chi=42, modality="language")
    assert legacy_ran["called"], "legacy iteration must still run (dual-write)"
    assert len(injected) == 1
    assert injected[0]["target_id"] == "fake_entry_1"
    assert injected[0]["source_id"] == "_input_injection_"
    assert injected[0]["metadata"]["word"] == "dog"
    assert injected[0]["metadata"]["input_chi"] == 42
    assert set(result.keys()) == {h.hemi_id for h in brain.hemispheres}
    print("test_step_injects_when_bus_and_chi_present_then_runs_legacy: PASS")


def test_injection_failure_does_not_break_legacy_path():
    """If spike injection raises, the legacy path must still run --
    dual-write is additive, never allowed to break the thing everything
    still reads from during Phase 1."""
    brain = LoomBrain(brain_seed=42, seed_size=8)

    class _ExplodingBus:
        def inject(self, **kwargs):
            raise RuntimeError("boom")

    brain.set_spike_bus(_ExplodingBus())
    brain._guala_ref = SimpleNamespace(
        _select_entry_neurons=lambda chi, mod: [SimpleNamespace(neuron_id="x")])
    result = brain.step("dog", tick=1, input_chi=1)
    assert set(result.keys()) == {h.hemi_id for h in brain.hemispheres}
    print("test_injection_failure_does_not_break_legacy_path: PASS")


def test_recall_fast_default_backend_is_legacy():
    os.environ.pop("RECALL_BACKEND", None)
    brain = LoomBrain(brain_seed=42, seed_size=8, observable="event_count")
    calls = {"legacy": 0, "stdp": 0}
    brain._recall_fast_legacy = lambda q: (calls.__setitem__("legacy", calls["legacy"] + 1) or Counter({"a": 1}))
    brain._recall_fast_stdp = lambda q: (calls.__setitem__("stdp", calls["stdp"] + 1) or Counter({"b": 1}))
    result = brain.recall_fast({"language": "dog"})
    assert calls == {"legacy": 1, "stdp": 0}
    assert result == Counter({"a": 1})
    print("test_recall_fast_default_backend_is_legacy: PASS")


def test_recall_fast_stdp_backend_calls_stdp_only():
    os.environ["RECALL_BACKEND"] = "stdp"
    try:
        brain = LoomBrain(brain_seed=42, seed_size=8, observable="event_count")
        calls = {"legacy": 0, "stdp": 0}
        brain._recall_fast_legacy = lambda q: (calls.__setitem__("legacy", calls["legacy"] + 1) or Counter())
        brain._recall_fast_stdp = lambda q: (calls.__setitem__("stdp", calls["stdp"] + 1) or Counter({"b": 1}))
        result = brain.recall_fast({"language": "dog"})
        assert calls == {"legacy": 0, "stdp": 1}
        assert result == Counter({"b": 1})
    finally:
        os.environ.pop("RECALL_BACKEND", None)
    print("test_recall_fast_stdp_backend_calls_stdp_only: PASS")


def test_recall_fast_shadow_backend_runs_both_returns_legacy():
    os.environ["RECALL_BACKEND"] = "shadow"
    try:
        brain = LoomBrain(brain_seed=42, seed_size=8, observable="event_count")
        calls = {"legacy": 0, "stdp": 0, "log": 0}
        brain._recall_fast_legacy = lambda q: (calls.__setitem__("legacy", calls["legacy"] + 1) or Counter({"a": 1}))
        brain._recall_fast_stdp = lambda q: (calls.__setitem__("stdp", calls["stdp"] + 1) or Counter({"b": 2}))
        brain._log_recall_shadow_comparison = lambda l, s, q: calls.__setitem__("log", calls["log"] + 1)
        result = brain.recall_fast({"language": "dog"})
        assert calls == {"legacy": 1, "stdp": 1, "log": 1}
        assert result == Counter({"a": 1}), "shadow mode must return the LEGACY result"
    finally:
        os.environ.pop("RECALL_BACKEND", None)
    print("test_recall_fast_shadow_backend_runs_both_returns_legacy: PASS")


def test_recall_fast_shadow_stdp_exception_still_returns_legacy():
    os.environ["RECALL_BACKEND"] = "shadow"
    try:
        brain = LoomBrain(brain_seed=42, seed_size=8, observable="event_count")
        brain._recall_fast_legacy = lambda q: Counter({"a": 1})
        def _boom(q):
            raise RuntimeError("stdp broke")
        brain._recall_fast_stdp = _boom
        result = brain.recall_fast({"language": "dog"})
        assert result == Counter({"a": 1})
    finally:
        os.environ.pop("RECALL_BACKEND", None)
    print("test_recall_fast_shadow_stdp_exception_still_returns_legacy: PASS")


def test_recall_fast_stdp_empty_without_spike_bus_or_guala():
    brain = LoomBrain(brain_seed=42, seed_size=8)
    assert brain._spike_bus is None
    assert brain._guala_ref is None
    result = brain._recall_fast_stdp({"language": "dog"})
    assert result == Counter()
    print("test_recall_fast_stdp_empty_without_spike_bus_or_guala: PASS")


def test_recall_fast_stdp_resolves_cue_and_reads_membrane():
    """Full stdp-path exercise with a stub Guala providing word_neuron_map
    + all_neurons + neuron_to_word, and a real SpikeBus."""
    from dsf_ai_service.substrate.spike_bus import SpikeBus
    from dsf_ai_service.loom_model.neuron import LoomNeuron

    n_cue = LoomNeuron("cue1")
    n_other = LoomNeuron("other1")
    n_cue.membrane_potential = 0.0
    # High enough to survive membrane decay over the ~30ms
    # RECALL_PROPAGATION_WINDOW_MS sleep (exp(-30/tau_m_ms=20) ~= 0.22)
    # and still clear RECALL_ACTIVATION_THRESHOLD=0.3.
    n_other.membrane_potential = 2.0
    n_other.last_update_time_s = time.monotonic()

    registry = {"cue1": n_cue, "other1": n_other}
    bus = SpikeBus(neuron_registry=registry)
    n_cue.set_spike_bus(bus)
    n_other.set_spike_bus(bus)
    bus.start()
    try:
        brain = LoomBrain(brain_seed=42, seed_size=8)
        brain.set_spike_bus(bus)
        guala_stub = SimpleNamespace(
            _word_neuron_map={"dog": {"cue1"}},
            _chi_to_neurons=lambda chi: [],
            _all_neurons=lambda: [n_cue, n_other],
            _neuron_to_word=lambda n: {"cue1": "dog", "other1": "bark"}.get(n.neuron_id),
        )
        brain._guala_ref = guala_stub

        votes = brain._recall_fast_stdp({"language": "dog"})
        # other1 was already above threshold before the cue even propagates
        assert votes.get("bark", 0) >= 1, votes
    finally:
        bus.stop()
    print("test_recall_fast_stdp_resolves_cue_and_reads_membrane: PASS")


def test_compute_query_chi_matches_embryo_convention():
    brain = LoomBrain(brain_seed=42, seed_size=8)
    assert brain._compute_query_chi([0.0, 0.0, 0.0]) is None  # all-zero -> None
    assert brain._compute_query_chi([]) is None
    chi = brain._compute_query_chi([0.5, 0.3, -0.2, 0.8])
    assert chi is None or (0 <= chi < 100)
    print("test_compute_query_chi_matches_embryo_convention: PASS")


if __name__ == "__main__":
    test_bare_brain_step_unaffected_no_spike_bus()
    test_step_no_injection_without_input_chi()
    test_step_injects_when_bus_and_chi_present_then_runs_legacy()
    test_injection_failure_does_not_break_legacy_path()
    test_recall_fast_default_backend_is_legacy()
    test_recall_fast_stdp_backend_calls_stdp_only()
    test_recall_fast_shadow_backend_runs_both_returns_legacy()
    test_recall_fast_shadow_stdp_exception_still_returns_legacy()
    test_recall_fast_stdp_empty_without_spike_bus_or_guala()
    test_recall_fast_stdp_resolves_cue_and_reads_membrane()
    test_compute_query_chi_matches_embryo_convention()
    print("ALL PASS: test_brain_dual_path")
