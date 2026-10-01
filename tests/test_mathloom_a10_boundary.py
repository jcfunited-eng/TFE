"""A10 numerical custody and atomic unsupported-operator checks.

These tests explicitly do NOT claim full-field neuronal or organism closure.
Run against the freshly built isolated candidate native extension.
"""
import importlib.util
import struct
from pathlib import Path

import pytest
from guala_core import ModularSubstrate64D

ROOT = Path(__file__).resolve().parents[1]


def test_exact_codec_rejects_corrupted_or_rounded_representations():
    codec = ModularSubstrate64D
    for value in (0.0, -0.0, 5e-324, 1e-300, 0.5, 0.6, 0.9, 1.0, 2.0, 1.79e308, -1.79e308):
        record = codec.float_to_rational_trits(value)
        assert struct.pack(">d", codec.rational_trits_to_float(*record)) == struct.pack(">d", value)
    for args in (([2], [1], 1, False), ([1], [1], 1, True),
                 ([1], [1], -1, False), ([0], [1], 1, False),
                 ([1, 0], [1], 1, False), ([1], [0], 1, False)):
        with pytest.raises(ValueError):
            codec.rational_trits_to_float(*args)
    n, digits = 2**53 + 1, []
    while n:
        rem = n % 3
        if rem == 2:
            rem = -1
        digits.append(rem)
        n = (n - rem) // 3
    with pytest.raises(ValueError, match="not exactly representable"):
        codec.rational_trits_to_float(digits, [1], 1, False)


@pytest.mark.parametrize("relative", [
    "dsf_ai_service/substrate/modular_column_substrate.py",
    "arcloom_demonstrator/substrate/modular_column_substrate.py",
])
def test_python_codec_never_coerces_malformed_evidence(relative):
    spec = importlib.util.spec_from_file_location("a10_codec_adapter", ROOT / relative)
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    decode = adapter.ModularColumnSubstrate.rational_trits_to_float
    for args in (([1.9], [1], 1, False), (["1"], [1], 1, False),
                 ([True], [1], 1, False), ([1], [1], 1.1, False),
                 ([1], [1], 1, "false")):
        with pytest.raises(ValueError):
            decode(*args)


def test_high_ternary_positions_are_not_interchangeable_evidence():
    # This pair defeated the rejected 32-position consumer despite an exact codec.
    a = 2**-52
    b = (2 * 3**32 + 1) * 2**-52
    na, da, sa, za = ModularSubstrate64D.float_to_rational_trits(a)
    nb, db, sb, zb = ModularSubstrate64D.float_to_rational_trits(b)
    assert a != b and da == db and sa == sb and za == zb
    assert (list(na) + [0] * 32)[:32] == (list(nb) + [0] * 32)[:32]
    assert na != nb and any(nb[32:])
    assert ModularSubstrate64D.rational_trits_to_float(na, da, sa, za) == a
    assert ModularSubstrate64D.rational_trits_to_float(nb, db, sb, zb) == b


def test_full_field_step_and_cold_step_refuse_without_mutating_any_state():
    sub = ModularSubstrate64D()
    sub.step([1] * 48 + [0] * 16, [1] * 32, 1200.0, 45000, 0.0, [220.0])
    cases = [([value] + [0.0] * 6, 1.0)
             for value in (2**-52, (2 * 3**32 + 1) * 2**-52, 0.0)]
    # Every field and global stability stay present evidence, never a shortcut
    # for choosing a motor output. Include the former P-B and refusal branches.
    cases += [([float(i == slot) for i in range(7)], 0.0) for slot in range(7)]
    for field, stability in cases:
        sub.consume_continuous_joint_field(field, stability)
        before = bytes(sub.export_sparse_v4())
        with pytest.raises(NotImplementedError, match="typed Psi/Krimelack"):
            sub.step([1] * 64, [1] * 32, 999.0, -45000, 1.0, [440.0])
        assert bytes(sub.export_sparse_v4()) == before
        restored = ModularSubstrate64D()
        restored.import_sparse_v4(before)
        assert bytes(restored.export_sparse_v4()) == before
        with pytest.raises(NotImplementedError, match="typed Psi/Krimelack"):
            restored.step([1] * 64, [1] * 32, 999.0, -45000, 1.0, [440.0])
        assert bytes(restored.export_sparse_v4()) == before
        del restored


