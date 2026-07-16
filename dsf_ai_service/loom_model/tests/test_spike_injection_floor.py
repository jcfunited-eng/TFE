"""
GL-CMD-SINGLE-STACK-ALL-LIVE-20260716 (organ 3): mechanism tests for the
sensory-spike-injection fix that lets SENSORY_SPIKE_INJECTION_ENABLED
default ON.

The 2026-07-09 incident: wave-atlas cells never decayed to exactly zero
(multiplicative decay is asymptotic), so the sensory injection branch
never went quiet -- one entry neuron per hemisphere kicked continuously
(14M+ fires, 3792/sec, zero synapses updated).  The fix is at the
mechanism, proven here at each of its three layers:

  1. WaveAtlas.tick_decay zero-clamps sub-epsilon strengths/aggregates to
     EXACTLY 0.0 (source of the dust).
  2. push_wave_summary_to_organism skips silent bands PER-BAND -- a quiet
     hemisphere gets no work item at all.
  3. LoomBrain._inject_input_as_spikes enforces
     SPIKE_INJECTION_MIN_WEIGHT: silence and float dust inject NOTHING; a
     real signal (and every word, at WORD_INJECTION_WEIGHT=1.5) injects
     normally.
"""

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

os.environ.setdefault("SUBSTRATE_MODE", "embedded")


# ---------------------------------------------------------------------
# 1. Zero-clamp in the wave-atlas decay
# ---------------------------------------------------------------------

def test_tick_decay_zero_clamps_to_exact_zero():
    from dsf_ai_service.v4.wave_atlas import WaveAtlas
    wa = WaveAtlas()
    wa.record("sight", 1, 100, tick=1, salience=10.0)  # strength 0.5
    # prune_threshold=0.0 disables pruning entirely, so only the clamp can
    # ever produce a true zero -- the pure asymptote test.
    for _ in range(40):
        wa.tick_decay(decay_rate=0.5, prune_threshold=0.0)
    for cell in wa.cells.values():
        for b in cell.bindings:
            assert b.get("strength") == 0.0, (
                f"binding strength {b.get('strength')!r} is float dust, "
                "not EXACTLY 0.0 -- the zero-clamp is not working")
        assert cell.aggregate_strength == 0.0, (
            f"aggregate_strength {cell.aggregate_strength!r} is float "
            "dust, not EXACTLY 0.0")
    print("test_tick_decay_zero_clamps_to_exact_zero: PASS")


def test_tick_decay_default_prune_leaves_exact_zero_aggregate():
    from dsf_ai_service.v4.wave_atlas import WaveAtlas
    from dsf_ai_service.substrate.wave_summary import sample_wave_summary
    wa = WaveAtlas()
    wa.record("sight", 1, 100, tick=1, salience=10.0)
    pruned_total = 0
    for _ in range(300):
        pruned_total += wa.tick_decay()  # defaults: 0.02 decay, 0.05 prune
        if all(not c.bindings for c in wa.cells.values()):
            break
    assert pruned_total >= 1, "decay never pruned the decayed binding"
    for cell in wa.cells.values():
        assert cell.bindings == [], "a fully decayed cell still holds bindings"
        assert cell.aggregate_strength == 0.0, (
            f"decayed cell aggregate is {cell.aggregate_strength!r}, "
            "not EXACTLY 0.0")
    # And the summary the injection path consumes reads exactly quiet.
    summary = sample_wave_summary(wa)
    for band, (aggregate, top) in summary.items():
        assert aggregate == 0.0 and top == [], (
            f"band {band!r} still reads {aggregate!r} from a fully "
            "decayed atlas")
    print("test_tick_decay_default_prune_leaves_exact_zero_aggregate: PASS")


def test_tick_decay_real_strength_survives():
    """The clamp must never eat a genuinely strong binding."""
    from dsf_ai_service.v4.wave_atlas import WaveAtlas
    wa = WaveAtlas()
    wa.record("sight", 1, 100, tick=1, salience=10.0)  # strength 0.5
    wa.tick_decay()  # one default tick: 0.5 * 0.98 = 0.49
    strengths = [b["strength"] for c in wa.cells.values() for b in c.bindings]
    assert strengths and all(s > 0.4 for s in strengths), (
        f"real strength was destroyed by one decay tick: {strengths}")
    print("test_tick_decay_real_strength_survives: PASS")


# ---------------------------------------------------------------------
# 2. Per-band skip-when-empty in the wave-summary push
# ---------------------------------------------------------------------

