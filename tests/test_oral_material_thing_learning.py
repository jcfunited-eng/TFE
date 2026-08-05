from __future__ import annotations

import json

import pytest

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.causal_thing_mosaic_persistence import (
    restore_causal_thing_mosaic_owner,
)
from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
    EmbodimentWorldAuthority,
    PickCommand,
    encode_command,
)
from dsf_ai_service.v4.guala_physical_runtime import Guala


KEY = "oral-material-thing-learning-authority-key-v1"
NONCE = "oral-material-learning-nonce-0001"
OBJECT_ID = "W1-object-1"


@pytest.fixture
def runtime(monkeypatch):
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("GUALA_CAUSAL_ACTION_KEY", KEY)
    value = Guala()
    try:
        yield value
    finally:
        value.shutdown()


def _pick(runtime: Guala):
    before = runtime._embodiment_world.observation_snapshot()
    execution = runtime._embodiment_world.execute_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(PickCommand(
            OBJECT_ID,
            duration_microseconds=200_000,
        )),
        causal_intent_receipt_sha256="a" * 64,
        expected_revision=before.revision,
    )
    assert execution.disposition == "applied"
    mount = runtime._w1_physical_evidence.mount_action_outcome(execution)
    custody = runtime._settled_prediction_custody(
        mount,
        world_execution=execution,
    )
    return execution, custody


def _held_thing(runtime: Guala):
    _execution, custody = _pick(runtime)
    return runtime._admit_thing_genesis_from_custody(custody)


def _oral(runtime: Guala, *, nonce=NONCE):
    return runtime.experience_oral_material_contact(
        tutor_id="joe",
        nonce=nonce,
        object_id=OBJECT_ID,
        duration_microseconds=200_000,
    )


def test_oral_material_contact_continues_full_field_thing(runtime):
    genesis = _held_thing(runtime)

    result = _oral(runtime)

    assert result["persistent_learned_state_created"] is True
    assert result["settlement_state"] == "consequence_learned"
    assert result["idempotent_replay"] is False
    assert result["thing_id"] == genesis.thing_id
    assert result["thing_version"] == genesis.version + 1
    learned = next(
        value
        for value in runtime._causal_thing_mosaic_owner.mosaics
        if value.thing_id == genesis.thing_id
    )
    partition = learned.partitions[-1]
    assert partition.execution_receipt_sha256 == (
        result["action_receipt_sha256"]
    )
    assert partition.settlement_receipt_sha256 == (
        result["consequence_settlement_receipt_sha256"]
    )
    assert [
        {
            "physical_value_sha256": value.physical_value_sha256,
            "sense": value.sense,
            "topology_index": value.topology_index,
        }
        for value in partition.full_field_roots
    ] == result["full_field_root_commitments"]
    assert {
        value.sense for value in partition.full_field_roots
    }.issuperset({"body", "smell", "taste", "touch"})
    for root in partition.full_field_roots:
        evidence = json.loads(root.full_evidence_json)
        assert evidence["field_tuples"]
        for field_tuple in evidence["field_tuples"]:
            assert tuple(
                name for name, _value in field_tuple["fields"]
            ) == DSF_FIELD_ORDER
    consequence = runtime._whole_organism_episode_authority.episodes[-1]
    receptor_contributions = {
        value.mechanism_id: value.state.value
        for value in consequence.contributions
        if value.mechanism_id.startswith("receptor:")
    }
    assert set(receptor_contributions) == {
        "receptor:body",
        "receptor:sight",
        "receptor:smell",
        "receptor:sound",
        "receptor:taste",
        "receptor:touch",
    }
    for owner in (
        runtime._causal_thing_mosaic_owner,
        runtime._causal_thing_lived_context,
    ):
        status = owner.status()
        assert status["state_bytes"] <= status["state_capacity_bytes"]


