"""Exact correctness proofs for incremental GLEW receipt-registry helpers.

Every helper must append only genuinely new records while preserving the
digest-to-payload contents of the original reconstruct-and-sort behavior.
Digest collisions carrying different bytes must still fail closed.

The former CleanConversation per-turn performance case is intentionally absent:
that case depended on the retired typed-semantic conversation fixture. The
registry correctness and collision proofs remain authoritative.
"""

from __future__ import annotations

import hashlib
from unittest import mock

import pytest

import dsf_ai_service.glew_runtime.model as model_mod
from dsf_ai_service.glew_runtime import (
    clean_conversation_engine,
    coexperienced_scene_recall_executor,
    fresh_recall_executor,
    heterogeneous_l6,
    live_boundary_episode_adapter,
    production_runtime_bootstrap,
    real_experience_learning_pipeline,
    recall_replay_integrity_provider,
    recall_story_runtime_resolver,
    sensor_port_authority_mount,
    six_lane_runtime_mount,
)
from dsf_ai_service.glew_runtime.model import (
    ReceiptError,
    ReceiptRecord,
    ReceiptRegistry,
    receipt_sha256,
)


def _payload(tag: str, seq: int) -> bytes:
    return b'{"schema":"test.receipt.extend.v1","seq":%d,"tag":"%s"}' % (
        seq,
        tag.encode(),
    )


def _base(records: int, tag: str) -> ReceiptRegistry:
    return ReceiptRegistry.from_payloads(
        profile_payload=_payload(f"{tag}-profile", -1),
        receipt_payloads=[_payload(tag, i) for i in range(records)],
    )


def _rec(payload: bytes) -> ReceiptRecord:
    return ReceiptRecord(receipt_sha256(payload), payload)


def _apply(mapping: dict[str, bytes], payloads) -> dict[str, bytes]:
    """Return the original reconstruct-and-sort helper's exact set semantics."""

    merged = dict(mapping)
    for payload in payloads:
        digest = receipt_sha256(payload)
        existing = merged.get(digest)
        if existing is not None and existing != payload:
            raise ReceiptError("oracle collision")
        merged[digest] = payload
    return merged


def _mapping(registry: ReceiptRegistry) -> dict[str, bytes]:
    return {record.digest: record.payload for record in registry.records}


_PAYLOAD_HELPERS = [
    (
        "clean_conversation_engine._extend_registry",
        lambda reg, ps: clean_conversation_engine._extend_registry(reg, *ps),
        clean_conversation_engine,
    ),
    (
        "coexperienced_scene_recall_executor._extend_registry",
        lambda reg, ps: coexperienced_scene_recall_executor._extend_registry(reg, *ps),
        coexperienced_scene_recall_executor,
    ),
    (
        "real_experience_learning_pipeline._extend",
        lambda reg, ps: real_experience_learning_pipeline._extend(reg, *ps),
        real_experience_learning_pipeline,
    ),
    (
        "production_runtime_bootstrap._extend_registry",
        lambda reg, ps: production_runtime_bootstrap._extend_registry(reg, *ps),
        production_runtime_bootstrap,
    ),
    (
        "live_boundary_episode_adapter._extend_receipt_registry",
        lambda reg, ps: live_boundary_episode_adapter._extend_receipt_registry(reg, *ps),
        live_boundary_episode_adapter,
    ),
    (
        "sensor_port_authority_mount._extend_receipt_registry",
        lambda reg, ps: sensor_port_authority_mount._extend_receipt_registry(reg, *ps),
        sensor_port_authority_mount,
    ),
    (
        "six_lane_runtime_mount.extend_receipt_registry",
        lambda reg, ps: six_lane_runtime_mount.extend_receipt_registry(reg, *ps),
        six_lane_runtime_mount,
    ),
    (
        "recall_replay_integrity_provider._extend_payloads",
        lambda reg, ps: recall_replay_integrity_provider._extend_payloads(reg, tuple(ps)),
        recall_replay_integrity_provider,
    ),
    (
        "heterogeneous_l6._extend_registry",
        lambda reg, ps: heterogeneous_l6._extend_registry(reg, payloads=tuple(ps)),
        heterogeneous_l6,
    ),
]

