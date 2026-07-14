"""Real, non-monkeypatched proof that every receipt-registry extend helper in
``dsf_ai_service/glew_runtime/`` is now incremental (append-only), amortized
O(new records) rather than O(total records) per call.

Background: a family of sibling ``_extend*``/``_merge*`` helpers rebuilt the
ENTIRE accumulated registry on every extend --
``tuple(ReceiptRecord(d, values[d]) for d in sorted(values))`` -- which
reconstructs every already-validated ``ReceiptRecord`` and therefore re-runs a
full SHA-256 over every accumulated payload (``ReceiptRecord.__post_init__``)
on every call. The already-proven fix (already live in
``expression_learning._extend_registry`` and the ``*_provider`` modules) copies
``list(registry.records)``, keeps a ``{digest: payload}`` map purely for O(1)
collision detection, and APPENDS only genuinely-new records -- never
reconstructing/rehashing/resorting the ones already held.

This module proves, for every fixed helper:
  (a) correctness -- the final registry's (digest -> payload) contents are
      byte-identical to what the original reconstruct+rehash+resort
      implementation would have produced, across a mix of new, duplicate, and
      repeated-within-batch payloads, single- and multi-call;
  (b) collision safety -- a digest that collides with an existing digest but
      carries DIFFERENT bytes still raises, exactly as before;
  (c) performance -- driving 40 real turns through the real
      ``ProductionCleanConversationEngine`` shows per-turn cost plateaus as the
      threaded registry grows several-fold, instead of climbing with it.
"""

from __future__ import annotations

import hashlib
import statistics
import time
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

# Reuse the real, non-monkeypatched engine fixture and its harness helpers
# (real MountedSixLaneRuntime + real LearnedBindingState, nothing faked).
from tests.glew_runtime.test_clean_conversation_engine import (  # noqa: F401
    fixture,
    _build_engine,
    _mount_test_chemistry_runtime,
    _new_generation_store,
    _turn,
)


# --------------------------------------------------------------------------- #
# payload / registry builders                                                 #
# --------------------------------------------------------------------------- #
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
    """The ORIGINAL reconstruct+rehash+resort helper's exact set semantics,
    expressed as a digest->payload mapping (the buggy implementation's record
    order differed only by sort; its contents are exactly this mapping)."""

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


# --------------------------------------------------------------------------- #
# helper registry: (label, callable(registry, payloads)->ReceiptRegistry, mod) #
# --------------------------------------------------------------------------- #
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

_PAYLOAD_IDS = [h[0] for h in _PAYLOAD_HELPERS]
_RECORD_IDS = [h[0] for h in _RECORD_HELPERS]


# --------------------------------------------------------------------------- #
# (a) correctness                                                             #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("label,fn,mod", _PAYLOAD_HELPERS, ids=_PAYLOAD_IDS)
def test_payload_helper_contents_match_original_and_are_incremental(label, fn, mod):
    base = _base(6, "corr")
    existing = [record.payload for record in base.records]
    fresh = [_payload("corr-new", k) for k in range(3)]
    # A mix that exercises every branch: genuinely-new payloads, duplicates of
    # already-mounted receipts (same bytes -> dedup, never raise), and a
    # payload repeated within the same batch.
    batch = [*fresh, existing[0], existing[3], fresh[0]]

    result = fn(base, batch)
    assert isinstance(result, ReceiptRegistry)
    assert result.profile_binding_sha256 == base.profile_binding_sha256

    # Byte-identical contents to the original reconstruct+rehash implementation.
    assert _mapping(result) == _apply(_mapping(base), batch)
    # No duplicate digests, exactly the unique count (3 new added to 7 held).
    assert len(result.records) == len(_mapping(result)) == len(base.records) + 3
    # Every previously-mounted receipt is preserved and still resolves.
    for record in base.records:
        assert result.resolve(record.digest) == record.payload

    # Many sequential extends stay byte-identical to the cumulative original.
    reg = base
    cumulative = _mapping(base)
    for step in range(12):
        step_batch = [_payload(f"corr-s{step}", k) for k in range(4)] + [existing[0]]
        reg = fn(reg, step_batch)
        cumulative = _apply(cumulative, step_batch)
        assert _mapping(reg) == cumulative
    # 12 calls * 4 unique-new each = 48 additions, plus the original 7.
    assert len(reg.records) == len(base.records) + 48


