"""Detached streaming causal-generation authority proofs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tracemalloc

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dsf_ai_service.substrate.generation_content_delta import (
    DETACHED_CAUSAL_MUTATION_MEMBER_PATH,
    GenerationContentDeltaError,
    STREAM_READ_BYTES,
    census_generation_content_delta,
    prepare_causal_mutation_manifest_member,
    validate_causal_mutation_manifest_member,
)
from dsf_ai_service.substrate.immutable_generation_store import (
    ImmutableGenerationStore,
)
from dsf_ai_service.substrate.owner_scoped_persistence import (
    issue_owner_state_snapshot_receipt,
)


IDENTITY = "generation-content-delta-proof"
HMAC_KEY = b"generation-content-delta-proof-key-material"
OWNER_KEY = b"owner-state-snapshot-proof-key-material"
LEARNED_A = "guala_visual.json"
LEARNED_B = "guala_sight_motifs.json"
CHECKPOINT = "guala_runtime_config.json"
MEMBER = DETACHED_CAUSAL_MUTATION_MEMBER_PATH
REQUIRED = (LEARNED_A, LEARNED_B, CHECKPOINT, MEMBER)
PRODUCTION_ESCROW_BYTES = 640_118_634


def _encoded(value) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _content(
    *,
    causal_value: str,
    thing_value: str,
    checkpoint_tick: int,
) -> dict[str, bytes]:
    return {
        LEARNED_A: _encoded({
            "schema": "test.causal_state.v1",
            "value": causal_value,
        }),
        LEARNED_B: _encoded({
            "schema": "test.thing_state.v1",
            "value": thing_value,
        }),
        CHECKPOINT: _encoded({
            "schema": "test.checkpoint_receipt.v1",
            "tick": checkpoint_tick,
        }),
    }


def _write_stage(root: Path, content: dict[str, bytes]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for relative, value in content.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(value)


def _authorities(content: dict[str, bytes], *paths: str):
    return {
        path: issue_owner_state_snapshot_receipt(
            identity=IDENTITY,
            relative_path=path,
            body_sha256=hashlib.sha256(content[path]).hexdigest(),
            body_bytes=len(content[path]),
            mutation_root_sha256=hashlib.sha256(
                ("mutation-root:" + path).encode("utf-8")
            ).hexdigest(),
            frozen_tick=2,
            authority_key=OWNER_KEY,
        )
        for path in paths
    }


def _store(tmp_path: Path):
    store = ImmutableGenerationStore(
        tmp_path / "store",
        identity=IDENTITY,
        required_files=REQUIRED,
        content_addressed=True,
    )
    baseline = store.commit(
        tick=1,
        files=_content(
            causal_value="first",
            thing_value="first",
            checkpoint_tick=1,
        ) | {
            MEMBER: _encoded({
                "schema": "guala.causal_generation_genesis.v1",
            }),
        },
    )
    return store, baseline


def _commit_candidate(
    tmp_path: Path,
    store,
    baseline,
    *,
    content: dict[str, bytes],
    authorities,
):
    stage = tmp_path / "candidate-stage"
    _write_stage(stage, content)
    member = prepare_causal_mutation_manifest_member(
        baseline,
        candidate_stage_root=stage,
        candidate_relative_paths=tuple(content),
        candidate_tick=2,
        path_authorities=authorities,
        owner_snapshot_authority_key=OWNER_KEY,
        hmac_key=HMAC_KEY,
    )
    _write_stage(stage, {MEMBER: member})
    candidate = store.commit(
        tick=2,
        files={
            relative: (stage / relative).read_bytes()
            for relative in REQUIRED
        },
        publish_current=False,
    )
    return member, candidate


def test_detached_member_is_durable_sealed_and_path_specific(
    tmp_path: Path,
) -> None:
    store, baseline = _store(tmp_path)
    content = _content(
        causal_value="second",
        thing_value="first",
        checkpoint_tick=2,
    )
    member, candidate = _commit_candidate(
        tmp_path,
        store,
        baseline,
        content=content,
        authorities=_authorities(content, LEARNED_A),
    )

    assert MEMBER in candidate.required_files
    assert candidate.stored_bytes(MEMBER) == member
    receipt = validate_causal_mutation_manifest_member(
        baseline,
        candidate,
        owner_snapshot_authority_key=OWNER_KEY,
        hmac_key=HMAC_KEY,
    )
    assert [
        value["relative_path"]
        for value in receipt["path_owner_snapshots"]
    ] == [LEARNED_A]
    assert receipt["path_owner_snapshots"][0][
        "candidate_sha256"
    ] == hashlib.sha256(content[LEARNED_A]).hexdigest()


def test_changed_paths_require_exact_individual_producers(
    tmp_path: Path,
) -> None:
    store, baseline = _store(tmp_path)
    content = _content(
        causal_value="second",
        thing_value="second",
        checkpoint_tick=2,
    )
    stage = tmp_path / "candidate-stage"
    _write_stage(stage, content)

    with pytest.raises(
        GenerationContentDeltaError,
        match="exactly cover changed learned paths",
    ):
        prepare_causal_mutation_manifest_member(
            baseline,
            candidate_stage_root=stage,
            candidate_relative_paths=tuple(content),
            candidate_tick=2,
            path_authorities=_authorities(content, LEARNED_A),
            owner_snapshot_authority_key=OWNER_KEY,
            hmac_key=HMAC_KEY,
        )

    member = prepare_causal_mutation_manifest_member(
        baseline,
        candidate_stage_root=stage,
        candidate_relative_paths=tuple(content),
        candidate_tick=2,
        path_authorities=_authorities(
            content,
            LEARNED_A,
            LEARNED_B,
        ),
        owner_snapshot_authority_key=OWNER_KEY,
        hmac_key=HMAC_KEY,
    )
    assert {
        value["relative_path"]
        for value in json.loads(member)["path_owner_snapshots"]
    } == {LEARNED_A, LEARNED_B}


def test_zero_learning_and_deleted_learning_are_exact(
    tmp_path: Path,
) -> None:
    store, baseline = _store(tmp_path)
    stable = _content(
        causal_value="first",
        thing_value="first",
        checkpoint_tick=2,
    )
    stage = tmp_path / "stable-stage"
    _write_stage(stage, stable)
    member = prepare_causal_mutation_manifest_member(
        baseline,
        candidate_stage_root=stage,
        candidate_relative_paths=tuple(stable),
        candidate_tick=2,
        path_authorities={},
        owner_snapshot_authority_key=OWNER_KEY,
        hmac_key=HMAC_KEY,
    )
    assert json.loads(member)["path_owner_snapshots"] == []
    candidate = store.commit(
        tick=2,
        files=stable | {MEMBER: member},
        publish_current=False,
    )
    validate_causal_mutation_manifest_member(
        baseline,
        candidate,
        owner_snapshot_authority_key=OWNER_KEY,
        hmac_key=HMAC_KEY,
    )
    delta = census_generation_content_delta(baseline, candidate)
    assert not {
        relative
        for chunk in delta.new_chunks
        for relative in chunk.relative_paths
    }.intersection((LEARNED_A, LEARNED_B))

    missing = dict(stable)
    missing.pop(LEARNED_B)
    missing_stage = tmp_path / "missing-stage"
    _write_stage(missing_stage, missing)
    with pytest.raises(
        GenerationContentDeltaError,
        match="forbids deleted learned paths",
    ):
        prepare_causal_mutation_manifest_member(
            baseline,
            candidate_stage_root=missing_stage,
            candidate_relative_paths=tuple(missing),
            candidate_tick=2,
            path_authorities={},
            owner_snapshot_authority_key=OWNER_KEY,
            hmac_key=HMAC_KEY,
        )


def test_forged_sealed_member_and_linked_stage_fail_closed(
    tmp_path: Path,
) -> None:
    store, baseline = _store(tmp_path)
    content = _content(
        causal_value="second",
        thing_value="first",
        checkpoint_tick=2,
    )
    stage = tmp_path / "candidate-stage"
    _write_stage(stage, content)
    member = prepare_causal_mutation_manifest_member(
        baseline,
        candidate_stage_root=stage,
        candidate_relative_paths=tuple(content),
        candidate_tick=2,
        path_authorities=_authorities(content, LEARNED_A),
        owner_snapshot_authority_key=OWNER_KEY,
        hmac_key=HMAC_KEY,
    )
    forged = json.loads(member)
    forged["path_owner_snapshots"][0][
        "owner_snapshot_receipt"
    ]["authority_hmac_sha256"] = "f" * 64
    candidate = store.commit(
        tick=2,
        files=content | {MEMBER: _encoded(forged)},
        publish_current=False,
    )
    with pytest.raises(
        GenerationContentDeltaError,
        match="authentication failed",
    ):
        validate_causal_mutation_manifest_member(
            baseline,
            candidate,
            owner_snapshot_authority_key=OWNER_KEY,
            hmac_key=HMAC_KEY,
        )

    linked_stage = tmp_path / "linked-stage"
    _write_stage(linked_stage, {
        LEARNED_A: content[LEARNED_A],
        CHECKPOINT: content[CHECKPOINT],
    })
    (linked_stage / LEARNED_B).symlink_to(
        stage / LEARNED_B
    )
    with pytest.raises(
        GenerationContentDeltaError,
        match="unavailable or linked",
    ):
        prepare_causal_mutation_manifest_member(
            baseline,
            candidate_stage_root=linked_stage,
            candidate_relative_paths=tuple(content),
            candidate_tick=2,
            path_authorities=_authorities(content, LEARNED_A),
            owner_snapshot_authority_key=OWNER_KEY,
            hmac_key=HMAC_KEY,
        )


def test_production_scale_escrow_is_hashed_with_bounded_memory(
    tmp_path: Path,
) -> None:
    _store_instance, baseline = _store(tmp_path)
    content = _content(
        causal_value="second",
        thing_value="first",
        checkpoint_tick=2,
    )
    stage = tmp_path / "production-scale-stage"
    _write_stage(stage, content)
    escrow = "legacy_cognition_archive/guala_deep_atlas.json"
    escrow_path = stage / escrow
    escrow_path.parent.mkdir(parents=True)
    with escrow_path.open("wb") as handle:
        handle.truncate(PRODUCTION_ESCROW_BYTES)

    tracemalloc.start()
    member = prepare_causal_mutation_manifest_member(
        baseline,
        candidate_stage_root=stage,
        candidate_relative_paths=(*content, escrow),
        candidate_tick=2,
        path_authorities=_authorities(content, LEARNED_A),
        owner_snapshot_authority_key=OWNER_KEY,
        hmac_key=HMAC_KEY,
    )
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    escrow_change = next(
        value
        for value in json.loads(member)["changed_files"]
        if value["relative_path"] == escrow
    )
    assert escrow_change["candidate_size_bytes"] == PRODUCTION_ESCROW_BYTES
    assert peak < STREAM_READ_BYTES * 4


def test_post_seal_census_includes_detached_member(
    tmp_path: Path,
) -> None:
    store, baseline = _store(tmp_path)
    content = _content(
        causal_value="second",
        thing_value="first",
        checkpoint_tick=2,
    )
    _member, candidate = _commit_candidate(
        tmp_path,
        store,
        baseline,
        content=content,
        authorities=_authorities(content, LEARNED_A),
    )
    delta = census_generation_content_delta(baseline, candidate)

    assert {
        value.relative_path for value in delta.changed_files
    } == {LEARNED_A, CHECKPOINT, MEMBER}
    assert delta.new_unique_content_bytes > 0
