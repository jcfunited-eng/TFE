"""Passive-only reciprocal trace recurrence without the known-sight hierarchy."""

from __future__ import annotations

import json
from dataclasses import replace
from fractions import Fraction

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    build_six_sense_full_field,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
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
from dsf_ai_service.substrate.causal_thing_mosaic_persistence import (
    restore_causal_thing_mosaic_owner,
)
from dsf_ai_service.substrate.causal_thing_reciprocal_mosaic import (
    CausalThingReciprocalMosaicOwner,
)
from dsf_ai_service.substrate.custodied_thing_encounter import (
    CustodiedW1ContactThingEncounterAuthority,
    THING_MOSAIC_CONSUMER_ID,
)
from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
    EmbodiedObject,
    MoveCommand,
    PickCommand,
    PlaceCommand,
    PoseMM,
    PositionMM,
    encode_command,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)
from dsf_ai_service.substrate.passive_whole_organism_thing_learning import (
    PASSIVE_THING_LEARNING_CONSUMER_ID,
    PassiveThingLearningProfile,
    PassiveWholeOrganismThingLearningOwner,
)
from dsf_ai_service.substrate.settled_experience_custody import (
    SettledExperienceCustodyAuthority,
    SettledExperienceCustodyProfile,
)
from dsf_ai_service.substrate.w1_physical_receptors import (
    EmbodimentSensoryOutcomeAuthority,
)
from tests.test_passive_whole_organism_thing_learning import (
    ACTION_CUSTODY_KEY,
    LEARNING_KEY,
    PARTITION_KEY,
    PASSIVE_CUSTODY_KEY,
    WINDOW_KEY,
    _native,
)
from tests.test_whole_organism_neuron_population import (
    _owner as _neuron_owner,
)
from tests.test_w1_audiovisual_physical_evidence import (
    EVIDENCE_KEY,
    WORLD_KEY,
    _authority as _physical_authority,
    _world,
)


RECIPROCAL_KEY = b"passive-reciprocal-trace-cutover-key-v2"


def _trace_settlement(
    window_id: str,
    *,
    altered_sound: bool = False,
):
    sound = _native(PhysicalSense.SOUND, topology_index=0)
    if altered_sound:
        sound = replace(
            sound,
            normalized_signal=tuple(
                value / 2 for value in sound.normalized_signal
            ),
        )
    observed = {
        PhysicalSense.SIGHT: (
            _native(PhysicalSense.SIGHT, topology_index=0),
        ),
        PhysicalSense.SOUND: (sound,),
    }
    built = build_six_sense_full_field(
        assembly_id=f"causal-{window_id}",
        source_time_start=Fraction(0),
        source_time_end=Fraction(48, 1_000),
        observed_substreams=observed,
        states={
            sense: (
                SenseBoundaryState.OBSERVED
                if sense in observed
                else SenseBoundaryState.SENSOR_UNAVAILABLE
            )
            for sense in SENSE_ORDER
        },
    )
    return ExactCausalExperienceOwner(
        on_settlement=lambda _settlement: None,
        log_event=lambda *_args, **_kwargs: None,
    ).settle(
        built,
        routing_chis=(),
        source_tags=(),
    )


def _execute(world, command, *, intent_digit: str):
    before = world.observation_snapshot()
    result = world.execute_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(command),
        causal_intent_receipt_sha256=intent_digit * 64,
        expected_revision=before.revision,
    )
    assert result.disposition == "applied"
    return result


def _contact_partition(
    *,
    world,
    physical,
    partitions,
    command,
    intent_digit: str,
):
    execution = _execute(
        world,
        command,
        intent_digit=intent_digit,
    )
    mount = physical.mount_action_outcome(execution)
    custody = SettledExperienceCustodyAuthority(
        authority_key=ACTION_CUSTODY_KEY,
        w1_physical_authority_key=EVIDENCE_KEY,
        world_authority_key=WORLD_KEY,
        profile=SettledExperienceCustodyProfile.create(
            profile_id="passive-reciprocal-contact",
            max_children=2,
            max_snapshot_bytes=64 * 1024 * 1024,
        ),
    )
    custody.admit(mount, execution)
    capability = custody.issue_child(THING_MOSAIC_CONSUMER_ID)
    return partitions.partition_from_custody(
        custody_authority=custody,
        capability=capability,
    )