def _fake_guala_with_organism():
    from dsf_ai_service.loom_model.embryo import Embryo
    emb = Embryo(brain_seed=42, seed_size=8, observable="event_count")
    enqueued = []
    events = []
    guala = SimpleNamespace(
        organism=emb,
        _enqueue_organism_sensory=(
            lambda hemi_id, sig, tick, input_chi=None:
            enqueued.append((hemi_id, sig, input_chi))),
        _log_substrate_event=lambda kind, **detail: events.append(kind),
    )
    return guala, enqueued


def test_push_skips_silent_bands_per_band():
    from dsf_ai_service.substrate.wave_summary import (
        push_wave_summary_to_organism, BANDS)
    guala, enqueued = _fake_guala_with_organism()
    summary = {b: (0.0, []) for b in BANDS}
    summary["sight"] = (1.5, [(42, 1.5, None)])
    push_wave_summary_to_organism(guala, summary, tick=7)
    hemis = sorted(h for h, _s, _c in enqueued)
    # H0 is the (only) visual hemisphere -- every silent band's hemisphere
    # must get NOTHING.
    assert hemis == ["H0"], (
        f"expected only the live band's hemisphere (H0) to be enqueued, "
        f"got {hemis} -- silent bands are still producing work items")
    print("test_push_skips_silent_bands_per_band: PASS")


def test_push_all_silent_enqueues_nothing():
    from dsf_ai_service.substrate.wave_summary import (
        push_wave_summary_to_organism, BANDS)
    guala, enqueued = _fake_guala_with_organism()
    summary = {b: (0.0, []) for b in BANDS}
    push_wave_summary_to_organism(guala, summary, tick=7)
    assert enqueued == [], (
        f"a fully quiet wave field still enqueued {len(enqueued)} items")
    print("test_push_all_silent_enqueues_nothing: PASS")


# ---------------------------------------------------------------------
# 3. Injection weight floor at the spike entry point
# ---------------------------------------------------------------------

class _RecordingBus:
    def __init__(self):
        self.calls = []

    def inject(self, **kwargs):
        self.calls.append(kwargs)


def _wired_brain():
    from dsf_ai_service.loom_model.embryo import Embryo
    emb = Embryo(brain_seed=42, seed_size=8, observable="event_count")
    brain = emb.brain
    bus = _RecordingBus()
    brain._spike_bus = bus
    entry = brain.hemispheres[0].cluster.neurons[0]
    brain._guala_ref = SimpleNamespace(
        _select_entry_neurons=lambda chi, modality=None: [entry])
    return brain, bus


def test_silent_and_dust_signals_inject_nothing():
    brain, bus = _wired_brain()
    brain._inject_input_as_spikes([0.0, 0.0, 0.0], 5, "H1")
    brain._inject_input_as_spikes([1e-7, 1e-7], 5, "H1")   # decay-clamp dust
    brain._inject_input_as_spikes([], 5, "H1")             # empty signal
    assert bus.calls == [], (
        f"silence injected {len(bus.calls)} spike(s) -- the "
        "SPIKE_INJECTION_MIN_WEIGHT floor is not holding")
    assert getattr(brain, '_injection_floor_skips', 0) >= 2, (
        "floor skips were not counted (observability regression)")
    print("test_silent_and_dust_signals_inject_nothing: PASS")


def test_real_signal_and_word_inject_normally():
    from dsf_ai_service.loom_model.injection_weight import (
        SPIKE_INJECTION_MIN_WEIGHT)
    brain, bus = _wired_brain()
    brain._inject_input_as_spikes([0.5, 0.6, 0.7], 5, "H1")
    assert len(bus.calls) == 1, (
        f"a real numeric signal injected {len(bus.calls)} spikes, expected 1")
    assert bus.calls[0]["weight"] >= SPIKE_INJECTION_MIN_WEIGHT
    brain._inject_input_as_spikes("hello", 5, "language")
    assert len(bus.calls) == 2, "a real word did not inject"
    assert bus.calls[1]["weight"] == 1.5  # WORD_INJECTION_WEIGHT untouched
    print("test_real_signal_and_word_inject_normally: PASS")


if __name__ == "__main__":
    test_tick_decay_zero_clamps_to_exact_zero()
    test_tick_decay_default_prune_leaves_exact_zero_aggregate()
    test_tick_decay_real_strength_survives()
    test_push_skips_silent_bands_per_band()
    test_push_all_silent_enqueues_nothing()
    test_silent_and_dust_signals_inject_nothing()
    test_real_signal_and_word_inject_normally()
    print("ALL PASS: test_spike_injection_floor")
