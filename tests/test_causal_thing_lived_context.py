from __future__ import annotations

import base64
import hashlib
import hmac
import json
from dataclasses import dataclass

import pytest

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    SENSE_ORDER,
)
from dsf_ai_service.substrate.causal_action_cycle import ActionCommand
from dsf_ai_service.substrate.causal_thing_action_execution import (
    CausalThingActionExecutionAuthority,
)
from dsf_ai_service.substrate.causal_thing_action_intent import (
    CausalThingActionIntentOwner,
    CausalThingActionIntentProfile,
)
from dsf_ai_service.substrate.causal_thing_lived_context import (
    _STATE_DOMAIN,
    CausalThingLivedContextOwner,
    CausalThingLivedContextResourceProfile,
)
from dsf_ai_service.substrate.causal_thing_mosaic import (
    CausalThingMosaicOwner,
    CausalThingMosaicProfile,
    ThingEncounterPartition,
)
from dsf_ai_service.substrate.causal_thing_mosaic_persistence import (
    restore_causal_thing_mosaic_owner,
)
from dsf_ai_service.substrate.causal_thing_sensory_expansion import (
    THING_SENSORY_EXPANSION_CONSUMER_ID,
    THING_SENSORY_GROUNDING_CONSUMER_ID,
    CausalThingSensoryExpansionOwner,
    RetainedAudiovisualCustodyAuthority,
)
from dsf_ai_service.substrate.custodied_thing_encounter import (
    THING_MOSAIC_CONSUMER_ID,
    CustodiedW1ContactThingEncounterAuthority,
)
from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
    SECOND_BODY_PORT_ID,
    EmbodimentWorldAuthority,
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
from dsf_ai_service.substrate.settled_experience_custody import (
    SettledExperienceCustody,
    SettledExperienceCustodyAuthority,
    SettledExperienceCustodyProfile,
)
from dsf_ai_service.substrate.w1_acoustic_emitter import (
    W1AcousticEmitterAuthority,
)
from dsf_ai_service.substrate.w1_anonymous_audiovisual_continuity import (
    W1AnonymousAudiovisualContinuityOwner,
)
from dsf_ai_service.substrate.w1_audiovisual_physical_evidence import (
    W1AudiovisualPhysicalEvidenceAuthority,
)
from dsf_ai_service.substrate.w1_binaural_auditory_l5 import (
    W1BinauralAuditoryL5Owner,
)
from dsf_ai_service.substrate.w1_physical_receptors import (
    EmbodimentSensoryOutcomeAuthority,
)
from tests.test_causal_thing_action_deliberation import (
    _close_relation,
    _owners,
)


WORLD_KEY = b"lived-context-world-authority-key"
PHYSICAL_KEY = b"lived-context-physical-authority-key"
CUSTODY_KEY = b"lived-context-custody-authority-key"
THING_KEY = b"lived-context-thing-authority-key"
CONTEXT_KEY = b"lived-context-owner-authority-key"
EMISSION_KEY = b"lived-context-emission-authority-key"
CONTINUITY_KEY = b"lived-context-av-continuity-key"
MEDIA_KEY = b"lived-context-media-authority-key"
ACTION_DURATION_MICROSECONDS = 200_000


@dataclass(slots=True)
class _System:
    world: EmbodimentWorldAuthority
    physical: W1AudiovisualPhysicalEvidenceAuthority
    partitions: CustodiedW1ContactThingEncounterAuthority
    things: CausalThingMosaicOwner
    context: CausalThingLivedContextOwner


def _profile(
    *,
    max_episodes: int = 16,
    max_events_per_episode: int = 16,
    max_total_events: int = 128,
    max_roots: int = 512,
    max_state_bytes: int = 8 * 1024 * 1024,
) -> CausalThingLivedContextResourceProfile:
    return CausalThingLivedContextResourceProfile.create(
        profile_id="production-causal-lived-context-v2-test",
        max_episodes=max_episodes,
        max_events_per_episode=max_events_per_episode,
        max_total_events=max_total_events,
        max_full_field_roots_per_event=max_roots,
        max_state_bytes=max_state_bytes,
    )


