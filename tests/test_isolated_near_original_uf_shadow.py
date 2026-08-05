from __future__ import annotations

import numpy as np

from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    REQUIRED_SAMPLE_RATE_HZ,
    transduce_auditory_full_field,
)
from tools.isolated_near_original_uf_shadow import (
    FIELD_WIDTH,
    PHYSICAL_EDGES,
    build_shadow_experience,
    relate,
)


def _tone(frequency: int, *, gain: float = 1.0) -> np.ndarray:
    time = np.arange(1_600, dtype=np.float64) / REQUIRED_SAMPLE_RATE_HZ
    return gain * 0.25 * np.sin(2.0 * np.pi * frequency * time)


def _experience(name: str, signal: np.ndarray):
    capture = transduce_auditory_full_field(
        signal,
        sample_rate_hz=REQUIRED_SAMPLE_RATE_HZ,
    )
    return build_shadow_experience(item_id=name, capture=capture)


def test_shadow_preserves_joint_field_and_all_projection_receipts():
    experience = _experience("tone-440", _tone(440))

    experience.verify()
    assert experience.scales == (1, 2, 4, 8)
    assert len(PHYSICAL_EDGES) == 156
    assert all(
        len(field.D_k) == FIELD_WIDTH
        and len(field.M_k) == FIELD_WIDTH
        and len(field.R_rev_k) == FIELD_WIDTH
        and len(field.U_star_k) == FIELD_WIDTH
        and len(field.P_k) == FIELD_WIDTH
        and len(field.B_k) == FIELD_WIDTH
        and len(field.C_k) == len(PHYSICAL_EDGES)
        and len(field.projection_receipts) == 8
        for scale_fields in experience.l4_by_scale
        for field in scale_fields
    )


def test_common_gain_is_removed_without_erasing_raw_custody():
    first = _experience("tone-gain-one", _tone(440, gain=1.0))
    scaled = _experience("tone-gain-half", _tone(440, gain=0.5))

    assert first.authority_receipt_sha256 != scaled.authority_receipt_sha256
    assert relate(first, scaled)["relation_locked"] is True


def test_distinct_tones_do_not_become_identical_experiences():
    first = _experience("tone-440", _tone(440))
    changed = _experience("tone-880", _tone(880))

    assert first.authority_receipt_sha256 != changed.authority_receipt_sha256
    assert any(
        left.authority_receipt_sha256
        != right.authority_receipt_sha256
        for left_scale, right_scale in zip(
            first.l4_by_scale, changed.l4_by_scale
        )
        for left, right in zip(left_scale, right_scale)
    )
