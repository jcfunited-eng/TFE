"""Production native-wheel API boundary.

The native artifact exposes physical substrate operations.  It must not
reintroduce the retired character-to-signal language shortcut.
"""

from __future__ import annotations

import guala_core


def test_production_native_api_excludes_scripted_language() -> None:
    assert not hasattr(guala_core, "word_signal")
    assert not hasattr(guala_core, "lang_transduce")
    assert not hasattr(guala_core, "canonical_l0_l4_trace_differential")
    assert not hasattr(guala_core, "seal_native_l0_l4_full_field_bank")


def test_production_native_api_retains_required_auditory_physics() -> None:
    for name in (
        "auditory_gammatone_field",
        "auditory_gammatone_stream",
        "auditory_joint_path_contains",
        "AuditoryIncrementalProposalCells",
    ):
        assert hasattr(guala_core, name), name


def test_production_native_api_retains_immutable_full_field_bank() -> None:
    for name in (
        "NativeL0L4FullFieldBank",
        "canonical_l0_l4_current_config",
        "settle_native_l0_l4_full_field_batch",
    ):
        assert hasattr(guala_core, name), name
