"""Fail-closed rejection of the retired named-formant auditory shortcut.

These are discrete component boundary proofs, not learned speech or A10/A11
closure. Whole checkpoint equality covers membrane, motor, topology and weights.
"""

import pytest
from guala_core import ModularSubstrate64D


def test_named_formants_refuse_before_fresh_or_retained_state_changes():
    original = ModularSubstrate64D()
    for retained in (False, True):
        if retained:
            original.step([1] * 64, [0] * 32)
        before = bytes(original.export_sparse_v4())
        restored = ModularSubstrate64D()
        restored.import_sparse_v4(before)
        assert bytes(restored.export_sparse_v4()) == before
        for subject in (original, restored):
            for formants in ([380.0, 1100.0, 2400.0],
                             [500.0, 1000.0, 2350.0],
                             [280.0, 850.0, 2200.0],
                             [0.0] * 8):
                with pytest.raises(NotImplementedError, match="Formant-profile"):
                    subject.step(
                        [1] * 64, [1] * 32,
                        observed_r_mm=450.0,
                        observed_theta_mdeg=25000,
                        barrier_stress=0.88,
                        acoustic_formants=formants,
                    )
                assert bytes(subject.export_sparse_v4()) == before


def test_explicit_component_input_retains_exact_cold_next_step():
    original = ModularSubstrate64D()
    original.step([1] * 64, [0] * 32)
    restored = ModularSubstrate64D()
    restored.import_sparse_v4(bytes(original.export_sparse_v4()))
    for subject in (original, restored):
        subject.step([0] * 64, [0] * 32, acoustic_formants=[])
    assert bytes(original.export_sparse_v4()) == bytes(restored.export_sparse_v4())
