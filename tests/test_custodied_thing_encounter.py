from __future__ import annotations

import ast
import inspect
from pathlib import Path
import wave

import pytest

import dsf_ai_service.substrate.custodied_thing_encounter as module
from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.causal_thing_mosaic import (
    CausalThingMosaicOwner,
    CausalThingMosaicProfile,
)
from dsf_ai_service.substrate.custodied_thing_encounter import (
    CustodiedW1ContactThingEncounterAuthority,
    THING_MOSAIC_CONSUMER_ID,
)
from dsf_ai_service.substrate.embodiment_world import (
    EmbodimentWorldAuthority,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)
from dsf_ai_service.substrate.auditory_recurrent_motif import (
    AuditoryMotifResourceProfile,
    AuditoryRecurrentMotifOwner,
)
from dsf_ai_service.substrate.w1_binaural_auditory_l5 import (
    W1BinauralAuditoryL5Owner,
)
from dsf_ai_service.substrate.w1_self_acoustic_propagation import (
    W1SelfAcousticPropagationAuthority,
)
from dsf_ai_service.substrate.w1_physical_receptors import (
    EmbodimentSensoryOutcomeAuthority,
)
from tests.test_lived_vocal_teaching_episode import _external_mount
from tests.test_w1_audiovisual_physical_evidence import (
    EVIDENCE_KEY,
    WORLD_KEY as W1_WORLD_KEY,
    _authority as _physical_authority,
    _execution,
    _world,
)
from tests.test_settled_experience_custody import (
    CUSTODY_KEY,
    PHYSICAL_KEY,
    WORLD_KEY,
    _settled_non_acoustic_w1_occurrence,
    _settled_passive_w1_occurrence,
)
from tests.test_w1_self_acoustic_propagation import (
    KEY as SELF_ACOUSTIC_KEY,
    _motor,
)
from dsf_ai_service.substrate.settled_experience_custody import (
    SettledExperienceCustodyAuthority,
    SettledExperienceCustodyProfile,
)


KEY = b"custodied-thing-encounter-test-authority-key"


def _custody(mount, execution):
    authority = SettledExperienceCustodyAuthority(
        authority_key=CUSTODY_KEY,
        w1_physical_authority_key=PHYSICAL_KEY,
        world_authority_key=WORLD_KEY,
        profile=SettledExperienceCustodyProfile.create(
            profile_id="custodied-thing-encounter",
            max_children=4,
            max_snapshot_bytes=64 * 1024 * 1024,
        ),
    )
    custody = authority.admit(mount, execution)
    child = authority.issue_child(THING_MOSAIC_CONSUMER_ID)
    return authority, custody, child


def _partition_authority(world=None, *, sensory_key=WORLD_KEY):
    world = world or EmbodimentWorldAuthority(authority_key=WORLD_KEY)
    sensory = EmbodimentSensoryOutcomeAuthority(
        authority_key=sensory_key
    )
    return CustodiedW1ContactThingEncounterAuthority(
        authority_key=KEY,
        world_authority=world,
        sensory_authority=sensory,
        max_roots_per_partition=256,
    )


def _custody_for(
    mount,
    execution,
    *,
    physical_key=PHYSICAL_KEY,
    world_key=WORLD_KEY,
):
    authority = SettledExperienceCustodyAuthority(
        authority_key=CUSTODY_KEY,
        w1_physical_authority_key=physical_key,
        world_authority_key=world_key,
        profile=SettledExperienceCustodyProfile.create(
            profile_id="custodied-thing-real-occurrence",
            max_children=4,
            max_snapshot_bytes=128 * 1024 * 1024,
        ),
    )
    custody = authority.admit(mount, execution)
    child = authority.issue_child(THING_MOSAIC_CONSUMER_ID)
    return authority, custody, child