def test_oral_replay_is_exactly_idempotent_and_cold_retained(runtime):
    _held_thing(runtime)
    first = _oral(runtime)
    world_after = runtime._embodiment_world.encoded_snapshot()
    mosaic_after = (
        runtime._causal_thing_mosaic_owner.snapshot_encoded()
    )
    lived_after = runtime._causal_thing_lived_context.snapshot_encoded()

    replay = _oral(runtime)

    assert replay["idempotent_replay"] is True
    assert replay["action_receipt_sha256"] == (
        first["action_receipt_sha256"]
    )
    assert replay["thing_partition_receipt_sha256"] == (
        first["thing_partition_receipt_sha256"]
    )
    assert runtime._embodiment_world.encoded_snapshot() == world_after
    assert (
        runtime._causal_thing_mosaic_owner.snapshot_encoded()
        == mosaic_after
    )
    assert (
        runtime._causal_thing_lived_context.snapshot_encoded()
        == lived_after
    )

    restored_world = EmbodimentWorldAuthority(authority_key=KEY)
    restored_world.restore_encoded(world_after)
    latest = restored_world.latest_execution_snapshot()
    assert latest is not None
    assert (
        restored_world.applied_execution_for_causal_intent(
            latest.causal_intent_receipt_sha256
        )
        == latest
    )
    restored_mosaic = restore_causal_thing_mosaic_owner(
        authority_key=runtime._thing_vocal_key,
        partition_authority=runtime._thing_partition_authority,
        encoded=mosaic_after,
    )
    assert restored_mosaic.snapshot_encoded() == mosaic_after
    assert restored_mosaic.mosaics[-1].version == first["thing_version"]


def test_oral_without_prior_thing_is_unresolved_and_rolls_back(runtime):
    _pick(runtime)
    world_before = runtime._embodiment_world.encoded_snapshot()
    mosaic_before = (
        runtime._causal_thing_mosaic_owner.snapshot_encoded()
    )
    lived_before = runtime._causal_thing_lived_context.snapshot_encoded()
    whole_before = runtime._live_whole_action_spine_snapshot()
    w1_before = runtime._w1_physical_evidence.status()

    result = _oral(runtime)

    assert result["persistent_learned_state_created"] is False
    assert result["settlement_state"] == "unresolved"
    assert result["reason"] == "no_prior_authenticated_held_thing"
    assert result["action_receipt_sha256"] is None
    assert runtime._embodiment_world.encoded_snapshot() == world_before
    assert (
        runtime._causal_thing_mosaic_owner.snapshot_encoded()
        == mosaic_before
    )
    assert (
        runtime._causal_thing_lived_context.snapshot_encoded()
        == lived_before
    )
    assert runtime._live_whole_action_spine_snapshot() == whole_before
    assert runtime._w1_physical_evidence.status() == w1_before


def test_oral_learning_rolls_back_every_owner_on_lived_failure(
    runtime,
    monkeypatch,
):
    _held_thing(runtime)
    world_before = runtime._embodiment_world.encoded_snapshot()
    mosaic_before = (
        runtime._causal_thing_mosaic_owner.snapshot_encoded()
    )
    lived_before = runtime._causal_thing_lived_context.snapshot_encoded()
    whole_before = runtime._live_whole_action_spine_snapshot()
    w1_before = runtime._w1_physical_evidence.status()

    def fail_lived(*_args, **_kwargs):
        raise RuntimeError("injected lived-context failure")

    monkeypatch.setattr(
        runtime,
        "_commit_lived_context_partitions",
        fail_lived,
    )
    with pytest.raises(
        RuntimeError,
        match="injected lived-context failure",
    ):
        _oral(runtime)

    assert runtime._embodiment_world.encoded_snapshot() == world_before
    assert (
        runtime._causal_thing_mosaic_owner.snapshot_encoded()
        == mosaic_before
    )
    assert (
        runtime._causal_thing_lived_context.snapshot_encoded()
        == lived_before
    )
    assert runtime._live_whole_action_spine_snapshot() == whole_before
    assert runtime._w1_physical_evidence.status() == w1_before
