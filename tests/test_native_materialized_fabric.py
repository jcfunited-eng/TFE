from __future__ import annotations

import pytest

from dsf_ai_service.glew_runtime import native_materialized_fabric as boundary


class _Source:
    schema = "guala.native.exact_joint_source_episode.v1"
    payload_sha256 = "0" * 64
    port_count = 2
    source_sample_count = 4
    python_callback_count = 0

    def as_bytes(self) -> bytes:
        return b"source"


class _Result:
    schema = "guala.native.owner_free_materialized_fabric.v4"
    state_sha256 = "2" * 64
    outcome = "joint_neuronal_fractals_transitioned"
    mosaic_sha256 = None
    mosaic_count = 0
    materialized_neuron_count = 0
    materialized_body_count = 0
    evidence_count = 1
    joint_field_count = 1
    joint_neuron_count = 2
    transitioned_fractal_count = 2
    recurrent_fractal_count = 0
    joint_transition_sha256 = "4" * 64
    episode_relation_candidate_sha256 = None
    python_callback_count = 0

    def as_bytes(self) -> bytes:
        return b"state"


class _NativeCore:
    def __init__(self) -> None:
        self.calls = []

    def transition_materialized_fabric(
        self, prior, source, max_state_bytes, max_working_bytes
    ):
        self.calls.append(
            (prior, source, max_state_bytes, max_working_bytes)
        )
        return _Result()


def test_boundary_makes_one_native_call_without_per_port_field_bank(
    monkeypatch,
) -> None:
    core = _NativeCore()
    monkeypatch.setattr(boundary, "_native_core", lambda: core)
    source = _Source()

    result = boundary.transition_native_materialized_fabric(
        prior_state=None,
        source=source,
    )

    assert result.outcome == "joint_neuronal_fractals_transitioned"
    assert result.python_callback_count == 0
    assert core.calls == [
        (None, source, 64 * 1024 * 1024, 64 * 1024 * 1024)
    ]


def test_historical_field_bank_argument_is_absent() -> None:
    with pytest.raises(TypeError, match="unexpected keyword"):
        boundary.transition_native_materialized_fabric(
            prior_state=None,
            bank=_Source(),
        )


def test_working_memory_and_persistent_state_are_separate_boundaries(
    monkeypatch,
) -> None:
    core = _NativeCore()
    monkeypatch.setattr(boundary, "_native_core", lambda: core)
    source = _Source()

    boundary.transition_native_materialized_fabric(
        prior_state=None,
        source=source,
        max_state_bytes=1024,
        max_working_bytes=4096,
    )

    assert core.calls == [(None, source, 1024, 4096)]