_RECORD_HELPERS = [
    (
        "fresh_recall_executor._extend_records",
        lambda reg, recs: fresh_recall_executor._extend_records(reg, tuple(recs)),
        fresh_recall_executor,
    ),
    (
        "recall_story_runtime_resolver._extend_records",
        lambda reg, recs: recall_story_runtime_resolver._extend_records(reg, tuple(recs)),
        recall_story_runtime_resolver,
    ),
]

_PAYLOAD_IDS = [helper[0] for helper in _PAYLOAD_HELPERS]
_RECORD_IDS = [helper[0] for helper in _RECORD_HELPERS]


@pytest.mark.parametrize("label,fn,mod", _PAYLOAD_HELPERS, ids=_PAYLOAD_IDS)
def test_payload_helper_contents_match_original_and_are_incremental(label, fn, mod):
    base = _base(6, "corr")
    existing = [record.payload for record in base.records]
    fresh = [_payload("corr-new", index) for index in range(3)]
    batch = [*fresh, existing[0], existing[3], fresh[0]]

    result = fn(base, batch)
    assert isinstance(result, ReceiptRegistry)
    assert result.profile_binding_sha256 == base.profile_binding_sha256
    assert _mapping(result) == _apply(_mapping(base), batch)
    assert len(result.records) == len(_mapping(result)) == len(base.records) + 3
    for record in base.records:
        assert result.resolve(record.digest) == record.payload

    registry = base
    cumulative = _mapping(base)
    for step in range(12):
        step_batch = [
            _payload(f"corr-s{step}", index) for index in range(4)
        ] + [existing[0]]
        registry = fn(registry, step_batch)
        cumulative = _apply(cumulative, step_batch)
        assert _mapping(registry) == cumulative
    assert len(registry.records) == len(base.records) + 48


@pytest.mark.parametrize("label,fn,mod", _RECORD_HELPERS, ids=_RECORD_IDS)
def test_record_helper_contents_match_original_and_are_incremental(label, fn, mod):
    base = _base(6, "reccorr")
    existing = [record.payload for record in base.records]
    fresh = [_payload("reccorr-new", index) for index in range(3)]
    batch_payloads = [*fresh, existing[0], existing[3], fresh[0]]

    result = fn(base, [_rec(payload) for payload in batch_payloads])
    assert result.profile_binding_sha256 == base.profile_binding_sha256
    assert _mapping(result) == _apply(_mapping(base), batch_payloads)
    assert len(result.records) == len(base.records) + 3
    for record in base.records:
        assert result.resolve(record.digest) == record.payload

    registry = base
    cumulative = _mapping(base)
    for step in range(12):
        step_payloads = [
            _payload(f"reccorr-s{step}", index) for index in range(4)
        ] + [existing[0]]
        registry = fn(registry, [_rec(payload) for payload in step_payloads])
        cumulative = _apply(cumulative, step_payloads)
        assert _mapping(registry) == cumulative
    assert len(registry.records) == len(base.records) + 48


def _colliding_hash(poison: bytes, forced_digest: str):
    """Force one otherwise-infeasible SHA-256 collision for guard testing."""

    def _hash(payload: bytes) -> str:
        if payload == poison:
            return forced_digest
        return hashlib.sha256(payload).hexdigest()

    return _hash


@pytest.mark.parametrize("label,fn,mod", _PAYLOAD_HELPERS, ids=_PAYLOAD_IDS)
def test_payload_helper_digest_collision_still_raises(label, fn, mod):
    base = _base(4, "collide")
    target = base.records[1]
    poison = b'{"schema":"test.receipt.extend.v1","poison":true}'
    assert poison != target.payload

    with mock.patch.object(mod, "receipt_sha256", _colliding_hash(poison, target.digest)):
        with pytest.raises(ReceiptError, match="colli"):
            fn(base, [poison])


@pytest.mark.parametrize("label,fn,mod", _RECORD_HELPERS, ids=_RECORD_IDS)
def test_record_helper_digest_collision_still_raises(label, fn, mod):
    base = _base(4, "reccollide")
    target = base.records[1]
    poison = b'{"schema":"test.receipt.extend.v1","poison":true}'
    assert poison != target.payload

    with mock.patch.object(
        model_mod,
        "receipt_sha256",
        _colliding_hash(poison, target.digest),
    ):
        poison_record = ReceiptRecord(target.digest, poison)
    assert poison_record.digest == target.digest
    assert poison_record.payload == poison

    with pytest.raises(ReceiptError, match="colli"):
        fn(base, [poison_record])
