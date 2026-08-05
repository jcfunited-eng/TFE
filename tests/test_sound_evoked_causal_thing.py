from __future__ import annotations

import json

import pytest

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.causal_thing_mosaic import (
    full_field_sensory_roots,
)
from dsf_ai_service.substrate.causal_thing_mosaic_persistence import (
    restore_causal_thing_mosaic_owner,
)
from dsf_ai_service.substrate.causal_thing_reciprocal_mosaic import (
    CausalThingReciprocalMosaicOwner,
)
from dsf_ai_service.substrate.causal_thing_sensory_expansion import (
    CausalThingSensoryExpansionOwner,
    RetainedAudiovisualCustodyAuthority,
    THING_SENSORY_EXPANSION_CONSUMER_ID,
    THING_SENSORY_GROUNDING_CONSUMER_ID,
)
from dsf_ai_service.substrate.embodiment_world import (
    MoveCommand,
    PickCommand,
    PlaceCommand,
    PoseMM,
    PositionMM,
)
from dsf_ai_service.substrate.live_sound_cue_custody import (
    LIVE_SOUND_CUE_SOURCE_CONSUMER_ID,
    LiveSoundCueCustodyAuthority,
)
from dsf_ai_service.substrate.settled_experience_custody import (
    SettledExperienceCustodyAuthority,
    SettledExperienceCustodyProfile,
)
from dsf_ai_service.substrate.sound_evoked_causal_thing import (
    SoundEvokedCausalThingAuthority,
)
from tests.test_causal_thing_lived_context import (
    ACTION_DURATION_MICROSECONDS,
    MEDIA_KEY,
    THING_KEY,
    _experience,
    _partition,
    _system,
)
from tests.test_lived_vocal_teaching_episode import (
    _external_mount,
    _modulated_tone_pcm,
)
from tests.test_w1_audiovisual_physical_evidence import (
    EVIDENCE_KEY,
    WORLD_KEY,
    _authority,
    _world,
)


CUE_KEY = b"live-sound-cue-focused-production-authority-key"
RESULT_KEY = b"sound-evoked-thing-focused-production-authority-key"
SOURCE_KEY = b"sound-cue-source-settled-custody-authority-key"


def _reciprocal(things, expansions=None):
    return CausalThingReciprocalMosaicOwner(
        authority_key=THING_KEY,
        thing_owner=things,
        sensory_expansion_owner=expansions,
        max_classes=8,
        max_roots_per_class=2_048,
        max_cue_roots=512,
    )


def _expansions(things):
    return CausalThingSensoryExpansionOwner(
        authority_key=THING_KEY,
        thing_owner=things,
        max_expansions=8,
        max_roots_per_expansion=512,
        max_state_bytes=64 * 1024 * 1024,
    )


def _sound_occurrences(*amplitudes):
    world = _world()
    physical = _authority(world)
    return tuple(
        _external_mount(
            world,
            physical,
            _modulated_tone_pcm(amplitude),
        )
        for amplitude in amplitudes
    )


def _media_custody(media, settlement, ordinal):
    custody = media.admit(
        settlement=settlement,
        frame_sha256s=(f"{ordinal:x}" * 64,),
        canonical_audio_sha256=f"{ordinal + 8:x}" * 64,
    )
    return media.issue_child(
        custody,
        THING_SENSORY_EXPANSION_CONSUMER_ID,
    )


def _thing_for_partition(things, partition):
    return next(
        mosaic
        for mosaic in things.mosaics
        if partition in mosaic.partitions
    )


def _direct_evocation(reciprocal, settlement):
    cue_owner = LiveSoundCueCustodyAuthority(
        authority_key=CUE_KEY,
        max_sound_roots=512,
    )
    cue = cue_owner.admit_verified_settlement(settlement)
    capability = cue_owner.issue_recall(cue)
    authority = SoundEvokedCausalThingAuthority(
        authority_key=RESULT_KEY,
        reciprocal_owner=reciprocal,
    )
    result = authority.evoke(
        custody_authority=cue_owner,
        custody_capability=capability,
    )
    authority.verify(result)
    return cue_owner, cue, capability, result


