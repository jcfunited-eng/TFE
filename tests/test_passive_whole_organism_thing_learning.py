from __future__ import annotations

import hashlib
import hmac
import json
import math
from dataclasses import replace
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    NativeSensorySubstreamInput,
    build_six_sense_full_field,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    NativeAxisCoordinate,
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.anonymous_passive_window import (
    AnonymousPassiveWindowAuthority,
    AnonymousPassiveWindowProfile,
)
from dsf_ai_service.substrate.causal_thing_mosaic import (
    CausalThingMosaicOwner,
    CausalThingMosaicProfile,
)
from dsf_ai_service.substrate.custodied_thing_encounter import (
    CustodiedW1ContactThingEncounterAuthority,
    THING_MOSAIC_CONSUMER_ID,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)
from dsf_ai_service.substrate.passive_whole_organism_thing_learning import (
    PASSIVE_THING_LEARNING_CONSUMER_ID,
    PassiveThingLearningProfile,
    PassiveWholeOrganismThingLearningOwner,
)
from dsf_ai_service.substrate import (
    passive_whole_organism_thing_learning as passive_learning_module,
)
from dsf_ai_service.substrate.settled_experience_custody import (
    SettledExperienceCustodyAuthority,
    SettledExperienceCustodyProfile,
)
from dsf_ai_service.substrate.w1_physical_receptors import (
    EmbodimentSensoryOutcomeAuthority,
)
from tests.test_w1_audiovisual_physical_evidence import (
    EVIDENCE_KEY,
    WORLD_KEY,
    _authority as _physical_authority,
    _execution,
    _world,
)
from tests.test_whole_organism_neuron_population import (
    _owner as _neuron_owner,
)
from tests.native_joint_occurrence_support import joint_occurrences_for


PARTITION_KEY = b"passive-learning-partition-authority-key-v1"
ACTION_CUSTODY_KEY = b"passive-learning-action-custody-key-v1"
PASSIVE_CUSTODY_KEY = b"passive-learning-window-custody-key-v1"
WINDOW_KEY = b"passive-learning-window-authority-key-v1"
LEARNING_KEY = b"passive-learning-owner-authority-key-v1"