def _new_context(
    things: CausalThingMosaicOwner,
    *,
    profile: CausalThingLivedContextResourceProfile | None = None,
    expansions: CausalThingSensoryExpansionOwner | None = None,
    action_execution: CausalThingActionExecutionAuthority | None = None,
) -> CausalThingLivedContextOwner:
    return CausalThingLivedContextOwner(
        authority_key=CONTEXT_KEY,
        custody_authority_key=CUSTODY_KEY,
        w1_physical_authority_key=PHYSICAL_KEY,
        world_authority_key=WORLD_KEY,
        thing_owner=things,
        sensory_expansion_owner=expansions,
        resource_profile=profile or _profile(),
        action_execution_authority=action_execution,
    )


def _system(
    *,
    profile: CausalThingLivedContextResourceProfile | None = None,
) -> _System:
    world = EmbodimentWorldAuthority(authority_key=WORLD_KEY)
    physical = W1AudiovisualPhysicalEvidenceAuthority(
        authority_key=PHYSICAL_KEY,
        world_authority=world,
        causal_owner=ExactCausalExperienceOwner(
            on_settlement=lambda _settlement: None,
            log_event=lambda *_args, **_kwargs: None,
        ),
        acoustic_emitter=W1AcousticEmitterAuthority(
            authority_key=EMISSION_KEY,
            world_authority=world,
        ),
        binaural_auditory_l5_owner=W1BinauralAuditoryL5Owner(),
        anonymous_av_continuity_owner=(
            W1AnonymousAudiovisualContinuityOwner(
                authority_key=CONTINUITY_KEY,
                physical_authority_key=PHYSICAL_KEY,
            )
        ),
    )
    partitions = CustodiedW1ContactThingEncounterAuthority(
        authority_key=THING_KEY,
        world_authority=world,
        sensory_authority=EmbodimentSensoryOutcomeAuthority(
            authority_key=WORLD_KEY
        ),
        max_roots_per_partition=512,
    )
    things = CausalThingMosaicOwner(
        authority_key=THING_KEY,
        profile=CausalThingMosaicProfile.create(
            profile_id="lived-context-v2-THING-mosaics",
            max_mosaics=8,
            max_partitions_per_mosaic=32,
            max_roots_per_partition=512,
            max_routes=8_192,
            max_state_bytes=64 * 1024 * 1024,
        ),
        partition_authority=partitions,
    )
    return _System(
        world=world,
        physical=physical,
        partitions=partitions,
        things=things,
        context=_new_context(things, profile=profile),
    )


def _experience(
    system: _System,
    command,
    *,
    intent: int,
    port_id: str = PORT_ID,
) -> tuple[
    SettledExperienceCustodyAuthority,
    SettledExperienceCustody,
]:
    before = system.world.observation_snapshot()
    execution = system.world.execute_port_command(
        port_id=port_id,
        command_payload=encode_command(command),
        causal_intent_receipt_sha256=f"{intent:064x}",
        expected_revision=before.revision,
    )
    assert execution.disposition == "applied"
    mount = system.physical.mount_action_outcome(execution)
    authority = SettledExperienceCustodyAuthority(
        authority_key=CUSTODY_KEY,
        w1_physical_authority_key=PHYSICAL_KEY,
        world_authority_key=WORLD_KEY,
        profile=SettledExperienceCustodyProfile.create(
            profile_id=f"lived-context-v2-custody-{intent}",
            max_children=8,
            max_snapshot_bytes=64 * 1024 * 1024,
        ),
    )
    return authority, authority.admit(mount, execution)


def _partition(
    system: _System,
    authority: SettledExperienceCustodyAuthority,
    *,
    prior: ThingEncounterPartition | None = None,
) -> ThingEncounterPartition:
    capability = authority.issue_child(THING_MOSAIC_CONSUMER_ID)
    partition = system.partitions.partition_from_custody(
        custody_authority=authority,
        capability=capability,
        prior=prior,
    )
    system.things.admit(partition)
    return partition


def _admit(
    system: _System,
    authority: SettledExperienceCustodyAuthority,
    custody: SettledExperienceCustody,
    *,
    prior: ThingEncounterPartition | None = None,
) -> ThingEncounterPartition:
    partition = _partition(system, authority, prior=prior)
    system.context.admit(custody, durable_reference=partition)
    return partition


