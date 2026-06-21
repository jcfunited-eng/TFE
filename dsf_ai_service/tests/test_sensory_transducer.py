"""
test_sensory_transducer.py — GL-CMD-107/108 F1+F12 SensoryTransducer tests.

Validates substrate-true sensory parameter generation:
- No fixed label-to-param mappings
- First-encounter variability
- Convergence with prior bindings
- Modality separation
- Deterministic replay within tick
"""

import sys, os
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from dsf_ai_service.substrate.sensory_transducer import (
    SensoryTransducer, NullAtlasReader, MODALITY_CHANNELS,
    TOUCH_CHANNELS, SMELL_CHANNELS, TASTE_CHANNELS,
)


class MockAtlasReader:
    """Atlas reader with injectable prior bindings for testing."""

    def __init__(self):
        self._bindings = {}  # (label, modality) → list of param dicts

    def add_binding(self, label, modality, params):
        key = (label, modality)
        if key not in self._bindings:
            self._bindings[key] = []
        self._bindings[key].append(params)

    def has_bindings(self, label, modality):
        return (label, modality) in self._bindings and len(self._bindings[(label, modality)]) > 0

    def get_binding_params(self, label, modality):
        return self._bindings.get((label, modality), [])


# ---------------------------------------------------------------------------
# T1: first-encounter variability
# ---------------------------------------------------------------------------

def test_t1_first_encounter_variability():
    """Empty atlas, transduce("touch", "warm") at different ticks → params differ."""
    transducer = SensoryTransducer(NullAtlasReader())

    params1 = transducer.transduce("touch", "warm", tick=100)
    params2 = transducer.transduce("touch", "warm", tick=101)

    # Count channels that differ
    diffs = sum(1 for ch in TOUCH_CHANNELS if abs(params1[ch] - params2[ch]) > 0.01)

    print(f"\n== T1: first-encounter variability ==")
    print(f"  tick=100: {params1}")
    print(f"  tick=101: {params2}")
    print(f"  channels differing: {diffs}/5")

    assert diffs >= 3, (
        f"Expected at least 3 of 5 channels to differ between ticks, got {diffs}"
    )


# ---------------------------------------------------------------------------
# T2: first-encounter range coverage
# ---------------------------------------------------------------------------

def test_t2_first_encounter_range_coverage():
    """100 first-encounter calls → temperature std > 0.15."""
    transducer = SensoryTransducer(NullAtlasReader())

    temperatures = []
    for tick in range(100):
        params = transducer.transduce("touch", "warm", tick=tick)
        temperatures.append(params["temperature"])

    std = float(np.std(temperatures))
    mean = float(np.mean(temperatures))

    print(f"\n== T2: first-encounter range coverage ==")
    print(f"  100 calls for 'warm' touch")
    print(f"  temperature mean={mean:.4f}, std={std:.4f}")
    print(f"  min={min(temperatures):.4f}, max={max(temperatures):.4f}")

    assert std > 0.15, (
        f"Expected temperature std > 0.15 (spans half of [0,1]), got {std:.4f}"
    )


# ---------------------------------------------------------------------------
# T3: convergence with prior bindings
# ---------------------------------------------------------------------------

def test_t3_convergence():
    """50 prior bindings centered at temperature≈0.8 → subsequent calls cluster there."""
    atlas = MockAtlasReader()

    # Seed 50 prior bindings centered at temperature=0.8, std=0.1
    rng = np.random.default_rng(42)
    for i in range(50):
        params = {ch: float(rng.normal(0.5, 0.2)) for ch in TOUCH_CHANNELS}
        params["temperature"] = float(rng.normal(0.8, 0.1))
        params = {k: max(0.0, min(1.0, v)) for k, v in params.items()}
        atlas.add_binding("warm", "touch", params)

    transducer = SensoryTransducer(atlas)

    # 50 subsequent calls
    temperatures = []
    for tick in range(50):
        params = transducer.transduce("touch", "warm", tick=1000 + tick)
        temperatures.append(params["temperature"])

    mean = float(np.mean(temperatures))
    std = float(np.std(temperatures))

    print(f"\n== T3: convergence ==")
    print(f"  50 prior bindings at temperature≈0.8")
    print(f"  50 subsequent calls: mean={mean:.4f}, std={std:.4f}")

    assert abs(mean - 0.8) < 0.1, (
        f"Expected mean temperature within 0.1 of 0.8, got {mean:.4f}"
    )


