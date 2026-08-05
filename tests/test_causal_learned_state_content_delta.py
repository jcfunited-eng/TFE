"""Causal learned-state growth is charged only to novel content and receipts."""

from __future__ import annotations

from pathlib import Path

from dsf_ai_service.substrate.causal_thing_mosaic import (
    CausalThingMosaicOwner,
    CausalThingMosaicProfile,
)
from dsf_ai_service.substrate.causal_thing_mosaic_persistence import (
    restore_causal_thing_mosaic_owner,
)
from dsf_ai_service.substrate.custodied_thing_encounter import (
    CustodiedW1ContactThingEncounterAuthority,
    THING_MOSAIC_CONSUMER_ID,
)
from dsf_ai_service.substrate.embodiment_world import (
    MoveCommand,
    PickCommand,
    PoseMM,
    PositionMM,
)
from dsf_ai_service.substrate.immutable_generation_store import (
    CONTENT_CHUNKS_DIRECTORY,
    CURRENT_NAME,
    MANIFEST_NAME,
    ImmutableGenerationStore,
)
from dsf_ai_service.substrate.settled_experience_custody import (
    SettledExperienceCustodyAuthority,
    SettledExperienceCustodyProfile,
)
from tests.test_causal_thing_mosaic import KEY, _execute, _fixture
from tests.test_w1_audiovisual_physical_evidence import (
    EVIDENCE_KEY,
    _authority as _physical_authority,
)


STATE_FILE = "causal_thing_mosaic.json"


def _retained_ledger(store: ImmutableGenerationStore, generation) -> dict:
    chunks = tuple(
        path
        for path in (
            store.root / CONTENT_CHUNKS_DIRECTORY
        ).rglob("*")
        if path.is_file()
    )
    manifests = tuple(
        path
        for path in store.generations_directory.rglob(MANIFEST_NAME)
        if path.is_file()
    )
    return {
        "learned_content_bytes": sum(path.stat().st_size for path in chunks),
        "learned_content_chunks": len(chunks),
        "generation_manifest_bytes": sum(
            path.stat().st_size for path in manifests),
        "generation_manifests": len(manifests),
        "current_receipt_bytes": (
            store.root / CURRENT_NAME
        ).stat().st_size,
        "recovery_receipt_bytes": len(
            generation.recovery_certificate_bytes()),
    }


def _causal_owner():
    world, sensory, _legacy_partitions, _legacy_owner = _fixture()
    partitions = CustodiedW1ContactThingEncounterAuthority(
        authority_key=KEY,
        world_authority=world,
        sensory_authority=sensory,
        max_roots_per_partition=256,
    )
    owner = CausalThingMosaicOwner(
        authority_key=KEY,
        profile=CausalThingMosaicProfile.create(
            profile_id="content-delta-causal-thing-mosaic",
            max_mosaics=4,
            max_partitions_per_mosaic=4,
            max_roots_per_partition=256,
            max_routes=512,
            max_state_bytes=64 * 1024 * 1024,
        ),
        partition_authority=partitions,
    )
    physical = _physical_authority(world)

    def partition(execution, ordinal, prior=None):
        mount = physical.mount_action_outcome(execution)
        custody = SettledExperienceCustodyAuthority(
            authority_key=f"{KEY}-content-delta-{ordinal}",
            w1_physical_authority_key=EVIDENCE_KEY,
            world_authority_key=KEY,
            profile=SettledExperienceCustodyProfile.create(
                profile_id=f"content-delta-custody-{ordinal}",
                max_children=1,
                max_snapshot_bytes=64 * 1024 * 1024,
            ),
        )
        custody.admit(mount, execution)
        capability = custody.issue_child(THING_MOSAIC_CONSUMER_ID)
        return partitions.partition_from_custody(
            custody_authority=custody,
            capability=capability,
            prior=prior,
        )

    picked = _execute(world, PickCommand("W1-object-1"), 101)
    first_partition = partition(picked, 101)
    owner.admit(first_partition)
    return world, partitions, owner, partition, first_partition


def test_zero_learning_has_zero_content_growth_and_one_learning_is_one_delta(
        tmp_path: Path,
) -> None:
    world, partitions, owner, partition, first_partition = _causal_owner()
    first_encoded = owner.snapshot_encoded()
    store = ImmutableGenerationStore(
        tmp_path / "causal-ledger",
        identity="causal-thing-mosaic-content-delta",
        required_files=(STATE_FILE,),
        content_addressed=True,
        max_encoded_generation_bytes=64 * 1024 * 1024,
    )

    first = store.commit(tick=1, files={STATE_FILE: first_encoded})
    first_ledger = _retained_ledger(store, first)
    unchanged = store.commit(tick=2, files={STATE_FILE: first_encoded})
    unchanged_ledger = _retained_ledger(store, unchanged)

    assert unchanged_ledger["learned_content_bytes"] == (
        first_ledger["learned_content_bytes"]
    )
    assert unchanged_ledger["learned_content_chunks"] == (
        first_ledger["learned_content_chunks"]
    )
    assert unchanged_ledger["generation_manifests"] == (
        first_ledger["generation_manifests"] + 1
    )
    first_record = first.recovery_certificate()["required_files"][0]
    unchanged_record = (
        unchanged.recovery_certificate()["required_files"][0]
    )
    assert unchanged_record["chunks"] == first_record["chunks"]
    assert unchanged_record["sha256"] == first_record["sha256"]
    assert unchanged_record["size_bytes"] == first_record["size_bytes"]

    moved = _execute(
        world,
        MoveCommand(PoseMM(PositionMM(1000, 1400, 0), 90_000)),
        102,
    )
    second_partition = partition(moved, 102, first_partition)
    owner.admit(second_partition)
    second_encoded = owner.snapshot_encoded()
    assert second_encoded != first_encoded

    learned = store.commit(tick=3, files={STATE_FILE: second_encoded})
    learned_ledger = _retained_ledger(store, learned)
    assert learned_ledger["learned_content_chunks"] == (
        unchanged_ledger["learned_content_chunks"] + 1
    )
    assert learned_ledger["learned_content_bytes"] == (
        unchanged_ledger["learned_content_bytes"] + len(second_encoded)
    )
    assert learned_ledger["generation_manifests"] == (
        unchanged_ledger["generation_manifests"] + 1
    )

    restored_encoded = learned.stored_bytes(STATE_FILE)
    restored = restore_causal_thing_mosaic_owner(
        authority_key=KEY,
        partition_authority=partitions,
        encoded=restored_encoded,
    )
    assert restored.snapshot_encoded() == second_encoded
    assert len(restored.mosaics[0].partitions) == 2