def _six_event_life() -> _System:
    system = _system()
    authority, custody = _experience(
        system,
        PickCommand("W1-object-1", ACTION_DURATION_MICROSECONDS),
        intent=1,
    )
    prior = _admit(system, authority, custody)
    for intent, x, y in (
        (2, 1_700, 1_000),
        (3, 1_700, 1_300),
    ):
        authority, custody = _experience(
            system,
            MoveCommand(
                PoseMM(PositionMM(x, y, 0), 0),
                ACTION_DURATION_MICROSECONDS,
            ),
            intent=intent,
        )
        prior = _admit(system, authority, custody, prior=prior)

    for intent, x, y in (
        (4, 1_800, 1_300),
        (5, 1_900, 1_200),
    ):
        authority, custody = _experience(
            system,
            MoveCommand(
                PoseMM(PositionMM(x, y, 0), 0),
                ACTION_DURATION_MICROSECONDS,
            ),
            intent=intent,
        )
        prior = _admit(system, authority, custody, prior=prior)
    other = next(
        body
        for body in system.world.observation_snapshot().bodies
        if body.body_id
        != system.world.observation_snapshot().self_body_id
    )
    authority, custody = _experience(
        system,
        MoveCommand(
            PoseMM(
                PositionMM(
                    other.pose.position.x - 100,
                    other.pose.position.y,
                    other.pose.position.z,
                ),
                other.pose.heading_millidegrees,
            ),
            ACTION_DURATION_MICROSECONDS,
        ),
        intent=6,
        port_id=SECOND_BODY_PORT_ID,
    )
    _admit(system, authority, custody, prior=prior)
    return system


def _payload(encoded: bytes) -> tuple[dict[str, object], dict[str, object]]:
    envelope = json.loads(encoded)
    body = json.loads(base64.b64decode(envelope["payload_base64"]))
    return envelope, body


