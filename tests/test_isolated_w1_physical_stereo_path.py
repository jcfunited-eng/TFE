from __future__ import annotations

import math
import struct
from dataclasses import replace
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    build_transaction_owned_six_sense_full_field,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.w1_binaural_acoustic_physics import (
    binaural_sound_field_inputs,
)
from dsf_ai_service.substrate.w1_exact_binaural_source_separation import (
    ExactBinauralSeparationState,
    separate_exact_binaural_sources,
)
from tools.isolated_w1_physical_stereo_path import (
    PhysicalStereoAuditAuthority,
)


KEY = b"isolated-w1-physical-stereo-path-test-key"
SAMPLE_COUNT = 960


def _source(frequency: int) -> bytes:
    values = tuple(
        4
        * int(
            1_500
            * math.sin(
                2.0 * math.pi * frequency * index / 16_000
            )
        )
        for index in range(SAMPLE_COUNT)
    )
    return struct.pack(f"<{len(values)}h", *values)


def _mount(capture):
    inputs = (
        *binaural_sound_field_inputs(
            ear="left",
            topology_index=0,
            pcm=capture.left_pcm_s16le,
            source_time_start=Fraction(0),
        ),
        *binaural_sound_field_inputs(
            ear="right",
            topology_index=32,
            pcm=capture.right_pcm_s16le,
            source_time_start=Fraction(0),
        ),
    )
    built = build_transaction_owned_six_sense_full_field(
        assembly_id="isolated-w1-physical-stereo-test",
        source_time_start=Fraction(0),
        source_time_end=Fraction(
            capture.capture_sample_count, 16_000
        ),
        observed_substreams={PhysicalSense.SOUND: inputs},
        states={
            sense: (
                SenseBoundaryState.OBSERVED
                if sense is PhysicalSense.SOUND
                else SenseBoundaryState.SENSOR_UNAVAILABLE
            )
            for sense in SENSE_ORDER
        },
    )
    built.verify_construction()
    sound = next(
        value
        for value in built.boundary.boundaries
        if value.sense is PhysicalSense.SOUND
    )
    return built, sound


def test_distinct_physical_paths_separate_overlapping_sources_exactly():
    authority = PhysicalStereoAuditAuthority(authority_key=KEY)
    first = _source(440)
    second = _source(730)

    capture = authority.render(
        (first, second),
        source_ordinals=(0, 1),
    )
    result = separate_exact_binaural_sources(
        left_pcm_s16le=capture.left_pcm_s16le,
        right_pcm_s16le=capture.right_pcm_s16le,
        paths=capture.paths,
        source_sample_count=SAMPLE_COUNT,
    )

    assert tuple(
        (
            value.left_delay_samples,
            value.right_delay_samples,
            value.left_attenuation,
            value.right_attenuation,
        )
        for value in authority.paths
    ) == (
        (10, 14, Fraction(1), Fraction(1)),
        (14, 10, Fraction(1), Fraction(1)),
    )
    assert result.state is ExactBinauralSeparationState.SEPARATED
    assert result.separated_pcm_s16le == (first, second)
    result.verify()


def test_both_ears_enter_full_l0_l4_and_mirrored_assemblies():
    authority = PhysicalStereoAuditAuthority(authority_key=KEY)
    capture = authority.render((_source(440),), source_ordinals=(0,))
    brainstem = authority.compare_brainstem(capture)
    built, sound = _mount(capture)

    assert len(sound.substreams) == 64
    for value in sound.substreams:
        value.verify(built.receipt_registry)
        assert all(
            tuple(
                getattr(field, name) for name in DSF_FIELD_ORDER
            )
            == field.as_tuple()
            for field in value.kernel_basin.exact_dsf_field_tuples
        )
    left = tuple(
        value.kernel_basin.authority_receipt_sha256
        for value in sound.substreams[:32]
    )
    right = tuple(
        value.kernel_basin.authority_receipt_sha256
        for value in sound.substreams[32:]
    )
    assembly = authority.assemble_bilateral(
        left_ear_port_receipt_sha256s=left,
        right_ear_port_receipt_sha256s=right,
        brainstem=brainstem,
    )

    assert len(brainstem.frames) == 16 * 6
    assert assembly.left_hemisphere_port_receipt_sha256s == left + right
    assert assembly.right_hemisphere_port_receipt_sha256s == right + left
    assert set(
        assembly.left_hemisphere_port_receipt_sha256s
    ) == set(assembly.right_hemisphere_port_receipt_sha256s)
    assert assembly.left_hemisphere_port_receipt_sha256s != (
        assembly.right_hemisphere_port_receipt_sha256s
    )


def test_stereo_and_brainstem_authorities_reject_tampering():
    authority = PhysicalStereoAuditAuthority(authority_key=KEY)
    capture = authority.render((_source(440),), source_ordinals=(0,))
    brainstem = authority.compare_brainstem(capture)

    with pytest.raises(ValueError, match="capture authority changed"):
        authority.verify_capture(replace(
            capture,
            authority_hmac_sha256="0" * 64,
        ))
    with pytest.raises(ValueError, match="brainstem authority changed"):
        authority.verify_brainstem(replace(
            brainstem,
            authority_hmac_sha256="0" * 64,
        ))