def _learn_passive(
    *,
    world,
    owner,
    neuron_owner,
    settlement,
    window_id: str,
):
    neuron_owner.commit(neuron_owner.prepare(settlement))
    window = AnonymousPassiveWindowAuthority(
        authority_key=WINDOW_KEY,
        profile=AnonymousPassiveWindowProfile.create(
            profile_id=f"passive-reciprocal-window-{window_id}",
            max_mounts=1,
            max_state_bytes=64 * 1024 * 1024,
        ),
        world_authority=world,
    )
    prepared_window = window.prepare(
        window_id=window_id,
        settlement=settlement,
        world_observation=world.observation_snapshot(),
    )
    custody = SettledExperienceCustodyAuthority(
        authority_key=PASSIVE_CUSTODY_KEY,
        w1_physical_authority_key=EVIDENCE_KEY,
        world_authority_key=WORLD_KEY,
        anonymous_passive_window_authority_key=WINDOW_KEY,
        profile=SettledExperienceCustodyProfile.create(
            profile_id=f"passive-reciprocal-custody-{window_id}",
            max_children=2,
            max_snapshot_bytes=64 * 1024 * 1024,
        ),
    )
    custody.admit(prepared_window.mount)
    window.commit_prepared(prepared_window)
    capability = custody.issue_child(
        PASSIVE_THING_LEARNING_CONSUMER_ID
    )
    result = owner.admit(
        custody_authority=custody,
        custody_capability=capability,
    )
    assert result.state == "learned"
    assert result.record is not None
    return result.record


def _reciprocal(
    things,
    passive,
) -> CausalThingReciprocalMosaicOwner:
    return CausalThingReciprocalMosaicOwner(
        authority_key=RECIPROCAL_KEY,
        thing_owner=things,
        passive_learning_owner=passive,
        max_classes=4,
        max_roots_per_class=2_048,
        max_cue_roots=256,
    )


def _assert_full_fields(roots) -> None:
    assert roots
    for root in roots:
        root.verify()
        evidence = json.loads(root.full_evidence_json)
        for field_tuple in evidence["field_tuples"]:
            assert tuple(
                name for name, _value in field_tuple["fields"]
            ) == DSF_FIELD_ORDER