def test_component_continuation_after_refusal_preserves_exact_successor():
    # Removing unavailable evidence is an explicit component-only operation.
    # It must not leave covert phase, motor, trace or plastic mutations behind.
    control = ModularSubstrate64D()
    control.step([1] * 48 + [0] * 16, [1] * 32)
    candidate = ModularSubstrate64D()
    candidate.import_sparse_v4(bytes(control.export_sparse_v4()))
    candidate.consume_continuous_joint_field([0.0] * 5 + [1.0, 0.0], 0.0)
    with pytest.raises(NotImplementedError, match="typed Psi/Krimelack"):
        candidate.step([1] * 64, [1] * 32, 10.0, 90000, 1.0, [220.0])
    candidate.clear_continuous_joint_field()
    control.clear_continuous_joint_field()
    assert bytes(candidate.export_sparse_v4()) == bytes(control.export_sparse_v4())
    assert candidate.step([0] * 64, [0] * 32) == control.step([0] * 64, [0] * 32)
    assert bytes(candidate.export_sparse_v4()) == bytes(control.export_sparse_v4())


def test_legacy_field_slots_cannot_resurrect_digit_injection():
    sub = ModularSubstrate64D()
    before = bytes(sub.export_sparse_v4())
    cold = ModularSubstrate64D()
    cold.import_sparse_v4(before)
    sub.step([0] * 64, [0] * 32)
    cold.step([0] * 48 + [1] * 16, [0] * 32)
    assert bytes(sub.export_sparse_v4()) == bytes(cold.export_sparse_v4())

def test_ordinary_restore_property_does_not_silently_migrate():
    # Execute the actual production property with its real adapter dependency.
    # This isolates custody routing, not organism behavior or physical closure.
    import ast
    from types import SimpleNamespace

    path = ROOT / "dsf_ai_service/guala_functional_organism.py"
    tree = ast.parse(path.read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "FunctionalOrganism")
    prop = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "_modular_substrate")
    spec = importlib.util.spec_from_file_location(
        "a10_restore_adapter", ROOT / "dsf_ai_service/substrate/modular_column_substrate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    namespace = {"ModularColumnSubstrate": module.ModularColumnSubstrate}
    exec(compile(ast.Module(body=[prop], type_ignores=[]), str(path), "exec"), namespace)
    getter = namespace["_modular_substrate"].fget
    original = module.ModularColumnSubstrate()
    data = original.to_dict()
    receiver = SimpleNamespace(_state={"modular_substrate": data})
    assert getter(receiver).export_sparse_bytes() == original.export_sparse_bytes()
    for version in ("ARCLOOM2", "ARCLOOM3"):
        legacy = dict(data, format=version, predecessor_layout="36B", field_present=True)
        receiver = SimpleNamespace(_state={"modular_substrate": legacy})
        with pytest.raises(ValueError, match="only accepts current format"):
            getter(receiver)
        assert not hasattr(receiver, "_cached_modular_substrate")
        assert receiver._state["modular_substrate"] == legacy


def test_source_does_not_recreate_joint_field_by_averaging():
    # Anti-resurrection source check, not an end-to-end execution claim.
    import ast

    path = ROOT / "dsf_ai_service/guala_functional_organism.py"
    tree = ast.parse(path.read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "FunctionalOrganism")
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "_form_moments")
    names = {n.attr for n in ast.walk(method) if isinstance(n, ast.Attribute)}
    assert "mean" not in names
    assert "max" not in names
    assert any(isinstance(n, ast.Constant) and isinstance(n.value, str)
               and "Shared full-field delivery is unavailable" in n.value for n in ast.walk(method))



@pytest.mark.parametrize("optimization", [[], ["-O"]])
def test_burn_in_cannot_certify_an_unmounted_operator(optimization):
    import json
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, *optimization, str(ROOT / "tools/run_arcloom_50k_burn_in.py"),
         "--cycles", "1", "--checkpoint-interval", "2"],
        cwd=ROOT, capture_output=True, text=True, timeout=30, check=False)
    assert result.returncode == 2, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "blocked_unmounted_operator"
    assert report["completed_cycles"] == 0
    assert report["checkpoint_roundtrips"] == 0
    assert report["same_process_next_step_checks"] == 0
    assert report["canonical_uf_used"] is False
    assert report["sleep_consolidation_tested"] is False
    assert report["physical_equilibrium_proven"] is False
    assert report["memory_competence_proven"] is False
    assert report["full_field_closure_proven"] is False
