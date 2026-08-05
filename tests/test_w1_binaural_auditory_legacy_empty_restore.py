"""Exact migration wall for the production W1 auditory v1 state."""

from __future__ import annotations

import hashlib
import json

import pytest

from dsf_ai_service.substrate.w1_binaural_auditory_l5 import (
    LEGACY_EMPTY_W1_BINAURAL_AUDITORY_L5_STATE_SCHEMA,
    W1_BINAURAL_AUDITORY_L5_STATE_SCHEMA,
    W1BinauralAuditoryL5Owner,
)


TRANSITION_CAPACITY = 1_024


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _legacy_record(
    *,
    generation: int,
    latest: object,
    settled: int,
    transitions: list[object],
) -> bytes:
    payload = {
        "generation": generation,
        "latest": latest,
        "schema": LEGACY_EMPTY_W1_BINAURAL_AUDITORY_L5_STATE_SCHEMA,
        "settled": settled,
        "transition_capacity": TRANSITION_CAPACITY,
        "transitions": transitions,
    }
    return _canonical({
        "payload": payload,
        "state_receipt_sha256": hashlib.sha256(
            _canonical(payload)
        ).hexdigest(),
    })


def test_authenticated_empty_production_v1_state_enters_v2_exactly() -> None:
    owner = W1BinauralAuditoryL5Owner(
        max_transitions=TRANSITION_CAPACITY,
    )

    owner.restore_encoded(_legacy_record(
        generation=0,
        latest=None,
        settled=0,
        transitions=[],
    ))

    restored = json.loads(owner.encoded_snapshot())
    assert restored["payload"]["schema"] == (
        W1_BINAURAL_AUDITORY_L5_STATE_SCHEMA
    )
    assert restored["payload"]["generation"] == 0
    assert restored["payload"]["settled"] == 0
    assert restored["payload"]["latest"] is None
    assert restored["payload"]["transitions"] == []


def test_nonempty_v1_state_is_rejected_without_inventing_causal_depth() -> None:
    owner = W1BinauralAuditoryL5Owner(
        max_transitions=TRANSITION_CAPACITY,
    )

    with pytest.raises(
        ValueError,
        match="lacks exact causal intervals",
    ):
        owner.restore_encoded(_legacy_record(
            generation=1,
            latest={"legacy": "field-without-causal-intervals"},
            settled=1,
            transitions=[],
        ))

    assert owner.status()["settled"] == 0
    assert owner.latest is None