def test_pick_occurrence_partitions_from_one_read_only_custody():
    mount, execution = _settled_non_acoustic_w1_occurrence()
    custody_authority, custody, child = _custody(mount, execution)
    partitions = _partition_authority()
    owner = CausalThingMosaicOwner(
        authority_key=KEY,
        profile=CausalThingMosaicProfile.create(
            profile_id="custodied-thing-mosaic",
            max_mosaics=4,
            max_partitions_per_mosaic=4,
            max_roots_per_partition=256,
            max_routes=2_048,
            max_state_bytes=64 * 1024 * 1024,
        ),
        partition_authority=partitions,
    )

    partition = partitions.partition_from_custody(
        custody_authority=custody_authority,
        capability=child,
    )
    mosaic = owner.admit(partition)

    assert partition.execution_receipt_sha256 == (
        execution.authority_receipt_sha256
    )
    assert partition.settlement_receipt_sha256 == (
        custody.causal_settlement.authority_receipt_sha256
    )
    assert partition.world_observation_receipt_sha256 == (
        execution.after.authority_receipt_sha256
    )
    assert partition.entity_root_keys
    assert mosaic.partitions == (partition,)
    assert custody.occurrence_counter.as_record() == (
        custody_authority.status()["occurrence_counter"]
    )
    for root in partition.full_field_roots:
        for field_tuple in __import__("json").loads(
            root.full_evidence_json
        )["field_tuples"]:
            assert tuple(
                name for name, _value in field_tuple["fields"]
            ) == DSF_FIELD_ORDER


def test_self_vocal_occurrence_advances_the_same_held_thing():
    world = _world()
    physical = _physical_authority(world)
    pick_execution = _execution(world)
    pick_mount = physical.mount_action_outcome(pick_execution)
    pick_custody, _pick_value, pick_child = _custody_for(
        pick_mount,
        pick_execution,
        physical_key=EVIDENCE_KEY,
        world_key=W1_WORLD_KEY,
    )
    partitions = _partition_authority(
        world,
        sensory_key=W1_WORLD_KEY,
    )
    first = partitions.partition_from_custody(
        custody_authority=pick_custody,
        capability=pick_child,
    )

    motor, exemplar = _motor()
    self_acoustic = W1SelfAcousticPropagationAuthority(
        authority_key=SELF_ACOUSTIC_KEY,
        world_authority=world,
        motor_owner=motor,
        causal_owner=ExactCausalExperienceOwner(
            on_settlement=lambda _settlement: None,
            log_event=lambda *_args, **_kwargs: None,
        ),
        binaural_l5_owner=W1BinauralAuditoryL5Owner(),
        binaural_motif_owner=AuditoryRecurrentMotifOwner(
            AuditoryMotifResourceProfile.create(
                profile_id="held-thing-self-vocal-q",
                ear_count=2,
                max_motif_neurons=24_192,
                max_pending_experiences=8,
                max_work_cells_per_observation=8_000_000,
                max_exact_fraction_text_bytes=4_096,
                encoded_state_allocation_bytes=128 * 1024 * 1024,
            ),
            ear_ids=("left", "right"),
        ),
    )
    emission = motor.execute(
        motor_id=exemplar.motor_id,
        world_authority=world,
        causal_intent_receipt_sha256="7" * 64,
    )
    self_mount = self_acoustic.propagate(emission)
    self_custody = SettledExperienceCustodyAuthority(
        authority_key=CUSTODY_KEY,
        w1_physical_authority_key=EVIDENCE_KEY,
        w1_self_acoustic_authority_key=SELF_ACOUSTIC_KEY,
        world_authority_key=W1_WORLD_KEY,
        profile=SettledExperienceCustodyProfile.create(
            profile_id="held-thing-self-vocal-custody",
            max_children=2,
            max_snapshot_bytes=128 * 1024 * 1024,
        ),
    )
    self_custody.admit(self_mount, emission.execution_receipt)
    self_child = self_custody.issue_child(THING_MOSAIC_CONSUMER_ID)

    second = partitions.partition_from_custody(
        custody_authority=self_custody,
        capability=self_child,
        prior=first,
    )

    assert second.prior_partition_receipt_sha256 == (
        first.authority_receipt_sha256
    )
    assert second.entity_continuity_hmac_sha256 == (
        first.entity_continuity_hmac_sha256
    )
    assert second.world_revision == first.world_revision + 1
    assert second.world_observation_receipt_sha256 == (
        emission.execution_receipt.after.authority_receipt_sha256
    )
    assert second.entity_root_keys
    assert {
        root.sense for root in second.full_field_roots
    } >= {"body", "sight", "sound", "touch"}


