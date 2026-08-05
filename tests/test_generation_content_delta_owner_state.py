from __future__ import annotations

import hashlib
import json
from pathlib import Path

from dsf_ai_service.substrate.generation_content_delta import (
    DETACHED_CAUSAL_MUTATION_MEMBER_PATH,
    census_generation_content_delta,
    prepare_causal_mutation_manifest_member,
    validate_causal_mutation_manifest_member,
)
from dsf_ai_service.substrate.immutable_generation_store import (
    ImmutableGenerationStore,
)
from dsf_ai_service.substrate.owner_scoped_persistence import (
    ACTIVE_OWNER_STATE_KEYS,
    OWNER_STATE_GROUPS,
    issue_owner_state_snapshot_receipt,
    owner_state_bodies,
    owner_state_body_mutation_root,
)


IDENTITY = "owner-state-content-delta-proof"
DELTA_KEY = b"owner-state-content-delta-proof-key-material"
OWNER_KEY = b"owner-state-snapshot-integration-proof-key"
MEMBER = DETACHED_CAUSAL_MUTATION_MEMBER_PATH
CONFIG = "guala_runtime_config.json"
OWNER_PATHS = tuple(
    group.relative_path for group in OWNER_STATE_GROUPS
)


def _write_stage(root: Path, files: dict[str, bytes]) -> None:
    root.mkdir(parents=True)
    for relative_path, body in files.items():
        target = root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)


def _genesis_bodies() -> dict[str, bytes]:
    return owner_state_bodies({
        key: None for key in ACTIVE_OWNER_STATE_KEYS
    })


def _baseline(tmp_path: Path):
    store = ImmutableGenerationStore(
        tmp_path / "store",
        identity=IDENTITY,
        required_files=(*OWNER_PATHS, CONFIG, MEMBER),
        content_addressed=True,
    )
    bodies = _genesis_bodies()
    baseline = store.commit(
        tick=1,
        files=bodies | {
            CONFIG: b'{"generation":1}',
            MEMBER: b'{"schema":"guala.causal_generation_genesis.v1"}',
        },
    )
    return store, baseline, bodies


def _sealed_candidate(
    tmp_path: Path,
    store,
    baseline,
    *,
    bodies: dict[str, bytes],
    authorities,
):
    content = bodies | {CONFIG: b'{"generation":1}'}
    stage = tmp_path / "stage"
    _write_stage(stage, content)
    member = prepare_causal_mutation_manifest_member(
        baseline,
        candidate_stage_root=stage,
        candidate_relative_paths=tuple(content),
        candidate_tick=2,
        path_authorities=authorities,
        owner_snapshot_authority_key=OWNER_KEY,
        hmac_key=DELTA_KEY,
    )
    candidate = store.commit(
        tick=2,
        files=content | {MEMBER: member},
        publish_current=False,
    )
    receipt = validate_causal_mutation_manifest_member(
        baseline,
        candidate,
        owner_snapshot_authority_key=OWNER_KEY,
        hmac_key=DELTA_KEY,
    )
    return candidate, receipt


def test_zero_owner_mutation_reuses_every_owner_body_chunk(
    tmp_path: Path,
) -> None:
    store, baseline, bodies = _baseline(tmp_path)
    candidate, receipt = _sealed_candidate(
        tmp_path,
        store,
        baseline,
        bodies=bodies,
        authorities={},
    )

    assert receipt["path_owner_snapshots"] == []
    assert all(
        baseline.stored_bytes(path) == candidate.stored_bytes(path)
        for path in OWNER_PATHS
    )
    delta = census_generation_content_delta(baseline, candidate)
    owner_chunk_paths = {
        relative_path
        for chunk in delta.new_chunks
        for relative_path in chunk.relative_paths
        if relative_path in OWNER_PATHS
    }
    assert owner_chunk_paths == set()
    changed_paths = {
        path
        for path in (*OWNER_PATHS, CONFIG, MEMBER)
        if baseline.stored_bytes(path) != candidate.stored_bytes(path)
    }
    assert changed_paths == {MEMBER}


def test_one_owner_mutation_changes_only_its_body_and_receipt(
    tmp_path: Path,
) -> None:
    store, baseline, bodies = _baseline(tmp_path)
    group = next(
        value
        for value in OWNER_STATE_GROUPS
        if value.owner_id == "whole_organism_reflection_monitor"
    )
    payload = {
        key: None for key in ACTIVE_OWNER_STATE_KEYS
    }
    payload[group.state_keys[0]] = {
        group.mutation_root_field: "a" * 64,
    }
    changed_bodies = owner_state_bodies(payload)
    changed_body = changed_bodies[group.relative_path]
    mutation_root = owner_state_body_mutation_root(
        group,
        changed_body,
    )
    owner_receipt = issue_owner_state_snapshot_receipt(
        identity=IDENTITY,
        relative_path=group.relative_path,
        body_sha256=hashlib.sha256(changed_body).hexdigest(),
        body_bytes=len(changed_body),
        mutation_root_sha256=mutation_root,
        frozen_tick=2,
        authority_key=OWNER_KEY,
    )

    candidate, receipt = _sealed_candidate(
        tmp_path,
        store,
        baseline,
        bodies=changed_bodies,
        authorities={group.relative_path: owner_receipt},
    )

    assert receipt["owner_snapshot_paths"] == [group.relative_path]
    embedded = receipt["path_owner_snapshots"][0][
        "owner_snapshot_receipt"
    ]
    assert embedded == owner_receipt.record()
    assert embedded["mutation_root_sha256"] == "a" * 64
    changed_owner_paths = {
        path
        for path in OWNER_PATHS
        if baseline.stored_bytes(path) != candidate.stored_bytes(path)
    }
    assert changed_owner_paths == {group.relative_path}
    delta = census_generation_content_delta(baseline, candidate)
    new_owner_chunk_paths = {
        relative_path
        for chunk in delta.new_chunks
        for relative_path in chunk.relative_paths
        if relative_path in OWNER_PATHS
    }
    assert new_owner_chunk_paths == {group.relative_path}
    assert json.loads(candidate.stored_bytes(MEMBER))[
        "owner_snapshot_paths"
    ] == [group.relative_path]
    changed_paths = {
        path
        for path in (*OWNER_PATHS, CONFIG, MEMBER)
        if baseline.stored_bytes(path) != candidate.stored_bytes(path)
    }
    assert changed_paths == {group.relative_path, MEMBER}
