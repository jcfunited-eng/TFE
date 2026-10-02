"""6292 repair: exact custody and containment, not motor-integration proof."""
import struct

import pytest
from guala_core import ArcLoomNeuron, ModularSubstrate64D


def snapshot(sub):
    return bytes(sub.export_sparse_v4())


def test_exact_evidence_and_full_byte_refusal_before_and_after_cold_restore():
    sub = ModularSubstrate64D()
    sub.step([1] * 64, [1] * 32)
    for value in (1.0, -1.0, 0.25, 0.0625, 2.0**-200, 5e-324,
                  float(3**63), float(3**64), -0.0, 0.0):
        field = [0.0, value, 0.0, 0.0, 0.0, 0.0, 0.0]
        sub.consume_continuous_joint_field(field, 1.0)
        before = snapshot(sub)
        with pytest.raises(NotImplementedError, match="typed Psi/Krimelack"):
            sub.step([1] * 64, [1] * 32, None, None, -100.0)
        assert snapshot(sub) == before
        restored = ModularSubstrate64D()
        restored.import_sparse_v4(before)
        assert struct.pack(">d", restored.get_continuous_joint_field()[1]) == struct.pack(">d", value)
        with pytest.raises(NotImplementedError, match="typed Psi/Krimelack"):
            restored.step([1] * 64, [1] * 32, None, None, 0.85)
        assert snapshot(restored) == before
        del restored


def test_used_recipient_restores_identical_complete_component_successor():
    source = ModularSubstrate64D()
    # Explicit discrete component stimulus; named-formant input is retired.
    # Its atomic rejection is proved separately in test_arcloom_acoustic_boundary.
    source.step([1] * 64, [1] * 32, 1200.0, 45000, 0.0, [])
    before = snapshot(source)
    receiver = ModularSubstrate64D(0.5, 0.08, 0.15)
    for _ in range(3):
        receiver.step([-1] * 64, [1] * 32, 999.0, -45000, 0.85)
    receiver.import_sparse_v4(before)
    assert snapshot(receiver) == before
    arguments = ([0] * 64, [0] * 32, None, None, 0.0, [])
    assert source.step(*arguments) == receiver.step(*arguments)
    assert snapshot(source) == snapshot(receiver)


def test_unversioned_material_footer_is_not_silently_accepted():
    sub = ModularSubstrate64D()
    sub.step([1] * 64, [1] * 32)
    before = snapshot(sub)
    neuron = ArcLoomNeuron()
    extra = bytes(neuron.export_canonical_bytes())
    # Accepted ARCLOOM4 has no material-neuron tail. No payload may acquire
    # recipient material state or discard unrecognized retained state.
    with pytest.raises(ValueError, match="padding"):
        sub.import_sparse_v4(before + len(extra).to_bytes(4, "little") + extra)
    assert snapshot(sub) == before
