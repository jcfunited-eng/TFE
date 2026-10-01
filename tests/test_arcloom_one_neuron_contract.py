"""A13/A14 rejection/custody falsifiers, NOT proof of a mounted neuron.

The former positive fixtures exercised a rejected untyped one-phase operator.
The actual A10 physical capability remains open in the causal witness suite.
Run with the exact candidate native extension, never the installed predecessor.
"""
import importlib.util
from pathlib import Path
import tarfile

import pytest
from guala_core import ModularSubstrate64D

ROOT = Path(__file__).resolve().parents[1]
RETIRED_API = (
    "step_mounted_canonical_neuron",
    "get_mounted_neuron_state",
    "export_mounted_neuron_bytes",
    "import_mounted_neuron_bytes",
    "step_operator_transition",
    "mounted_operator",
    "mounted_operator_mut",
)


def _load_adapter(relative):
    spec = importlib.util.spec_from_file_location("a13_adapter", ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.ModularColumnSubstrate


def _rejected_untyped_stream(field, stability):
    """Historical counterexample only; this must never become a consumer."""
    flattened = []
    for value in (*field, stability):
        numerator, denominator, _sign, zero = ModularSubstrate64D.float_to_rational_trits(value)
        if not zero:
            flattened.extend(numerator)
            flattened.extend(denominator)
    return flattened


def test_field_identity_cannot_be_proven_by_digit_participation():
    field_a = (1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    field_b = (0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    assert field_a != field_b
    assert _rejected_untyped_stream(field_a, 1.0) == _rejected_untyped_stream(field_b, 1.0)
    # Numerator/denominator and place identity are also absent from the force
    # sum; using every digit does not recover their original roles.
    from collections import Counter
    assert Counter(_rejected_untyped_stream((2.0,), 0.0)) == Counter(
        _rejected_untyped_stream((0.5,), 0.0)
    )
    assert Counter(_rejected_untyped_stream((10.0,), 0.0)) == Counter(
        _rejected_untyped_stream((12.0,), 0.0)
    )
    # Numeric sign itself WAS preserved by signed numerator digits.
    assert _rejected_untyped_stream((-1.0,), 0.0) != _rejected_untyped_stream((1.0,), 0.0)


@pytest.mark.parametrize("relative", [
    "dsf_ai_service/substrate/modular_column_substrate.py",
    "arcloom_demonstrator/substrate/modular_column_substrate.py",
])
def test_native_and_python_cannot_reenter_rejected_mount(relative):
    adapter = _load_adapter(relative)
    for name in RETIRED_API:
        assert not hasattr(adapter, name), name
        assert not hasattr(ModularSubstrate64D, name), name
    for relative_source in (
        "native/guala_core/src/cortical_column.rs",
        "arcloom_demonstrator/native/guala_core/src/cortical_column.rs",
        "native/guala_core/src/constitutive.rs",
    ):
        source = (ROOT / relative_source).read_text()
        for retired in (*RETIRED_API, "NeuronPhaseGateTransition", "normalize_phase_and_winding",
                        "TypedPhaseGateMaterialOperator", "PhaseCoupledOscillatorFabric"):
            assert retired not in source, (relative_source, retired)


def test_ordinary_checkpoint_replaces_used_recipient_and_preserves_next_interval():
    original = ModularSubstrate64D()
    original.step([1] * 48 + [0] * 16, [1] * 32)
    checkpoint = bytes(original.export_sparse_v4())
    restored = ModularSubstrate64D()
    restored.step([-1] * 48 + [0] * 16, [-1] * 32)
    restored.import_sparse_v4(checkpoint)
    assert bytes(restored.export_sparse_v4()) == checkpoint
    expected = original.step([0] * 64, [0] * 32)
    actual = restored.step([0] * 64, [0] * 32)
    assert actual == expected
    assert bytes(original.export_sparse_v4()) == bytes(restored.export_sparse_v4())


def test_release_archive_contains_exact_source_without_rejected_api():
    # Archive custody only, not independent native compilation or deployment.
    with tarfile.open(ROOT / "arcloom_demonstrator_v1.0.tar.gz", "r:gz") as archive:
        regular = 0
        for member in archive.getmembers():
            path = Path(member.name)
            assert not path.is_absolute() and ".." not in path.parts
            assert path.parts[0] == "arcloom_demonstrator"
            assert not member.issym() and not member.islnk()
            assert not any(part in ("__pycache__", ".pytest_cache", "target") for part in path.parts)
            if member.isdir():
                continue
            assert member.isfile()
            regular += 1
            assert archive.extractfile(member).read() == (ROOT / path).read_bytes(), member.name
        assert regular > 0


def test_primary_and_demonstrator_share_the_same_native_checkpoint_law():
    """No new primary state or migration may hide behind an old release archive."""
    primary = ROOT / "native/guala_core/src/cortical_column.rs"
    released = ROOT / "arcloom_demonstrator/native/guala_core/src/cortical_column.rs"
    assert primary.read_bytes() == released.read_bytes()


def test_current_restore_refuses_unrecognized_extension_atomically():
    """Ordinary restore must not infer a new law or synthesize missing state."""
    recipient = ModularSubstrate64D()
    recipient.step([1] * 48 + [0] * 16, [1] * 32)
    before = bytes(recipient.export_sparse_v4())
    for malformed in (before + bytes(936), before[:-8]):
        with pytest.raises(ValueError):
            recipient.import_sparse_v4(malformed)
        assert bytes(recipient.export_sparse_v4()) == before