def test_direct_settlement_returns_unique_unresolved_and_ambiguous() -> None:
    system = _system()
    contact_one, contact_one_value = _experience(
        system,
        PickCommand(
            "W1-object-1",
            ACTION_DURATION_MICROSECONDS,
        ),
        intent=101,
    )
    partition_one = _partition(system, contact_one)
    thing_one = _thing_for_partition(system.things, partition_one)
    (
        (_learned_one_execution, learned_one),
        (_unique_execution, unique_cue),
        (_unknown_execution, unknown_cue),
        (_learned_two_execution, learned_two),
        (_ambiguous_execution, ambiguous_cue),
    ) = _sound_occurrences(11_000, 11_000, 8_000, 11_000, 11_000)

    media = RetainedAudiovisualCustodyAuthority(
        authority_key=MEDIA_KEY,
        max_live_occurrences=8,
        max_frames_per_occurrence=4,
    )
    expansions = _expansions(system.things)
    learned_one_capability = _media_custody(
        media,
        learned_one.causal_settlement,
        1,
    )
    contact_one_capability = contact_one.issue_child(
        THING_SENSORY_GROUNDING_CONSUMER_ID
    )
    first_expansion = expansions.admit_lived_contact_tutor(
        custody_authority=media,
        custody_capability=learned_one_capability,
        contact_custody_authority=contact_one,
        contact_custody_capability=contact_one_capability,
    )
    assert first_expansion.thing_id == thing_one.thing_id

    reciprocal = _reciprocal(system.things, expansions)
    cue_owner, cue, capability, unique = _direct_evocation(
        reciprocal,
        unique_cue.causal_settlement,
    )
    exact_sound_roots = tuple(
        root
        for root in full_field_sensory_roots(
            unique_cue.causal_settlement
        )
        if root.sense == "sound"
    )
    assert unique.state == "unique"
    assert unique.thing_ids == (thing_one.thing_id,)
    assert unique.cue_roots == exact_sound_roots == cue.sound_roots
    assert unique.evoked_full_field_roots == (
        reciprocal.classes()[0].full_field_roots
    )
    assert {
        root.sense for root in unique.evoked_full_field_roots
    } >= {"body", "sight", "sound", "touch"}
    assert all(
        tuple(name for name, _value in field_tuple["fields"])
        == DSF_FIELD_ORDER
        for root in unique.evoked_full_field_roots
        for field_tuple in json.loads(root.full_evidence_json)[
            "field_tuples"
        ]
    )
    assert cue.source_kind == "verified_causal_settlement"
    assert cue.source_parent_receipt_sha256 == (
        unique_cue.causal_settlement.authority_receipt_sha256
    )
    assert cue_owner.status() == {
        "available_cues": 0,
        "cold_state_persisted": False,
        "consumed": True,
        "max_live_cues": 1,
        "max_sound_roots": 512,
        "raw_pressure_bytes_retained": 0,
        "schema": "guala.live_sound_cue.status.v1",
    }
    assert "pcm" not in json.dumps(cue.payload()).lower()
    assert "frame" not in json.dumps(cue.payload()).lower()
    with pytest.raises(
        RuntimeError,
        match="no longer available",
    ):
        SoundEvokedCausalThingAuthority(
            authority_key=RESULT_KEY,
            reciprocal_owner=reciprocal,
        ).evoke(
            custody_authority=cue_owner,
            custody_capability=capability,
        )

    _unknown_owner, _unknown_custody, _unknown_capability, unknown = (
        _direct_evocation(
            reciprocal,
            unknown_cue.causal_settlement,
        )
    )
    assert unknown.state == "unresolved"
    assert unknown.thing_ids == ()
    assert unknown.evoked_full_field_roots == ()

    thing_state = system.things.snapshot_encoded()
    expansion_state = expansions.snapshot_encoded()
    restored_things = restore_causal_thing_mosaic_owner(
        authority_key=THING_KEY,
        partition_authority=system.partitions,
        encoded=thing_state,
    )
    restored_expansions = _expansions(restored_things)
    restored_expansions.restore_encoded(expansion_state)
    restored_reciprocal = _reciprocal(
        restored_things,
        restored_expansions,
    )
    _cold_owner, _cold_custody, _cold_capability, cold = (
        _direct_evocation(
            restored_reciprocal,
            unique_cue.causal_settlement,
        )
    )
    assert cold.state == "unique"
    assert cold.thing_ids == (thing_one.thing_id,)
    assert not hasattr(
        LiveSoundCueCustodyAuthority,
        "restore_encoded",
    )
    assert not hasattr(
        SoundEvokedCausalThingAuthority,
        "restore_encoded",
    )

    _place_authority, _place_value = _experience(
        system,
        PlaceCommand(
            "W1-object-1",
            PositionMM(1_000, 1_700, 0),
            ACTION_DURATION_MICROSECONDS,
        ),
        intent=102,
    )
    _move_authority, _move_value = _experience(
        system,
        MoveCommand(
            PoseMM(PositionMM(2_000, 1_000, 0), 0),
            ACTION_DURATION_MICROSECONDS,
        ),
        intent=103,
    )
    contact_two, contact_two_value = _experience(
        system,
        PickCommand(
            "W1-object-2",
            ACTION_DURATION_MICROSECONDS,
        ),
        intent=104,
    )
    partition_two = _partition(system, contact_two)
    thing_two = _thing_for_partition(system.things, partition_two)
    learned_two_capability = _media_custody(
        media,
        learned_two.causal_settlement,
        2,
    )
    contact_two_capability = contact_two.issue_child(
        THING_SENSORY_GROUNDING_CONSUMER_ID
    )
    second_expansion = expansions._admit(
        custody_authority=media,
        custody_capability=learned_two_capability,
        thing_id=thing_two.thing_id,
        admission_basis="lived_contact_tutor",
        grounding_partition_receipt_sha256=(
            partition_two.authority_receipt_sha256
        ),
        grounding_contact_occurrence_id=(
            contact_two_value.source_occurrence_id
        ),
        grounding_contact_custody_receipt_sha256=(
            contact_two_value.authority_receipt_sha256
        ),
        grounding_contact_capability_receipt_sha256=(
            contact_two_capability.authority_receipt_sha256
        ),
        grounding_contact_settlement_receipt_sha256=(
            contact_two_value.causal_settlement
            .authority_receipt_sha256
        ),
        prior_expansion_receipt_sha256s=(),
    )
    assert second_expansion.thing_id == thing_two.thing_id
    assert thing_two.thing_id != thing_one.thing_id

    ambiguous_reciprocal = _reciprocal(
        system.things,
        expansions,
    )
    _amb_owner, _amb_custody, _amb_capability, ambiguous = (
        _direct_evocation(
            ambiguous_reciprocal,
            ambiguous_cue.causal_settlement,
        )
    )
    assert ambiguous.state == "ambiguous"
    assert ambiguous.thing_ids == tuple(sorted((
        thing_one.thing_id,
        thing_two.thing_id,
    )))
    assert ambiguous.evoked_full_field_roots == ()


