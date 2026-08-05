from __future__ import annotations

import hashlib
import math
from dataclasses import replace
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    NativeAxisCoordinate,
    PhysicalSense,
)
from dsf_ai_service.substrate.w1_binaural_acoustic_physics import (
    pcm16_bytes,
    signed_pcm16_samples,
)
from tools.dual_kernel_full_field_acceptance import (
    CANONICAL_KERNEL_ID,
    NO_LEARNING_CLAIM,
    SIDE_KERNEL_ID,
    DualKernelFullFieldAcceptanceHarness,
    LivedNonauditoryChannel,
)
from tools.isolated_w1_physical_stereo_path import (
    PhysicalStereoAuditAuthority,
)


AUTHORITY_KEY = b"dual-kernel-full-field-acceptance-test-key-v1"
CAPTURE_KEY = b"dual-kernel-full-field-capture-test-key-v1"
SOURCE_TIME_START = Fraction(19, 7)
SOURCE_SAMPLE_COUNT = 1_280
SAMPLE_RATE_HZ = 16_000


def _spoken_pressure() -> bytes:
    """Deterministic voiced, multi-formant pressure; data only, never meaning."""

    samples = []
    for index in range(SOURCE_SAMPLE_COUNT):
        onset = min(index, 160)
        release = min(SOURCE_SAMPLE_COUNT - index, 160)
        envelope = min(onset, release, 160)
        pressure = (
            9 * int(180 * math.sin(2 * math.pi * 120 * index / SAMPLE_RATE_HZ))
            + 5 * int(120 * math.sin(
                2 * math.pi * 720 * index / SAMPLE_RATE_HZ
            ))
            + 3 * int(90 * math.sin(
                2 * math.pi * 1_240 * index / SAMPLE_RATE_HZ
            ))
        )
        samples.append(pressure * envelope // 160)
    return pcm16_bytes(tuple(samples))


def _fixture():
    capture_authority = PhysicalStereoAuditAuthority(
        authority_key=CAPTURE_KEY
    )
    capture = capture_authority.render(
        (_spoken_pressure(),),
        source_ordinals=(0,),
    )
    times = tuple(
        SOURCE_TIME_START + Fraction(index, SAMPLE_RATE_HZ)
        for index in range(capture.capture_sample_count)
    )
    channels = (
        LivedNonauditoryChannel(
            sense=PhysicalSense.SIGHT,
            sensor_id="authenticated-lived-retina",
            substream_id="left-light-receptor",
            topology_index=0,
            coordinates=(
                NativeAxisCoordinate("retinal-column", "left"),
            ),
            physical_quantity="incident-light",
            physical_unit="normalized-photon-load",
            source_times=times,
            signal=tuple(
                Fraction((index // 80) % 4, 8)
                for index in range(capture.capture_sample_count)
            ),
            phase_turns=(Fraction(0),) * capture.capture_sample_count,
        ),
        LivedNonauditoryChannel(
            sense=PhysicalSense.SIGHT,
            sensor_id="authenticated-lived-retina",
            substream_id="right-light-receptor",
            topology_index=1,
            coordinates=(
                NativeAxisCoordinate("retinal-column", "right"),
            ),
            physical_quantity="incident-light",
            physical_unit="normalized-photon-load",
            source_times=times,
            signal=tuple(
                Fraction(3 - ((index // 80) % 4), 8)
                for index in range(capture.capture_sample_count)
            ),
            phase_turns=(Fraction(0),) * capture.capture_sample_count,
        ),
        LivedNonauditoryChannel(
            sense=PhysicalSense.TOUCH,
            sensor_id="authenticated-lived-skin",
            substream_id="left-contact-load",
            topology_index=0,
            coordinates=(
                NativeAxisCoordinate("body-side", "left"),
            ),
            physical_quantity="contact-load",
            physical_unit="normalized-force",
            source_times=times,
            signal=tuple(
                Fraction(1 if 320 <= index < 960 else 0, 4)
                for index in range(capture.capture_sample_count)
            ),
            phase_turns=(Fraction(0),) * capture.capture_sample_count,
        ),
        LivedNonauditoryChannel(
            sense=PhysicalSense.TOUCH,
            sensor_id="authenticated-lived-skin",
            substream_id="right-contact-load",
            topology_index=1,
            coordinates=(
                NativeAxisCoordinate("body-side", "right"),
            ),
            physical_quantity="contact-load",
            physical_unit="normalized-force",
            source_times=times,
            signal=tuple(
                Fraction(1 if 480 <= index < 1_120 else 0, 8)
                for index in range(capture.capture_sample_count)
            ),
            phase_turns=(Fraction(0),) * capture.capture_sample_count,
        ),
    )
    harness = DualKernelFullFieldAcceptanceHarness(
        authority_key=AUTHORITY_KEY,
        capture_authority=capture_authority,
    )
    return harness, capture, channels


def _accept():
    harness, capture, channels = _fixture()
    accepted = harness.accept(
        capture=capture,
        world_observation_receipt_sha256=hashlib.sha256(
            b"authenticated-lived-world-observation"
        ).hexdigest(),
        source_time_start=SOURCE_TIME_START,
        nonauditory_channels=channels,
    )
    return harness, accepted


def test_identical_authenticated_raw_evidence_reaches_two_complete_fields():
    harness, accepted = _accept()

    harness.verify(accepted)
    assert accepted.disposition == NO_LEARNING_CLAIM
    assert accepted.canonical.kernel_id == CANONICAL_KERNEL_ID
    assert accepted.side.kernel_id == SIDE_KERNEL_ID
    assert (
        accepted.canonical.raw_encounter_receipt_sha256
        == accepted.side.raw_encounter_receipt_sha256
        == accepted.raw_encounter.authority_receipt_sha256
    )

    boundaries = {
        value.sense: value
        for value in accepted.canonical.full_field.boundary.boundaries
    }
    assert len(boundaries[PhysicalSense.SOUND].substreams) == 64
    assert len(boundaries[PhysicalSense.SIGHT].substreams) == 2
    assert len(boundaries[PhysicalSense.TOUCH].substreams) == 2
    for boundary in boundaries.values():
        for substream in boundary.substreams:
            substream.verify(
                accepted.canonical.full_field.receipt_registry
            )
            assert all(
                tuple(
                    getattr(field, name)
                    for name in DSF_FIELD_ORDER
                ) == field.as_tuple()
                and len(field.as_tuple()) == 7
                for field in (
                    substream.kernel_basin.exact_dsf_field_tuples
                )
            )

    side = accepted.side.full_field
    assert side.joint_input.vertex_ids == tuple(
        value.vertex_id
        for value in accepted.side.vertex_provenance
    )
    assert side.joint_input.groups == ((0, 1), (2, 3), (4, 5))
    assert len(side.L0.frames) == (
        accepted.raw_encounter.capture.capture_sample_count
    )
    assert all(
        len(getattr(side.L4, name)) == len(side.L0.frames)
        for name in (
            "D_k",
            "M_k",
            "R_rev_k",
            "U_star_k",
            "C_k",
            "P_k",
            "B_k",
        )
    )
    first_raw = side.L0.frames[0].raw_vector
    assert first_raw[:2] == (
        Fraction(signed_pcm16_samples(
            accepted.raw_encounter.capture.left_pcm_s16le
        )[0]),
        Fraction(signed_pcm16_samples(
            accepted.raw_encounter.capture.right_pcm_s16le
        )[0]),
    )
    assert first_raw[2:] == tuple(
        value.signal[0]
        for value in accepted.raw_encounter.nonauditory_channels
    )


def test_common_boundary_rejects_branch_substitution():
    harness, accepted = _accept()
    changed_side = replace(
        accepted.side,
        raw_encounter_receipt_sha256="0" * 64,
    )
    changed = replace(
        accepted,
        kernel_fields=(accepted.canonical, changed_side),
    )

    with pytest.raises(
        ValueError,
        match="common boundary changed its authority",
    ):
        harness.verify(changed, recompute_branches=False)


def test_nonauditory_value_must_cross_canonical_intake_losslessly():
    _harness, capture, channels = _fixture()

    with pytest.raises(
        ValueError,
        match="not lossless at the canonical binary64 intake",
    ):
        replace(
            channels[0],
            signal=(Fraction(1, 3),) * capture.capture_sample_count,
        )