# ---------------------------------------------------------------------------
# T4: modality separation
# ---------------------------------------------------------------------------

def test_t4_modality_separation():
    """touch "warm" and smell "warm" use different param channels."""
    transducer = SensoryTransducer(NullAtlasReader())

    touch_params = transducer.transduce("touch", "warm", tick=42)
    smell_params = transducer.transduce("smell", "warm", tick=42)

    print(f"\n== T4: modality separation ==")
    print(f"  touch channels: {set(touch_params.keys())}")
    print(f"  smell channels: {set(smell_params.keys())}")

    # No key overlap between touch and smell
    touch_keys = set(touch_params.keys())
    smell_keys = set(smell_params.keys())
    overlap = touch_keys & smell_keys

    assert len(overlap) == 0, (
        f"Touch and smell should have no overlapping channel names, got {overlap}"
    )


# ---------------------------------------------------------------------------
# T5: bridge backward compat — generate_sensory_signals still produces waveforms
# ---------------------------------------------------------------------------

def test_t5_bridge_backward_compat():
    """generate_sensory_signals("touch", ["warm"]) still returns valid waveforms."""
    from dsf_ai_service.substrate.sensory_generators import (
        generate_sensory_signals, transduce_sensory_signals,
    )

    signals = generate_sensory_signals("touch", ["warm"], tick=100)

    print(f"\n== T5: bridge backward compat ==")
    print(f"  channels returned: {list(signals.keys())}")

    # Should return multi-channel waveform dict
    assert isinstance(signals, dict), f"Expected dict, got {type(signals)}"
    assert len(signals) > 0, "Expected at least one channel"

    for ch_name, waveform in signals.items():
        assert hasattr(waveform, '__len__'), f"Channel {ch_name} not array-like"
        assert len(waveform) == 200, f"Channel {ch_name} length {len(waveform)}, expected 200"
        print(f"  {ch_name}: len={len(waveform)}, mean={float(np.mean(waveform)):.4f}")

    # Transduce still works
    channel_results = transduce_sensory_signals(signals)
    assert isinstance(channel_results, dict)
    print(f"  transduced: {len(channel_results)} channels with chi values")


# ---------------------------------------------------------------------------
# T6: substrate-true sanity
# ---------------------------------------------------------------------------

def test_t6_substrate_true_sanity():
    """No label-to-param dicts, no if label == branches, no static lookup tables."""
    import inspect
    from dsf_ai_service.substrate import sensory_transducer

    source = inspect.getsource(sensory_transducer)

    # No label-keyed branches
    assert 'if label == ' not in source, "Found 'if label ==' branch in transducer"
    assert 'if label ==' not in source, "Found label equality check in transducer"

    # No static lookup dicts mapping labels to fixed param values
    import re, ast
    # Parse the AST to find dict assignments with string keys mapping to numbers
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and 'LIBRARY' in target.id:
                    pytest.fail(f"Found LIBRARY dict definition: {target.id}")
        # Check for if-label branches in functions
        if isinstance(node, ast.Compare):
            for comparator in node.comparators:
                if isinstance(comparator, ast.Constant) and comparator.value in (
                    "warm", "hot", "cold", "cool", "soft", "hard"
                ):
                    pytest.fail(f"Found label-specific branch for '{comparator.value}'")

    # Also check sensory_generators.py no longer has the dicts
    from dsf_ai_service.substrate import sensory_generators
    gen_source = inspect.getsource(sensory_generators)
    assert 'TOUCH_LIBRARY' not in gen_source, "TOUCH_LIBRARY still in sensory_generators"
    assert 'SMELL_LIBRARY' not in gen_source, "SMELL_LIBRARY still in sensory_generators"
    assert 'TASTE_LIBRARY' not in gen_source, "TASTE_LIBRARY still in sensory_generators"

    print(f"\n== T6: substrate-true sanity ==")
    print(f"  No label-keyed branches in transducer")
    print(f"  No LIBRARY dicts in sensory_generators")
    print(f"  No hardcoded label strings in transducer")