def _native(
    sense: PhysicalSense,
    *,
    topology_index: int,
) -> NativeSensorySubstreamInput:
    count = 48
    return NativeSensorySubstreamInput(
        sense=sense,
        sensor_id=f"passive-{sense.value}-{topology_index}",
        substream_id=f"{sense.value}-field-{topology_index}",
        topology_index=topology_index,
        coordinates=(
            NativeAxisCoordinate(
                f"{sense.value}-receptor",
                str(topology_index),
            ),
        ),
        physical_quantity=f"{sense.value}-physical-intensity",
        physical_unit="exact-normalized-physical-input",
        source_times=tuple(
            Fraction(index, 1_000) for index in range(count)
        ),
        normalized_signal=tuple(
            math.sin(
                2
                * math.pi
                * (topology_index + 2)
                * index
                / count
            )
            for index in range(count)
        ),
        phase_turns=tuple(
            Fraction(index // 8) for index in range(count)
        ),
    )


def _settlement(
    window_id: str,
    observed_senses: tuple[PhysicalSense, ...],
):
    observed = {
        sense: (_native(sense, topology_index=0),)
        for sense in observed_senses
    }
    states = {
        sense: (
            SenseBoundaryState.OBSERVED
            if sense in observed
            else SenseBoundaryState.SENSOR_UNAVAILABLE
        )
        for sense in SENSE_ORDER
    }
    built = build_six_sense_full_field(
        assembly_id=f"causal-{window_id}",
        source_time_start=Fraction(0),
        source_time_end=Fraction(48, 1_000),
        observed_substreams=observed, occurrences=joint_occurrences_for(observed),
        states=states,
    )
    return ExactCausalExperienceOwner(
        on_settlement=lambda _value: None,
        log_event=lambda *_args, **_kwargs: None,
    ).settle(
        built,
        routing_chis=(),
        source_tags=(),
    )


def _thing_stack():
    world = _world()
    physical = _physical_authority(world)
    no_target_observation = world.observation_snapshot()
    execution = _execution(world)
    mount = physical.mount_action_outcome(execution)
    custody = SettledExperienceCustodyAuthority(
        authority_key=ACTION_CUSTODY_KEY,
        w1_physical_authority_key=EVIDENCE_KEY,
        world_authority_key=WORLD_KEY,
        profile=SettledExperienceCustodyProfile.create(
            profile_id="passive-learning-action-custody",
            max_children=2,
            max_snapshot_bytes=64 * 1024 * 1024,
        ),
    )
    custody.admit(mount, execution)
    capability = custody.issue_child(THING_MOSAIC_CONSUMER_ID)
    partitions = CustodiedW1ContactThingEncounterAuthority(
        authority_key=PARTITION_KEY,
        world_authority=world,
        sensory_authority=EmbodimentSensoryOutcomeAuthority(
            authority_key=WORLD_KEY
        ),
        max_roots_per_partition=256,
    )
    things = CausalThingMosaicOwner(
        authority_key=PARTITION_KEY,
        profile=CausalThingMosaicProfile.create(
            profile_id="passive-learning-thing-owner",
            max_mosaics=4,
            max_partitions_per_mosaic=8,
            max_roots_per_partition=256,
            max_routes=4_096,
            max_state_bytes=64 * 1024 * 1024,
        ),
        partition_authority=partitions,
    )
    partition = partitions.partition_from_custody(
        custody_authority=custody,
        capability=capability,
    )
    mosaic = things.admit_custody_genesis(partition)
    neurons = _neuron_owner()
    return (
        world,
        partitions,
        things,
        mosaic,
        no_target_observation,
        neurons,
    )


def _passive_custody(
    *,
    world,
    window_id: str,
    observed_senses: tuple[PhysicalSense, ...],
    neuron_owner,
    observation=None,
):
    settlement = _settlement(window_id, observed_senses)
    neuron_owner.commit(neuron_owner.prepare(settlement))
    window = AnonymousPassiveWindowAuthority(
        authority_key=WINDOW_KEY,
        profile=AnonymousPassiveWindowProfile.create(
            profile_id=f"passive-window-{window_id}",
            max_mounts=1,
            max_state_bytes=64 * 1024 * 1024,
        ),
        world_authority=world,
    )
    prepared = window.prepare(
        window_id=window_id,
        settlement=settlement,
        world_observation=observation or world.observation_snapshot(),
    )
    custody = SettledExperienceCustodyAuthority(
        authority_key=PASSIVE_CUSTODY_KEY,
        w1_physical_authority_key=EVIDENCE_KEY,
        world_authority_key=WORLD_KEY,
        anonymous_passive_window_authority_key=WINDOW_KEY,
        profile=SettledExperienceCustodyProfile.create(
            profile_id=f"passive-custody-{window_id}",
            max_children=2,
            max_snapshot_bytes=64 * 1024 * 1024,
        ),
    )
    custody.admit(prepared.mount)
    window.commit_prepared(prepared)
    capability = custody.issue_child(
        PASSIVE_THING_LEARNING_CONSUMER_ID
    )
    return custody, capability


def _owner(
    partitions,
    things,
    neuron_owner,
    *,
    max_records: int = 8,
):
    profile = PassiveThingLearningProfile.create(
        profile_id="passive-whole-organism-learning",
        max_records=max_records,
        max_roots_per_record=256,
        max_state_bytes=64 * 1024 * 1024,
    )
    return (
        PassiveWholeOrganismThingLearningOwner(
            authority_key=LEARNING_KEY,
            profile=profile,
            partition_authority=partitions,
            thing_owner=things,
            neuron_owner=neuron_owner,
        ),
        profile,
    )


@pytest.mark.parametrize(
    "observed_senses",
    (
        (PhysicalSense.SOUND, PhysicalSense.SIGHT),
        (PhysicalSense.SOUND, PhysicalSense.SMELL),
    ),
)
def test_any_observed_pair_learns_by_target_continuity_not_sense(
    observed_senses,
    monkeypatch,
):
    (
        world,
        partitions,
        things,
        mosaic,
        _no_target,
        neurons,
    ) = _thing_stack()
    custody, capability = _passive_custody(
        world=world,
        window_id="-".join(value.value for value in observed_senses),
        observed_senses=observed_senses,
        neuron_owner=neurons,
    )
    owner, _profile = _owner(partitions, things, neurons)

    result = owner.admit(
        custody_authority=custody,
        custody_capability=capability,
    )

    assert result.state == "learned"
    assert result.record is not None
    assert result.record.thing_id == mosaic.thing_id
    assert (
        result.record.neuron_mosaic_assembly.full_field_roots
        == result.record.full_field_roots
    )
    assert (
        result.record.neuron_mosaic_assembly
        .settlement_receipt_sha256
        == result.record.story.settlement_authority_receipt_sha256
    )
    neurons.verify_mosaic_assembly(
        result.record.neuron_mosaic_assembly,
        expected_roots=result.record.full_field_roots,
        expected_settlement_receipt_sha256=(
            result.record.story.settlement_authority_receipt_sha256
        ),
    )
    assert frozenset(result.record.observed_senses) == frozenset(
        value.value for value in observed_senses
    )
    assert len(result.record.six_lane_states) == len(SENSE_ORDER)
    assert owner.status()["master_sense"] is None
    assert frozenset(owner.roots_for_thing(mosaic.thing_id)) == (
        frozenset(result.record.full_field_roots)
    )
    assert owner.receipts_for_thing(mosaic.thing_id) == (
        result.record.authority_receipt_sha256,
    )
    assert all(
        tuple(
            name for name, _value in field_tuple["fields"]
        )
        == DSF_FIELD_ORDER
        for root in result.record.full_field_roots
        for field_tuple in __import__("json").loads(
            root.full_evidence_json
        )["field_tuples"]
    )
    record = result.record
    root_type = type(record.full_field_roots[0])
    original_verify = root_type.verify
    calls = 0

    def counted_verify(root):
        nonlocal calls
        calls += 1
        return original_verify(root)

    monkeypatch.setattr(root_type, "verify", counted_verify)
    object.__setattr__(record, "_verified_integrity", None)
    owner._verify_record(record)
    owner._verify_record(record)
    assert calls == 2 * len(record.full_field_roots)


def test_unknown_contact_and_fewer_than_two_senses_leave_exact_bytes():
    (
        world,
        partitions,
        things,
        _mosaic,
        no_target_observation,
        neurons,
    ) = _thing_stack()
    owner, _profile = _owner(partitions, things, neurons)
    baseline = owner.snapshot_encoded()

    one_custody, one_capability = _passive_custody(
        world=world,
        window_id="single-sound",
        observed_senses=(PhysicalSense.SOUND,),
        neuron_owner=neurons,
    )
    one = owner.admit(
        custody_authority=one_custody,
        custody_capability=one_capability,
    )
    assert one.state == "unresolved"
    assert one.reasons == ("fewer_than_two_observed_senses",)
    assert owner.snapshot_encoded() == baseline

    absent_custody, absent_capability = _passive_custody(
        world=world,
        window_id="no-contacted-target",
        observed_senses=(
            PhysicalSense.SOUND,
            PhysicalSense.SIGHT,
        ),
        neuron_owner=neurons,
        observation=no_target_observation,
    )
    absent = owner.admit(
        custody_authority=absent_custody,
        custody_capability=absent_capability,
    )
    assert absent.state == "unresolved"
    assert "contacted entity" in absent.reasons[0]
    assert owner.snapshot_encoded() == baseline
    assert things.mosaics[0].partitions


def test_another_consumers_capability_is_rejected_without_mutation():
    (
        world,
        partitions,
        things,
        _mosaic,
        _no_target,
        neurons,
    ) = _thing_stack()
    custody, _capability = _passive_custody(
        world=world,
        window_id="wrong-consumer",
        observed_senses=(
            PhysicalSense.SOUND,
            PhysicalSense.SIGHT,
        ),
        neuron_owner=neurons,
    )
    another = custody.issue_child("another-consumer")
    owner, _profile = _owner(partitions, things, neurons)
    baseline = owner.snapshot_encoded()

    with pytest.raises(
        ValueError,
        match="own custody capability",
    ):
        owner.prepare_admission(
            custody_authority=custody,
            custody_capability=another,
        )

    assert owner.snapshot_encoded() == baseline


def test_prepare_commit_rollback_capacity_and_cold_restore_are_exact():
    (
        world,
        partitions,
        things,
        mosaic,
        _no_target,
        neurons,
    ) = _thing_stack()
    owner, profile = _owner(
        partitions,
        things,
        neurons,
        max_records=1,
    )
    custody, capability = _passive_custody(
        world=world,
        window_id="transaction",
        observed_senses=(
            PhysicalSense.SOUND,
            PhysicalSense.SMELL,
        ),
        neuron_owner=neurons,
    )
    baseline = owner.snapshot_encoded()

    prepared = owner.prepare_admission(
        custody_authority=custody,
        custody_capability=capability,
    )
    assert prepared.state == "prepared"
    assert prepared.prepared is not None
    assert owner.snapshot_encoded() == baseline
    undo = owner.commit_prepared(prepared.prepared)
    committed = owner.snapshot_encoded()
    assert committed != baseline
    owner.rollback_committed(undo)
    assert owner.snapshot_encoded() == baseline

    learned = owner.admit(
        custody_authority=custody,
        custody_capability=capability,
    )
    assert learned.state == "learned"
    encoded = owner.snapshot_encoded()
    assert b"native_evidence_transition" in encoded
    assert b"neuron_mosaic_assembly" in encoded
    assert b"receipt_records" not in encoded
    assert b"payload_base64" not in encoded

    second_custody, second_capability = _passive_custody(
        world=world,
        window_id="capacity",
        observed_senses=(
            PhysicalSense.SOUND,
            PhysicalSense.SIGHT,
        ),
        neuron_owner=neurons,
    )
    refused = owner.admit(
        custody_authority=second_custody,
        custody_capability=second_capability,
    )
    assert refused.state == "unresolved"
    assert refused.reasons == (
        "passive learning record capacity exhausted",
    )
    assert owner.snapshot_encoded() == encoded

    cold = PassiveWholeOrganismThingLearningOwner.restore_encoded(
        authority_key=LEARNING_KEY,
        profile=profile,
        partition_authority=partitions,
        thing_owner=things,
        neuron_owner=neurons,
        encoded=encoded,
    )
    assert cold.snapshot_encoded() == encoded
    assert cold.roots_for_thing(mosaic.thing_id) == (
        owner.roots_for_thing(mosaic.thing_id)
    )

    damaged = bytearray(encoded)
    damaged[-8] = ord("0") if damaged[-8] != ord("0") else ord("1")
    with pytest.raises(ValueError):
        PassiveWholeOrganismThingLearningOwner.restore_encoded(
            authority_key=LEARNING_KEY,
            profile=profile,
            partition_authority=partitions,
            thing_owner=things,
            neuron_owner=neurons,
            encoded=bytes(damaged),
        )


def test_neuron_assembly_tamper_and_populated_v1_are_refused():
    (
        world,
        partitions,
        things,
        _mosaic,
        _no_target,
        neurons,
    ) = _thing_stack()
    owner, profile = _owner(partitions, things, neurons)
    custody, capability = _passive_custody(
        world=world,
        window_id="assembly-custody",
        observed_senses=(
            PhysicalSense.SOUND,
            PhysicalSense.SIGHT,
        ),
        neuron_owner=neurons,
    )
    learned = owner.admit(
        custody_authority=custody,
        custody_capability=capability,
    )
    assert learned.record is not None
    record = learned.record
    tampered_assembly = replace(
        record.neuron_mosaic_assembly,
        settlement_receipt_sha256="0" * 64,
    )
    tampered_record = replace(
        record,
        neuron_mosaic_assembly=tampered_assembly,
    )
    with pytest.raises(
        ValueError,
        match="neuron mosaic assembly authority changed",
    ):
        owner.issue_relation_gap_capability(
            record=tampered_record,
            whole_organism_episode_receipt_sha256="1" * 64,
        )

    current = json.loads(owner.snapshot_encoded())
    legacy_record = dict(current["body"]["records"][0])
    legacy_record.pop("neuron_mosaic_assembly")
    legacy_record["schema"] = (
        "guala.passive_thing_learning.record.v1"
    )
    legacy_body = {
        **current["body"],
        "records": [legacy_record],
        "schema": "guala.passive_thing_learning.state.v1",
    }
    legacy_envelope = {
        "body": legacy_body,
        "schema": current["schema"],
        "state_hmac_sha256": hmac.new(
            owner._legacy_state_key,
            passive_learning_module._LEGACY_STATE_DOMAIN
            + passive_learning_module._canonical(legacy_body),
            hashlib.sha256,
        ).hexdigest(),
    }
    legacy_encoded = passive_learning_module._canonical(
        legacy_envelope
    )
    with pytest.raises(
        ValueError,
        match="lacks exact neuron mosaic custody",
    ):
        PassiveWholeOrganismThingLearningOwner.restore_encoded(
            authority_key=LEARNING_KEY,
            profile=profile,
            partition_authority=partitions,
            thing_owner=things,
            neuron_owner=neurons,
            encoded=legacy_encoded,
        )

    empty_legacy_body = {
        **legacy_body,
        "records": [],
    }
    empty_legacy_encoded = passive_learning_module._canonical({
        "body": empty_legacy_body,
        "schema": current["schema"],
        "state_hmac_sha256": hmac.new(
            owner._legacy_state_key,
            passive_learning_module._LEGACY_STATE_DOMAIN
            + passive_learning_module._canonical(empty_legacy_body),
            hashlib.sha256,
        ).hexdigest(),
    })
    migrated = (
        PassiveWholeOrganismThingLearningOwner
        .migrate_authenticated_empty_v1_encoded(
            authority_key=LEARNING_KEY,
            profile=profile,
            partition_authority=partitions,
            thing_owner=things,
            neuron_owner=neurons,
            encoded=empty_legacy_encoded,
        )
    )
    migrated_body = json.loads(migrated)["body"]
    assert migrated_body["schema"] == (
        "guala.passive_thing_learning.state.v2"
    )
    assert migrated_body["records"] == []
