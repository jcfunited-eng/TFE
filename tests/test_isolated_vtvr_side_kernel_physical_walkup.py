from __future__ import annotations

from fractions import Fraction

from dsf_ai_service.substrate.w1_binaural_acoustic_physics import (
    pcm16_bytes,
    signed_pcm16_samples,
)
from tools.isolated_vtvr_side_kernel_v2 import (
    JointFieldInput,
    run_side_kernel,
    structural_relation,
)
from tools.isolated_w1_physical_stereo_path import (
    PhysicalStereoAuditAuthority,
)


AUTHORITY = PhysicalStereoAuditAuthority(
    authority_key=b"isolated-vtvr-physical-walkup-authority-v1"
)
SAMPLE_RATE_HZ = 16_000


def _triangle(*, period: int, count: int = 512) -> tuple[int, ...]:
    quarter = period // 4
    if period < 8 or period % 4:
        raise ValueError("triangle period must contain four exact quarters")
    values = []
    for index in range(count):
        phase = index % period
        if phase < quarter:
            ordinate = phase
        elif phase < 3 * quarter:
            ordinate = 2 * quarter - phase
        else:
            ordinate = phase - period
        values.append(ordinate * 64)
    return tuple(values)


def _experience(
    samples: tuple[int, ...],
    *,
    source_ordinal: int,
):
    capture = AUTHORITY.render(
        (pcm16_bytes(samples),),
        source_ordinals=(source_ordinal,),
    )
    left = signed_pcm16_samples(capture.left_pcm_s16le)
    right = signed_pcm16_samples(capture.right_pcm_s16le)
    joint_input = JointFieldInput.create(
        vertex_ids=("left-ear-pressure", "right-ear-pressure"),
        groups=((0, 1),),
        times=tuple(
            Fraction(index, SAMPLE_RATE_HZ)
            for index in range(capture.capture_sample_count)
        ),
        vectors=tuple(zip(left, right, strict=True)),
    )
    return capture, run_side_kernel(joint_input)


def test_physical_binaural_tone_walkup():
    source = _triangle(period=32)
    replay_capture, replay = _experience(source, source_ordinal=0)
    repeated_capture, repeated = _experience(source, source_ordinal=0)

    assert replay_capture == repeated_capture
    assert replay == repeated
    assert structural_relation(replay, repeated) is True

    gained_capture, gained = _experience(
        tuple(value * 3 for value in source),
        source_ordinal=0,
    )
    assert (
        replay_capture.authority_receipt_sha256
        != gained_capture.authority_receipt_sha256
    )
    assert (
        replay.joint_input.raw_authority_receipt_sha256
        != gained.joint_input.raw_authority_receipt_sha256
    )
    assert structural_relation(replay, gained) is True

    mirrored_capture, mirrored = _experience(source, source_ordinal=1)
    assert replay_capture.paths != mirrored_capture.paths
    assert structural_relation(replay, mirrored) is False
    assert replay.L1.relation != mirrored.L1.relation

    different_capture, different = _experience(
        _triangle(period=40),
        source_ordinal=0,
    )
    assert (
        replay_capture.authority_receipt_sha256
        != different_capture.authority_receipt_sha256
    )
    assert structural_relation(replay, different) is False