def _resign(
    owner: CausalThingLivedContextOwner,
    body: dict[str, object],
) -> bytes:
    payload = json.dumps(
        body,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    envelope = {
        "authority_hmac_sha256": hmac.new(
            owner._state_key,
            _STATE_DOMAIN + payload,
            hashlib.sha256,
        ).hexdigest(),
        "payload_base64": base64.b64encode(payload).decode("ascii"),
        "schema": "guala.causal_thing_lived_context.state_hmac.v2",
    }
    return json.dumps(
        envelope,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def test_durable_life_retains_order_and_references_full_six_sense_roots():
    system = _six_event_life()
    events = tuple(
        event
        for episode in system.context.episodes
        for event in episode.events
    )

    assert len(events) == 6
    assert len(system.context.episodes) == 1
    assert tuple(event.world_revision for event in events) == (
        1,
        2,
        3,
        4,
        5,
        6,
    )
    assert events[0].continuity == "episode_genesis"
    assert events[1].continuity == "exact_world_transition"
    assert events[2].continuity == "exact_world_transition"
    assert all(
        event.continuity == "exact_world_transition"
        for event in events[1:]
    )
    assert events[-1].actor_body_provenance.role == "other"
    assert all(
        event.durable_reference_kind == "thing_partition"
        for event in events
    )
    assert len({
        event.durable_reference_receipt_sha256 for event in events
    }) == 6

    partitions = tuple(
        partition
        for mosaic in system.things.mosaics
        for partition in mosaic.partitions
    )
    for partition, event in zip(partitions, events, strict=True):
        assert event.full_field_root_count == len(
            partition.full_field_roots
        )
        assert event.matching_route_key_count == len(
            partition.full_field_roots
        )
        senses = {root.sense for root in partition.full_field_roots}
        assert senses
        assert senses.issubset({value.value for value in SENSE_ORDER})
        for root in partition.full_field_roots:
            evidence = json.loads(root.full_evidence_json)
            for item in evidence["field_tuples"]:
                assert tuple(
                    name for name, _value in item["fields"]
                ) == DSF_FIELD_ORDER


def test_state_is_lean_commitment_not_route_tuple_settlement_or_media():
    system = _six_event_life()
    encoded = system.context.snapshot_encoded()
    _envelope, body = _payload(encoded)
    body_text = json.dumps(body, separators=(",", ":"), sort_keys=True)

    assert '"matching_route_keys"' not in body_text
    assert '"matching_route_commitment_sha256"' in body_text
    assert '"transient_custody_archive":false' in body_text
    assert '"field_tuples"' not in body_text
    assert "raw_pcm" not in body_text
    assert "binaural_pcm" not in body_text
    assert "frame_b64" not in body_text
    assert "video" not in body_text
    assert "W1-object" not in body_text

    events = [
        event
        for episode in body["episodes"]
        for event in episode["events"]
    ]
    legacy_body = json.loads(json.dumps(body))
    legacy_events = [
        event
        for episode in legacy_body["episodes"]
        for event in episode["events"]
    ]
    partition_index = {
        partition.authority_receipt_sha256: partition
        for mosaic in system.things.mosaics
        for partition in mosaic.partitions
    }
    for event, legacy in zip(events, legacy_events, strict=True):
        partition = partition_index[
            event["durable_reference_receipt_sha256"]
        ]
        legacy["matching_route_keys"] = [
            list(root.route_key) for root in partition.full_field_roots
        ]
    projected_legacy = _resign(system.context, legacy_body)
    assert len(encoded) < len(projected_legacy)
    assert len(projected_legacy) - len(encoded) > 3_000 * len(events)
    assert len(encoded) / len(events) < 4_000


def test_prepare_discard_commit_rollback_and_replay_are_exact():
    system = _system()
    authority, custody = _experience(
        system,
        PickCommand("W1-object-1", ACTION_DURATION_MICROSECONDS),
        intent=21,
    )
    partition = _partition(system, authority)
    initial = system.context.snapshot_encoded()

    prepared = system.context.prepare_admission(
        custody,
        durable_reference=partition,
    )
    other_owner = _new_context(system.things)
    with pytest.raises(TypeError, match="prepared admission is not owned"):
        other_owner.commit_prepared_admission(prepared)
    assert system.context.snapshot_encoded() == initial
    system.context.discard_prepared_admission(prepared)
    assert system.context.snapshot_encoded() == initial

    prepared = system.context.prepare_admission(
        custody,
        durable_reference=partition,
    )
    undo = system.context.commit_prepared_admission(prepared)
    committed = system.context.snapshot_encoded()
    assert committed != initial
    system.context.rollback_committed_admission(undo)
    assert system.context.snapshot_encoded() == initial

    admitted = system.context.admit(
        custody,
        durable_reference=partition,
    )
    replay = system.context.admit(
        custody,
        durable_reference=partition,
    )
    assert admitted.state == "admitted"
    assert replay.state == "replayed"
    assert replay.event == admitted.event
    assert system.context.snapshot_encoded() == committed


def test_cold_restore_needs_no_custodies_and_fails_on_missing_reference():
    system = _system()
    authority, custody = _experience(
        system,
        PickCommand("W1-object-1", ACTION_DURATION_MICROSECONDS),
        intent=31,
    )
    prior = _admit(system, authority, custody)
    earlier_thing_state = system.things.snapshot_encoded()
    authority, custody = _experience(
        system,
        MoveCommand(
            PoseMM(PositionMM(1_700, 1_000, 0), 0),
            ACTION_DURATION_MICROSECONDS,
        ),
        intent=32,
    )
    _admit(system, authority, custody, prior=prior)
    encoded = system.context.snapshot_encoded()

    restored = CausalThingLivedContextOwner.restore_encoded(
        encoded,
        authority_key=CONTEXT_KEY,
        custody_authority_key=CUSTODY_KEY,
        w1_physical_authority_key=PHYSICAL_KEY,
        world_authority_key=WORLD_KEY,
        thing_owner=system.things,
    )
    assert restored.snapshot_encoded() == encoded
    assert restored.episodes == system.context.episodes

    incomplete = restore_causal_thing_mosaic_owner(
        authority_key=THING_KEY,
        partition_authority=system.partitions,
        encoded=earlier_thing_state,
    )
    with pytest.raises(
        ValueError,
        match="durable partition reference is absent",
    ):
        CausalThingLivedContextOwner.restore_encoded(
            encoded,
            authority_key=CONTEXT_KEY,
            custody_authority_key=CUSTODY_KEY,
            w1_physical_authority_key=PHYSICAL_KEY,
            world_authority_key=WORLD_KEY,
            thing_owner=incomplete,
        )

    envelope = json.loads(encoded)
    envelope["authority_hmac_sha256"] = "0" * 64
    tampered = json.dumps(
        envelope, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    with pytest.raises(ValueError, match="snapshot authority changed"):
        CausalThingLivedContextOwner.restore_encoded(
            tampered,
            authority_key=CONTEXT_KEY,
            custody_authority_key=CUSTODY_KEY,
            w1_physical_authority_key=PHYSICAL_KEY,
            world_authority_key=WORLD_KEY,
            thing_owner=system.things,
        )


def _move_action_graph():
    system = _system()
    authority, custody = _experience(
        system,
        PickCommand("W1-object-1", ACTION_DURATION_MICROSECONDS),
        intent=41,
    )
    first_partition = _partition(system, authority)
    held_world = system.world.encoded_snapshot()

    trained_authority, trained_custody = _experience(
        system,
        MoveCommand(
            PoseMM(PositionMM(1_600, 1_200, 0), 0),
            ACTION_DURATION_MICROSECONDS,
        ),
        intent=42,
    )
    trained_settlement = trained_custody.causal_settlement
    system.world.restore_encoded(held_world)

    current_authority, current_custody = _experience(
        system,
        MoveCommand(
            PoseMM(PositionMM(1_500, 1_100, 0), 0),
            ACTION_DURATION_MICROSECONDS,
        ),
        intent=43,
    )
    current_partition = _partition(
        system, current_authority, prior=first_partition
    )
    actions, _reciprocal, deliberation = _owners(system.things)
    command = ActionCommand.embodiment(
        PORT_ID,
        encode_command(
            MoveCommand(
                PoseMM(PositionMM(1_600, 1_200, 0), 0),
                ACTION_DURATION_MICROSECONDS,
            )
        ),
    )
    _close_relation(
        actions,
        trigger=first_partition.full_field_roots
        and current_custody.causal_settlement,
        outcome=trained_settlement,
        action=command,
        ordinal=44,
    )
    resolution = deliberation.resolve(
        current_custody.causal_settlement,
        cue_senses=("touch",),
    )
    assert resolution.state == "ready"
    intents = CausalThingActionIntentOwner(
        authority_key=CONTEXT_KEY,
        profile=CausalThingActionIntentProfile.create(
            profile_id="lived-context-v2-action-intent",
            max_live_intents=2,
            max_witness_bytes=4 * 1024 * 1024,
            max_state_bytes=32 * 1024 * 1024,
        ),
        deliberation_owner=deliberation,
    )
    intent = intents.issue(
        settlement=current_custody.causal_settlement,
        resolution=resolution,
    )
    executor = CausalThingActionExecutionAuthority(
        authority_key=CONTEXT_KEY,
        intent_owner=intents,
        world_authority=system.world,
        physical_authority=system.physical,
        custody_authority_key=CUSTODY_KEY,
        w1_physical_authority_key=PHYSICAL_KEY,
        world_authority_key=WORLD_KEY,
        custody_profile=SettledExperienceCustodyProfile.create(
            profile_id="lived-context-v2-action-custody",
            max_children=8,
            max_snapshot_bytes=64 * 1024 * 1024,
        ),
    )
    executed = executor.execute(intent=intent)
    capability = executed.custody_authority.issue_child(
        THING_MOSAIC_CONSUMER_ID
    )
    outcome_partition = system.partitions.partition_from_custody(
        custody_authority=executed.custody_authority,
        capability=capability,
        prior=current_partition,
    )
    system.things.admit(outcome_partition)
    return system, executor, executed, outcome_partition


def test_compact_action_journal_verifies_and_restores_exactly():
    system, executor, executed, partition = _move_action_graph()
    context = _new_context(
        system.things,
        action_execution=executor,
    )
    custody = executed.custody_authority.custody
    assert custody is not None
    admission = context.admit(
        custody,
        durable_reference=partition,
        action_consequence=executed.execution,
    )
    encoded = context.snapshot_encoded()
    _envelope, body = _payload(encoded)

    assert admission.event.action_consequence_receipt_sha256 == (
        executed.execution.authority_receipt_sha256
    )
    assert len(body["action_execution_records"]) == 1
    assert (
        context.resolve_action_execution(
            executed.execution.authority_receipt_sha256
        )
        == executed.execution
    )
    action_bytes = json.dumps(
        body["action_execution_records"][0],
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    assert len(action_bytes) < 2_048
    restored = CausalThingLivedContextOwner.restore_encoded(
        encoded,
        authority_key=CONTEXT_KEY,
        custody_authority_key=CUSTODY_KEY,
        w1_physical_authority_key=PHYSICAL_KEY,
        world_authority_key=WORLD_KEY,
        thing_owner=system.things,
        action_execution_authority=executor,
    )
    assert restored.snapshot_encoded() == encoded

    body["action_execution_records"] = []
    tampered = _resign(context, body)
    with pytest.raises(
        ValueError,
        match="action journal record is absent",
    ):
        CausalThingLivedContextOwner.restore_encoded(
            tampered,
            authority_key=CONTEXT_KEY,
            custody_authority_key=CUSTODY_KEY,
            w1_physical_authority_key=PHYSICAL_KEY,
            world_authority_key=WORLD_KEY,
            thing_owner=system.things,
            action_execution_authority=executor,
        )


def test_sensory_expansion_is_a_durable_reference_not_media_archive():
    system = _system()
    authority, custody = _experience(
        system,
        PickCommand("W1-object-1", ACTION_DURATION_MICROSECONDS),
        intent=51,
    )
    _partition(system, authority)
    _media_authority, media_occurrence = _experience(
        system,
        MoveCommand(
            PoseMM(PositionMM(1_700, 1_100, 0), 0),
            ACTION_DURATION_MICROSECONDS,
        ),
        intent=52,
    )
    media = RetainedAudiovisualCustodyAuthority(
        authority_key=MEDIA_KEY,
        max_live_occurrences=4,
        max_frames_per_occurrence=4,
    )
    media_custody = media.admit(
        settlement=media_occurrence.causal_settlement,
        frame_sha256s=("a" * 64,),
        canonical_audio_sha256=None,
    )
    media_capability = media.issue_child(
        media_custody,
        THING_SENSORY_EXPANSION_CONSUMER_ID,
    )
    contact_capability = authority.issue_child(
        THING_SENSORY_GROUNDING_CONSUMER_ID
    )
    expansions = CausalThingSensoryExpansionOwner(
        authority_key=THING_KEY,
        thing_owner=system.things,
        max_expansions=8,
        max_roots_per_expansion=512,
        max_state_bytes=8 * 1024 * 1024,
    )
    expansion = expansions.admit_lived_contact_tutor(
        custody_authority=media,
        custody_capability=media_capability,
        contact_custody_authority=authority,
        contact_custody_capability=contact_capability,
    )
    context = _new_context(system.things, expansions=expansions)
    admission = context.admit_expansion(
        expansion,
        custody_authority=media,
        custody_capability=media_capability,
    )
    encoded = context.snapshot_encoded()

    assert admission.event.durable_reference_kind == "sensory_expansion"
    assert admission.event.world_revision is None
    assert admission.event.thing_ids == (expansion.thing_id,)
    assert b"frame_sha256s" not in encoded
    assert b"canonical_audio_sha256" not in encoded
    restored = CausalThingLivedContextOwner.restore_encoded(
        encoded,
        authority_key=CONTEXT_KEY,
        custody_authority_key=CUSTODY_KEY,
        w1_physical_authority_key=PHYSICAL_KEY,
        world_authority_key=WORLD_KEY,
        thing_owner=system.things,
        sensory_expansion_owner=expansions,
    )
    assert restored.snapshot_encoded() == encoded


def test_root_and_state_capacity_refusal_publish_nothing():
    root_limited = _system(profile=_profile(max_roots=1))
    authority, custody = _experience(
        root_limited,
        PickCommand("W1-object-1", ACTION_DURATION_MICROSECONDS),
        intent=61,
    )
    partition = _partition(root_limited, authority)
    before = root_limited.context.snapshot_encoded()
    with pytest.raises(
        RuntimeError,
        match="field root capacity exhausted",
    ):
        root_limited.context.prepare_admission(
            custody,
            durable_reference=partition,
        )
    assert root_limited.context.snapshot_encoded() == before

    byte_limited = _system(
        profile=_profile(max_state_bytes=2_048)
    )
    authority, custody = _experience(
        byte_limited,
        PickCommand("W1-object-1", ACTION_DURATION_MICROSECONDS),
        intent=62,
    )
    partition = _partition(byte_limited, authority)
    before = byte_limited.context.snapshot_encoded()
    with pytest.raises(
        RuntimeError,
        match="state byte capacity exhausted",
    ):
        byte_limited.context.prepare_admission(
            custody,
            durable_reference=partition,
        )
    assert byte_limited.context.snapshot_encoded() == before
