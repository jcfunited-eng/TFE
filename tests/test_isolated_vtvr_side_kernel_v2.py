from __future__ import annotations

from fractions import Fraction

from tools.isolated_vtvr_side_kernel_v2 import (
    JointFieldInput,
    run_side_kernel,
    structural_relation,
)


VERTICES = (
    "left-low",
    "left-high",
    "right-low",
    "right-high",
)
GROUPS = ((0, 1, 2, 3),)
TIMES = tuple(Fraction(index, 100) for index in range(6))
BASE = (
    (0, 0, 0, 0),
    (1, 0, 0, 0),
    (3, 1, 1, 0),
    (1, 3, 3, 1),
    (0, 1, 1, 3),
    (0, 0, 0, 1),
)


def _input(vectors) -> JointFieldInput:
    return JointFieldInput.create(
        vertex_ids=VERTICES,
        groups=GROUPS,
        times=TIMES,
        vectors=vectors,
    )


def test_vtvr_is_one_joint_field_and_is_byte_deterministic():
    first = run_side_kernel(_input(BASE))
    second = run_side_kernel(_input(BASE))

    first.verify()
    assert first == second
    assert first.authority_receipt_sha256 == (
        second.authority_receipt_sha256
    )
    assert len(first.L0.frames[0].vector) == 4
    assert len(first.L0.frames[0].relation) == 6
    assert len(first.L1.vector) == len(TIMES)
    assert len(first.L1.time) == len(TIMES)
    assert len(first.L1.volume) == len(TIMES)
    assert len(first.L1.relation) == len(TIMES)
    assert len(first.L4.C_k[0]) == 6


def test_common_positive_gain_changes_raw_custody_not_vtvr_structure():
    base = run_side_kernel(_input(BASE))
    gained = run_side_kernel(_input(tuple(
        tuple(7 * value for value in vector)
        for vector in BASE
    )))

    assert (
        base.joint_input.raw_authority_receipt_sha256
        != gained.joint_input.raw_authority_receipt_sha256
    )
    assert structural_relation(base, gained) is True
    assert base.L1 == gained.L1


def test_interaural_delay_remains_visible_in_relation_dimension():
    base = run_side_kernel(_input(BASE))
    delayed_vectors = tuple(
        (
            vector[0],
            vector[1],
            0 if index == 0 else BASE[index - 1][2],
            0 if index == 0 else BASE[index - 1][3],
        )
        for index, vector in enumerate(BASE)
    )
    delayed = run_side_kernel(_input(delayed_vectors))

    assert structural_relation(base, delayed) is False
    assert base.L1.relation != delayed.L1.relation
    assert any(
        fact.oriented_area != 0
        for frame in delayed.L1.relation
        for fact in frame
    )


def test_genuinely_different_waveform_does_not_share_vtvr_structure():
    base = run_side_kernel(_input(BASE))
    different = run_side_kernel(_input((
        (0, 0, 0, 0),
        (0, 1, 0, 1),
        (1, 3, 1, 3),
        (3, 1, 3, 1),
        (1, 0, 1, 0),
        (0, 0, 0, 0),
    )))

    assert structural_relation(base, different) is False
    assert base.L1.vector != different.L1.vector
    assert base.L1.volume != different.L1.volume
    assert base.L1.relation != different.L1.relation
