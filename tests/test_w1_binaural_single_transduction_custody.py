from __future__ import annotations

import json
import math
import struct
from dataclasses import replace
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    build_six_sense_full_field,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate import (
    auditory_receptor_event_boundary,
    w1_binaural_acoustic_physics,
    w1_binaural_receptor_settlement,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)
from dsf_ai_service.substrate.w1_binaural_auditory_l5 import (
    W1BinauralAuditoryL5Owner,
)
from dsf_ai_service.substrate.w1_binaural_receptor_settlement import (
    settle_w1_binaural_receptors,
)


SAMPLE_RATE_HZ = 16_000
SAMPLE_COUNT = 960


def _tone(frequency_hz: int, amplitude: int) -> bytes:
    samples = tuple(
        int(
            amplitude
            * math.sin(
                2.0 * math.pi * frequency_hz * index / SAMPLE_RATE_HZ
            )
        )
        for index in range(SAMPLE_COUNT)
    )
    return struct.pack(f"<{SAMPLE_COUNT}h", *samples)


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def test_each_ear_is_transduced_and_mounted_once_then_settled_from_custody(
    monkeypatch,
) -> None:
    assert not hasattr(
        w1_binaural_receptor_settlement,
        "transduce_auditory_full_field",
    )
    assert not hasattr(
        auditory_receptor_event_boundary,
        "auditory_kernel_component_inputs",
    )
    actual_transducer = (
        w1_binaural_acoustic_physics.transduce_auditory_full_field
    )
    actual_component_mount = (
        w1_binaural_acoustic_physics.auditory_kernel_component_inputs
    )
    transduction_pcm_commitments: list[tuple[float, ...]] = []
    mounted_capture_ids: list[int] = []

    def counted_transducer(signal, *, sample_rate_hz):
        transduction_pcm_commitments.append(
            tuple(float(value) for value in signal)
        )
        return actual_transducer(
            signal,
            sample_rate_hz=sample_rate_hz,
        )

    def counted_component_mount(capture, *, source_anchor):
        mounted_capture_ids.append(id(capture))
        return actual_component_mount(
            capture,
            source_anchor=source_anchor,
        )

    monkeypatch.setattr(
        w1_binaural_acoustic_physics,
        "transduce_auditory_full_field",
        counted_transducer,
    )
    monkeypatch.setattr(
        w1_binaural_acoustic_physics,
        "auditory_kernel_component_inputs",
        counted_component_mount,
    )
    left_pcm = _tone(440, 4_000)
    right_pcm = _tone(730, 2_000)
    source_time_start = Fraction(0)
    source_time_end = Fraction(SAMPLE_COUNT, SAMPLE_RATE_HZ)
    left = w1_binaural_acoustic_physics.binaural_sound_field_inputs(
        ear="left",
        topology_index=0,
        pcm=left_pcm,
        source_time_start=source_time_start,
    )
    right = w1_binaural_acoustic_physics.binaural_sound_field_inputs(
        ear="right",
        topology_index=len(left),
        pcm=right_pcm,
        source_time_start=source_time_start,
    )

    assert len(transduction_pcm_commitments) == 2
    assert len(mounted_capture_ids) == 2
    assert mounted_capture_ids == [id(left.capture), id(right.capture)]
    assert transduction_pcm_commitments[0] != (
        transduction_pcm_commitments[1]
    )
    assert left.transduction_count == right.transduction_count == 1
    assert left.component_mount_count == right.component_mount_count == 1
    assert left.capture is not right.capture
    assert left.component_inputs[0].normalized_signal != (
        right.component_inputs[0].normalized_signal
    )
    assert left.native_inputs[0].coordinates[0].coordinate_id == "left"
    assert right.native_inputs[0].coordinates[0].coordinate_id == "right"

    built = build_six_sense_full_field(
        assembly_id="w1-single-transduction-custody",
        source_time_start=source_time_start,
        source_time_end=source_time_end,
        observed_substreams={
            PhysicalSense.SOUND: (*left, *right),
        },
        states={
            sense: (
                SenseBoundaryState.OBSERVED
                if sense is PhysicalSense.SOUND
                else SenseBoundaryState.SENSOR_UNAVAILABLE
            )
            for sense in SENSE_ORDER
        },
    )
    causal = ExactCausalExperienceOwner(
        on_settlement=lambda _settlement: None,
        log_event=lambda *_args, **_kwargs: None,
    ).settle(
        built,
        routing_chis=(),
        source_tags=(),
    )
    l5_owner = W1BinauralAuditoryL5Owner(max_transitions=1)
    l5 = l5_owner.prepare(causal)
    l5_owner.commit_prepared(l5)

    first = settle_w1_binaural_receptors(
        left_custody=left,
        right_custody=right,
        causal_settlement=causal,
        w1_l5=l5,
    )
    second = settle_w1_binaural_receptors(
        left_custody=left,
        right_custody=right,
        causal_settlement=causal,
        w1_l5=l5,
    )

    assert len(transduction_pcm_commitments) == 2
    assert len(mounted_capture_ids) == 2
    assert first.authority_receipt_sha256 == (
        second.authority_receipt_sha256
    )
    assert _canonical(first.authority_record()) == (
        _canonical(second.authority_record())
    )
    assert first.ears[0].source_pcm_sha256 != (
        first.ears[1].source_pcm_sha256
    )
    assert first.ears[0].event.authority_receipt_sha256 != (
        first.ears[1].event.authority_receipt_sha256
    )
    for ear in first.ears:
        for channel in ear.event.channels:
            for field_tuple in (
                *channel.pressure_fields,
                *channel.phase_fields,
            ):
                assert tuple(
                    name for name, _value in field_tuple.fields
                ) == DSF_FIELD_ORDER

    with pytest.raises(
        ValueError,
        match="transduction custody changed",
    ):
        settle_w1_binaural_receptors(
            left_custody=replace(left, transduction_count=2),
            right_custody=right,
            causal_settlement=causal,
            w1_l5=l5,
        )
    with pytest.raises(
        ValueError,
        match="transduction custody changed",
    ):
        settle_w1_binaural_receptors(
            left_custody=left,
            right_custody=replace(
                right,
                capture=left.capture,
            ),
            causal_settlement=causal,
            w1_l5=l5,
        )