def test_passive_trace_recurrence_is_unique_unresolved_ambiguous_and_cold():
    world = _world(additional_objects=(
        EmbodiedObject(
            "second-object",
            radius_mm=100,
            mass_grams=400,
            position=PositionMM(300, 1_000, 0),
        ),
    ))
    physical = _physical_authority(world)
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
            profile_id="passive-reciprocal-things",
            max_mosaics=4,
            max_partitions_per_mosaic=4,
            max_roots_per_partition=256,
            max_routes=4_096,
            max_state_bytes=64 * 1024 * 1024,
        ),
        partition_authority=partitions,
    )
    passive_profile = PassiveThingLearningProfile.create(
        profile_id="passive-reciprocal-learning",
        max_records=4,
        max_roots_per_record=256,
        max_state_bytes=64 * 1024 * 1024,
    )
    neurons = _neuron_owner()
    passive = PassiveWholeOrganismThingLearningOwner(
        authority_key=LEARNING_KEY,
        profile=passive_profile,
        partition_authority=partitions,
        thing_owner=things,
        neuron_owner=neurons,
    )

    first_partition = _contact_partition(
        world=world,
        physical=physical,
        partitions=partitions,
        command=PickCommand("teaching-object", 200_000),
        intent_digit="2",
    )
    first_thing = things.admit_custody_genesis(first_partition)
    learned_trace = _trace_settlement("first-passive-trace")
    first_record = _learn_passive(
        world=world,
        owner=passive,
        neuron_owner=neurons,
        settlement=learned_trace,
        window_id="first-passive-trace",
    )

    reciprocal = _reciprocal(things, passive)
    unique = reciprocal.evoke(
        _trace_settlement("unique-recurrence"),
        cue_senses=("sound",),
    )
    assert unique.state == "unique"
    assert unique.thing_ids == (first_thing.thing_id,)
    assert unique.authority_scope == (
        "exact_experienced_trace_recurrence_only"
    )
    assert unique.final_recognition_authority is False
    assert unique.familiarity_authority is False
    assert unique.candidate is not None
    assert unique.candidate.partition_receipt_sha256s == (
        first_partition.authority_receipt_sha256,
    )
    assert unique.candidate.passive_record_receipt_sha256s == (
        first_record.authority_receipt_sha256,
    )
    assert (
        unique.candidate.legacy_sensory_expansion_receipt_sha256s
        == ()
    )
    assert first_record.full_field_roots
    assert set(first_record.full_field_roots).issubset(
        set(unique.evoked_full_field_roots)
    )
    _assert_full_fields(unique.evoked_full_field_roots)

    unresolved = reciprocal.evoke(
        _trace_settlement(
            "never-experienced-trace",
            altered_sound=True,
        ),
        cue_senses=("sound",),
    )
    assert unresolved.state == "unresolved"
    assert unresolved.thing_ids == ()
    assert unresolved.evoked_full_field_roots == ()
    assert unresolved.final_recognition_authority is False
    assert unresolved.familiarity_authority is False

    _execute(
        world,
        PlaceCommand(
            "teaching-object",
            PositionMM(1_600, 1_000, 0),
            200_000,
        ),
        intent_digit="3",
    )
    _execute(
        world,
        MoveCommand(
            PoseMM(PositionMM(700, 1_000, 0), 180_000),
            200_000,
        ),
        intent_digit="5",
    )
    second_partition = _contact_partition(
        world=world,
        physical=physical,
        partitions=partitions,
        command=PickCommand("second-object", 200_000),
        intent_digit="4",
    )
    second_thing = things.admit_custody_genesis(second_partition)
    second_record = _learn_passive(
        world=world,
        owner=passive,
        neuron_owner=neurons,
        settlement=_trace_settlement("second-passive-trace"),
        window_id="second-passive-trace",
    )
    assert second_thing.thing_id != first_thing.thing_id
    assert second_record.thing_id == second_thing.thing_id

    ambiguous = reciprocal.evoke(
        _trace_settlement("ambiguous-recurrence"),
        cue_senses=("sound",),
    )
    assert ambiguous.state == "ambiguous"
    assert ambiguous.thing_ids == tuple(sorted((
        first_thing.thing_id,
        second_thing.thing_id,
    )))
    assert ambiguous.candidate is None
    assert ambiguous.evoked_full_field_roots == ()
    assert ambiguous.final_recognition_authority is False
    assert ambiguous.familiarity_authority is False

    things_state = things.snapshot_encoded()
    passive_state = passive.snapshot_encoded()
    cold_things = restore_causal_thing_mosaic_owner(
        authority_key=PARTITION_KEY,
        partition_authority=partitions,
        encoded=things_state,
    )
    cold_passive = PassiveWholeOrganismThingLearningOwner.restore_encoded(
        authority_key=LEARNING_KEY,
        profile=passive_profile,
        partition_authority=partitions,
        thing_owner=cold_things,
        neuron_owner=neurons,
        encoded=passive_state,
    )
    assert cold_things.snapshot_encoded() == things_state
    assert cold_passive.snapshot_encoded() == passive_state

    cold_reciprocal = _reciprocal(cold_things, cold_passive)
    cold_ambiguous = cold_reciprocal.evoke(
        _trace_settlement("cold-ambiguous-recurrence"),
        cue_senses=("sound",),
    )
    assert cold_ambiguous.state == "ambiguous"
    assert cold_ambiguous.thing_ids == ambiguous.thing_ids
    assert cold_reciprocal.status() == {
        "authority_scope": "exact_experienced_trace_recurrence_only",
        "classes": 2,
        "experienced_variant_roots": sum(
            len(value.full_field_roots)
            for value in cold_reciprocal.classes()
        ),
        "familiarity_authority": False,
        "final_recognition_authority": False,
        "integrated_passive_records": 2,
        "legacy_sensory_expansions": 0,
        "max_classes": 4,
        "max_cue_roots": 256,
        "max_roots_per_class": 2_048,
        "schema": "guala.causal_thing.reciprocal_mosaic.status.v2",
        "signal_matching": False,
        "unseen_variant_guessing": False,
    }
