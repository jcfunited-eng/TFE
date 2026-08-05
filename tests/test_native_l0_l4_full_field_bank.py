from __future__ import annotations

from fractions import Fraction

from dsf_ai_service.glew_runtime import (
    native_l0_l4_full_field_bank as boundary,
)
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    NativeSensorySubstreamInput,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    NativeAxisCoordinate,
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)


class _Bank:
    schema = "guala.native.immutable_canonical_l0_l4_full_field_bank.v3"
    payload_sha256 = "0" * 64
    root_sha256 = "1" * 64
    port_count = 1
    source_sample_count = 2
    field_row_count = 1
    python_callback_count = 0

    def as_bytes(self) -> bytes:
        return b"bank"


class _NativeCore:
    def __init__(self) -> None:
        self.config_calls = 0
        self.batch_calls = 0
        self.candidates: list[bytes] = []

    def canonical_l0_l4_current_config(self):
        self.config_calls += 1
        return b"canonical-config", "0" * 64

    def settle_native_l0_l4_full_field_batch(self, payload: bytes):
        self.batch_calls += 1
        self.candidates.append(payload)
        return _Bank()


def _input() -> NativeSensorySubstreamInput:
    return NativeSensorySubstreamInput(
        sense=PhysicalSense.SIGHT,
        sensor_id="retina",
        substream_id="retina-0",
        topology_index=0,
        coordinates=(
            NativeAxisCoordinate("row", "0"),
            NativeAxisCoordinate("column", "0"),
        ),
        physical_quantity="optical_intensity",
        physical_unit="normalized_binary64",
        source_times=(Fraction(0), Fraction(1)),
        normalized_signal=(0.25, -0.5),
        phase_turns=(Fraction(0), Fraction(1, 4)),
    )


def _states() -> dict[PhysicalSense, SenseBoundaryState]:
    return {
        sense: (
            SenseBoundaryState.OBSERVED
            if sense is PhysicalSense.SIGHT
            else SenseBoundaryState.QUIESCENT
        )
        for sense in SENSE_ORDER
    }


def test_typed_boundary_makes_one_batch_call_and_returns_native_bank(
    monkeypatch,
) -> None:
    core = _NativeCore()
    monkeypatch.setattr(boundary, "_native_core", lambda: core)
    monkeypatch.setattr(boundary, "_CONFIG_PAYLOAD", None)

    result = boundary.settle_native_l0_l4_full_field_bank(
        assembly_id="episode-1",
        observed_substreams={PhysicalSense.SIGHT: (_input(),)},
        states=_states(),
    )

    assert result is not None
    assert result.python_callback_count == 0
    assert core.config_calls == 1
    assert core.batch_calls == 1
    assert len(core.candidates) == 1
    assert core.candidates[0].startswith(b"GLNEPI03")


def test_config_is_cached_but_each_episode_has_exactly_one_batch_call(
    monkeypatch,
) -> None:
    core = _NativeCore()
    monkeypatch.setattr(boundary, "_native_core", lambda: core)
    monkeypatch.setattr(boundary, "_CONFIG_PAYLOAD", None)
    values = {PhysicalSense.SIGHT: (_input(),)}
    states = _states()

    boundary.settle_native_l0_l4_full_field_bank(
        assembly_id="episode-1",
        observed_substreams=values,
        states=states,
    )
    boundary.settle_native_l0_l4_full_field_bank(
        assembly_id="episode-2",
        observed_substreams=values,
        states=states,
    )

    assert core.config_calls == 1
    assert core.batch_calls == 2
    assert len(core.candidates) == 2
    assert core.candidates[0] != core.candidates[1]