@pytest.mark.parametrize("label,fn,mod", _RECORD_HELPERS, ids=_RECORD_IDS)
def test_record_helper_contents_match_original_and_are_incremental(label, fn, mod):
    base = _base(6, "reccorr")
    existing = [record.payload for record in base.records]
    fresh = [_payload("reccorr-new", k) for k in range(3)]
    batch_payloads = [*fresh, existing[0], existing[3], fresh[0]]

    result = fn(base, [_rec(p) for p in batch_payloads])
    assert result.profile_binding_sha256 == base.profile_binding_sha256
    assert _mapping(result) == _apply(_mapping(base), batch_payloads)
    assert len(result.records) == len(base.records) + 3
    for record in base.records:
        assert result.resolve(record.digest) == record.payload

    reg = base
    cumulative = _mapping(base)
    for step in range(12):
        step_payloads = [_payload(f"reccorr-s{step}", k) for k in range(4)] + [existing[0]]
        reg = fn(reg, [_rec(p) for p in step_payloads])
        cumulative = _apply(cumulative, step_payloads)
        assert _mapping(reg) == cumulative
    assert len(reg.records) == len(base.records) + 48


# --------------------------------------------------------------------------- #
# (b) collision safety                                                        #
# --------------------------------------------------------------------------- #
def _colliding_hash(poison: bytes, forced_digest: str):
    """A hash that returns ``forced_digest`` for ``poison`` and the real
    SHA-256 for everything else -- used ONLY to simulate an otherwise-
    infeasible SHA-256 collision and thereby exercise the defensive
    digest-collides-with-different-bytes branch. It never fakes the engine's
    cognition; it forces a single input to collide with an already-mounted
    receipt so the guard has something to reject."""

    def _hash(payload: bytes) -> str:
        if payload == poison:
            return forced_digest
        return hashlib.sha256(payload).hexdigest()

    return _hash


@pytest.mark.parametrize("label,fn,mod", _PAYLOAD_HELPERS, ids=_PAYLOAD_IDS)
def test_payload_helper_digest_collision_still_raises(label, fn, mod):
    base = _base(4, "collide")
    target = base.records[1]  # a genuine, already-mounted receipt
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

    # Build a ReceiptRecord whose declared digest collides with an existing one
    # but whose bytes differ, by forcing the collision only while its own
    # __post_init__ validates it.
    with mock.patch.object(model_mod, "receipt_sha256", _colliding_hash(poison, target.digest)):
        poison_record = ReceiptRecord(target.digest, poison)
    assert poison_record.digest == target.digest
    assert poison_record.payload == poison

    with pytest.raises(ReceiptError, match="colli"):
        fn(base, [poison_record])


# --------------------------------------------------------------------------- #
# (c) performance -- real engine, real turns                                  #
# --------------------------------------------------------------------------- #
def test_engine_per_turn_cost_plateaus_as_threaded_registry_grows(
    fixture, tmp_path_factory
):
    """Drive 40 real turns through the real ``ProductionCleanConversationEngine``
    (genesis learned-state: every turn honestly runs the full sensory/
    expression/recognition pipeline and threads+grows ``self._registry``).

    With the O(n)-per-extend rehash removed, per-turn wall-clock cost plateaus:
    two post-warmup windows measured at registry sizes that differ ~2x are
    within a small factor of each other. The original reconstruct+rehash+resort
    helpers instead made per-turn cost climb monotonically with the registry.
    """

    engine = _build_engine(
        mounted_runtime=fixture["mounted_runtime"],
        learned_state=fixture["genesis"],
        registry=fixture["registry"],
        generation_store=_new_generation_store(tmp_path_factory),
    )
    chemistry = _mount_test_chemistry_runtime()

    per_turn: list[float] = []
    sizes: list[int] = []
    for i in range(40):
        turn = _turn(f"registry-extend-perf-turn-{i}", "a")
        started = time.perf_counter()
        engine.run_clean_conversation(turn=turn, story_chemistry=chemistry)
        per_turn.append(time.perf_counter() - started)
        sizes.append(len(engine._registry.records))

    # The threaded registry genuinely grew several-fold across the run, so this
    # really exercises the large-registry regime.
    assert sizes[-1] >= sizes[0] * 3
    # Two post-warmup windows, taken where the registry has roughly doubled.
    assert sizes[-1] >= sizes[10] * 2
    warm = statistics.median(per_turn[15:22])
    late = statistics.median(per_turn[-7:])
    # Plateau: later (much larger registry) turns are not dramatically slower.
    assert late <= warm * 1.8, (
        f"per-turn cost climbed with registry size: warm={warm:.4f}s "
        f"(reg~{sizes[18]}) late={late:.4f}s (reg~{sizes[-1]}); "
        f"per_turn={per_turn}"
    )
    # Absolute sanity: no turn regressed into the multi-second regime.
    assert max(per_turn) < 5.0