# ---------------------------------------------------------------------------
# T7: atlas integration
# ---------------------------------------------------------------------------

def test_t7_atlas_integration():
    """After 50 transduce calls recorded in atlas, call 51 uses _sample_from_bindings."""
    atlas = MockAtlasReader()
    transducer = SensoryTransducer(atlas)

    # First 50 calls — generate_initial (atlas empty)
    for tick in range(50):
        params = transducer.transduce("touch", "warm", tick=tick)
        # Record in atlas (simulating what production would do)
        atlas.add_binding("warm", "touch", params)

    # Verify atlas has 50 bindings
    assert atlas.has_bindings("warm", "touch")
    assert len(atlas.get_binding_params("warm", "touch")) == 50

    # Call 51: should use _sample_from_bindings
    params_51 = transducer.transduce("touch", "warm", tick=50)

    # Verify it sampled from distribution (mean of prior bindings)
    prior_temps = [p["temperature"] for p in atlas.get_binding_params("warm", "touch")]
    prior_mean = float(np.mean(prior_temps))

    print(f"\n== T7: atlas integration ==")
    print(f"  50 prior bindings recorded")
    print(f"  prior temperature mean={prior_mean:.4f}")
    print(f"  call 51 temperature={params_51['temperature']:.4f}")
    print(f"  (expected near prior mean ± std)")

    # After 50 uniform samples, mean ≈ 0.5. Call 51 should sample from that distribution.
    assert abs(params_51["temperature"] - prior_mean) < 0.4, (
        f"Call 51 should sample from prior distribution "
        f"(prior_mean={prior_mean:.4f}, got {params_51['temperature']:.4f})"
    )


# ---------------------------------------------------------------------------
# T8: determinism within session
# ---------------------------------------------------------------------------

def test_t8_determinism():
    """Same label + same tick → identical params; different ticks → different."""
    transducer = SensoryTransducer(NullAtlasReader())

    # Same tick → same params
    params_a = transducer.transduce("touch", "warm", tick=42)
    params_b = transducer.transduce("touch", "warm", tick=42)

    print(f"\n== T8: determinism ==")
    print(f"  Same tick (42): params_a == params_b: {params_a == params_b}")

    assert params_a == params_b, (
        f"Same (label, modality, tick) must produce identical params"
    )

    # Different tick → different params
    params_c = transducer.transduce("touch", "warm", tick=43)
    assert params_a != params_c, (
        f"Different ticks must produce different params"
    )
    print(f"  Different tick (43): params_a != params_c: {params_a != params_c}")


# ---------------------------------------------------------------------------
# T9: remote-mode variability (F12)
# ---------------------------------------------------------------------------

def test_t9_remote_mode_variability():
    """Same label at different ticks → different chi addresses (not same-label-same-chi)."""
    from dsf_ai_service.substrate.sensory_generators import (
        generate_sensory_signals, transduce_sensory_signals,
    )

    chi_values = []
    for tick in range(10):
        signals = generate_sensory_signals("touch", ["warm"], tick=tick * 100)
        channel_results = transduce_sensory_signals(signals)
        chis = [ch_data["chi"] for ch_data in channel_results.values()]
        chi_values.append(tuple(chis))

    print(f"\n== T9: remote-mode variability ==")
    for i, chis in enumerate(chi_values):
        print(f"  tick={i*100}: chi={chis}")

    # At least 2 distinct chi tuples across 10 calls
    unique = len(set(chi_values))
    print(f"  unique chi tuples: {unique}/10")

    assert unique >= 2, (
        f"Expected at least 2 distinct chi tuples from 10 calls, got {unique}. "
        f"Chi should vary with tick (no longer same-label-same-chi)."
    )


# ---------------------------------------------------------------------------
# T10: cross-mode consistency (F12)
# ---------------------------------------------------------------------------