def test_typed_source_capability_and_bounds_are_enforced() -> None:
    (
        (execution, mount),
        (_other_execution, other_mount),
    ) = _sound_occurrences(9_000, 7_000)
    source = SettledExperienceCustodyAuthority(
        authority_key=SOURCE_KEY,
        w1_physical_authority_key=EVIDENCE_KEY,
        world_authority_key=WORLD_KEY,
        profile=SettledExperienceCustodyProfile.create(
            profile_id="live-sound-cue-focused-source",
            max_children=4,
            max_snapshot_bytes=64 * 1024 * 1024,
        ),
    )
    source.admit(mount, execution)
    wrong = source.issue_child("another-consumer")
    cue_owner = LiveSoundCueCustodyAuthority(
        authority_key=CUE_KEY,
        max_sound_roots=512,
    )
    with pytest.raises(
        ValueError,
        match="dedicated settled capability",
    ):
        cue_owner.admit(
            custody_authority=source,
            custody_capability=wrong,
        )

    source_capability = source.issue_child(
        LIVE_SOUND_CUE_SOURCE_CONSUMER_ID
    )
    cue = cue_owner.admit(
        custody_authority=source,
        custody_capability=source_capability,
    )
    assert cue.source_kind == "settled_experience_capability"
    assert cue.source_authority_receipt_sha256 == (
        source_capability.authority_receipt_sha256
    )
    assert cue.sound_roots
    with pytest.raises(
        RuntimeError,
        match="capacity is full",
    ):
        cue_owner.admit_verified_settlement(
            other_mount.causal_settlement
        )

    root_limited = LiveSoundCueCustodyAuthority(
        authority_key=CUE_KEY,
        max_sound_roots=1,
    )
    with pytest.raises(
        RuntimeError,
        match="root capacity exhausted",
    ):
        root_limited.admit_verified_settlement(
            mount.causal_settlement
        )
    assert root_limited.status()["available_cues"] == 0
    assert root_limited.status()["raw_pressure_bytes_retained"] == 0
