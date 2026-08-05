from __future__ import annotations

import hashlib
import json

from dsf_ai_service.substrate.w1_anonymous_spatial_vocal_relation import (
    W1AnonymousSpatialVocalDistinction,
    W1AnonymousSpatialVocalRelation,
    W1RecurrentQTemporalFeature,
)


MAX_RECORD_BYTES = 64 * 1024 * 1024
MAX_FEATURES_PER_RELATION = 24_192


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _relation(
    *,
    relation_index: int,
    positives: tuple[str, ...],
    contrasts: tuple[str, ...],
) -> W1AnonymousSpatialVocalRelation:
    return W1AnonymousSpatialVocalRelation(
        signed_displacement=(0, -200 + 400 * relation_index, 0, 0),
        before_pose_sha256=_sha("before-pose"),
        diagnostic_features=tuple(
            W1RecurrentQTemporalFeature(
                ear_id=("left" if index % 2 == 0 else "right"),
                neuron_id=_sha(
                    f"relation-{relation_index}-feature-{index}"
                ),
                positive_activation_witness_receipt_sha256s=tuple(
                    (_sha(f"{receipt}-activation-{index}"),)
                    for receipt in positives
                ),
            )
            for index in range(MAX_FEATURES_PER_RELATION)
        ),
        positive_lesson_receipt_sha256s=positives,
        contrast_lesson_receipt_sha256s=contrasts,
    )


def test_maximum_relation_record_is_receipt_scale_and_bounded():
    first = tuple(_sha(f"lesson-a-{index}") for index in range(6))
    second = tuple(_sha(f"lesson-b-{index}") for index in range(6))
    distinction = W1AnonymousSpatialVocalDistinction(
        distinction_id="0" * 64,
        q_state_sha256=_sha("q-state"),
        relations=(
            _relation(
                relation_index=0,
                positives=first,
                contrasts=second,
            ),
            _relation(
                relation_index=1,
                positives=second,
                contrasts=first,
            ),
        ),
        source_lesson_receipt_sha256s=tuple(sorted(first + second)),
        authority_hmac_sha256="0" * 64,
        authority_receipt_sha256="0" * 64,
    )

    encoded = json.dumps(
        distinction.payload(),
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()

    assert len(encoded) < MAX_RECORD_BYTES
    assert b"activation_json" not in encoded
    assert b"full_dynamic_roots" not in encoded
    assert len(distinction.relations[0].diagnostic_features) == (
        MAX_FEATURES_PER_RELATION
    )