def test_t10_cross_mode_consistency():
    """Embedded and remote paths use same pipeline → same distribution of chi."""
    from dsf_ai_service.substrate.sensory_generators import (
        generate_sensory_signals, transduce_sensory_signals,
    )

    # Both paths now go through: SensoryTransducer → generate_*_waveform → transduce
    # Simulate both with same transducer + tick
    transducer = SensoryTransducer(NullAtlasReader())

    embedded_chis = []
    remote_chis = []
    for tick in range(50):
        # "Embedded" path (app.py style)
        signals_e = generate_sensory_signals("touch", ["warm"],
                                             transducer=transducer, tick=tick)
        results_e = transduce_sensory_signals(signals_e)
        embedded_chis.extend(ch["chi"] for ch in results_e.values())

        # "Remote" path (substrate_runner style) — now identical
        signals_r = generate_sensory_signals("touch", ["warm"],
                                             transducer=transducer, tick=tick)
        results_r = transduce_sensory_signals(signals_r)
        remote_chis.extend(ch["chi"] for ch in results_r.values())

    # Same inputs → identical outputs (they use the same pipeline)
    print(f"\n== T10: cross-mode consistency ==")
    print(f"  embedded chi sample: {embedded_chis[:5]}")
    print(f"  remote chi sample:   {remote_chis[:5]}")
    print(f"  identical: {embedded_chis == remote_chis}")

    assert embedded_chis == remote_chis, (
        "Embedded and remote paths should produce identical chi values "
        "when given same transducer + tick (unified pipeline)"
    )


# ---------------------------------------------------------------------------
# T11: substrate-true sanity on F12
# ---------------------------------------------------------------------------

def test_t11_f12_substrate_true():
    """deterministic_motif_id not called for touch/smell/taste chi in substrate_runner."""
    import inspect
    from dsf_ai_service import substrate_runner

    source = inspect.getsource(substrate_runner)

    # Find the experience bundle handler
    # The old pattern was: deterministic_motif_id(f"{modality}_{desc}")
    # This should no longer exist
    import re
    old_pattern = re.findall(
        r'deterministic_motif_id\(f"[{]modality[}]_[{]desc[}]"\)', source
    )

    print(f"\n== T11: F12 substrate-true ==")
    print(f"  Old pattern 'deterministic_motif_id(f\"{{modality}}_{{desc}}\")' found: {len(old_pattern)} times")

    assert len(old_pattern) == 0, (
        f"Found {len(old_pattern)} instances of label-hashing chi derivation. "
        f"Touch/smell/taste chi should come from waveform transduction, not label hash."
    )

    # Chi derivation goes through transduce_sensory_signals (krimelack-based)
    assert "transduce_sensory_signals" in source, (
        "substrate_runner should use transduce_sensory_signals for chi derivation"
    )


# ---------------------------------------------------------------------------
# T12: backward compat — loom_model tests use inline params
# ---------------------------------------------------------------------------

def test_t12_backward_compat():
    """Loom model tests can generate touch signals without TOUCH_LIBRARY."""
    from dsf_ai_service.substrate.sensory_generators import generate_touch_waveform

    # The substrate-true way: inline physical params (what tests now use)
    params = {"temperature": 0.85, "pressure": 0.3, "texture_freq": 0.0,
              "sharpness": 0.0, "wetness": 0.0}
    waveforms = generate_touch_waveform(params)

    print(f"\n== T12: backward compat ==")
    print(f"  channels: {list(waveforms.keys())}")
    print(f"  all 200 samples: {all(len(v) == 200 for v in waveforms.values())}")

    assert len(waveforms) == 5, f"Expected 5 channels, got {len(waveforms)}"
    assert all(len(v) == 200 for v in waveforms.values()), "All channels should be 200 samples"

    # Can also use SensoryTransducer for a substrate-discovered signal
    transducer = SensoryTransducer(NullAtlasReader())
    discovered_params = transducer.transduce("touch", "hot", tick=42)
    waveforms2 = generate_touch_waveform(discovered_params)
    assert len(waveforms2) == 5
    print(f"  SensoryTransducer params: {discovered_params}")
    print(f"  Generates valid waveform: True")