def test_partition_rejects_another_consumers_capability():
    mount, execution = _settled_non_acoustic_w1_occurrence()
    custody_authority, _custody_value, _child = _custody(
        mount, execution
    )
    other = custody_authority.issue_child("prediction")
    partitions = _partition_authority()

    with pytest.raises(
        ValueError,
        match="own custody capability",
    ):
        partitions.partition_from_custody(
            custody_authority=custody_authority,
            capability=other,
        )


def test_passive_custody_cannot_claim_a_contact_transition():
    mount, observation = _settled_passive_w1_occurrence()
    authority = SettledExperienceCustodyAuthority(
        authority_key=CUSTODY_KEY,
        w1_physical_authority_key=PHYSICAL_KEY,
        world_authority_key=WORLD_KEY,
        profile=SettledExperienceCustodyProfile.create(
            profile_id="passive-cannot-be-contact",
            max_children=2,
            max_snapshot_bytes=64 * 1024 * 1024,
        ),
    )
    authority.admit(mount, world_observation=observation)
    child = authority.issue_child(THING_MOSAIC_CONSUMER_ID)

    with pytest.raises(
        ValueError,
        match="applied-execution custody",
    ):
        _partition_authority().partition_from_custody(
            custody_authority=authority,
            capability=child,
        )


def test_real_recorded_word_enters_held_thing_as_same_causal_mosaic():
    recording = Path(
        "dsf_ai_service/curriculum/assets/speech_commands/"
        "go/022cd682_nohash_0.wav"
    )
    with wave.open(str(recording), "rb") as source:
        assert (
            source.getnchannels(),
            source.getsampwidth(),
            source.getframerate(),
        ) == (1, 2, 16_000)
        pcm_s16le = source.readframes(source.getnframes())

    world = _world()
    physical = _physical_authority(world)
    partitions = _partition_authority(
        world,
        sensory_key=EVIDENCE_KEY,
    )
    owner = CausalThingMosaicOwner(
        authority_key=KEY,
        profile=CausalThingMosaicProfile.create(
            profile_id="custodied-real-word-thing-mosaic",
            max_mosaics=4,
            max_partitions_per_mosaic=4,
            max_roots_per_partition=256,
            max_routes=2_048,
            max_state_bytes=128 * 1024 * 1024,
        ),
        partition_authority=partitions,
    )

    pick_execution = _execution(world)
    pick_mount = physical.mount_action_outcome(pick_execution)
    pick_custody, pick_parent, pick_child = _custody_for(
        pick_mount,
        pick_execution,
        physical_key=EVIDENCE_KEY,
        world_key=W1_WORLD_KEY,
    )
    first = partitions.partition_from_custody(
        custody_authority=pick_custody,
        capability=pick_child,
    )
    genesis = owner.admit(first)

    speech_execution, speech_mount = _external_mount(
        world,
        physical,
        pcm_s16le,
    )
    speech_custody, speech_parent, speech_child = _custody_for(
        speech_mount,
        speech_execution,
        physical_key=EVIDENCE_KEY,
        world_key=W1_WORLD_KEY,
    )
    second = partitions.partition_from_custody(
        custody_authority=speech_custody,
        capability=speech_child,
        prior=first,
    )
    expanded = owner.admit(second)

    assert expanded.thing_id == genesis.thing_id
    assert expanded.partitions == (first, second)
    assert second.prior_partition_receipt_sha256 == (
        first.authority_receipt_sha256
    )
    assert {
        root.sense for root in second.full_field_roots
    }.issuperset({"body", "sight", "sound", "touch"})
    assert speech_parent.binaural_auditory_l5 is not None
    assert speech_parent.binaural_receptor_settlement is not None
    assert pick_parent.binaural_auditory_l5 is None
    assert (
        speech_parent.occurrence_counter
        .source_transduction_lineage_count
        == speech_parent.occurrence_counter
        .full_field_build_lineage_count
        == speech_parent.occurrence_counter
        .causal_settlement_lineage_count
        == speech_parent.occurrence_counter.custody_count
        == 1
    )


def test_custody_partition_module_has_no_physical_producer_calls():
    tree = ast.parse(inspect.getsource(module))
    forbidden = {
        "build_transaction_owned_six_sense_full_field",
        "mount",
        "mount_action_outcome",
        "mount_current_observation",
        "settle",
        "transduce",
        "transduce_auditory_full_field",
    }
    called = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
    } | {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
    }
    assert not forbidden.intersection(called)
