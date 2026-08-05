"""A real spoken occurrence becomes one reciprocal multisensory mosaic.

The test supplies no word, transcript, semantic label, signal comparison, or
preferred sensory lane.  A physical hold transition provides target
continuity.  A later external vocal occurrence contributes its complete sound
field to the same lived causal chain.  Exact recurrence from either sight or
sound must awaken the same retained mosaic after cold restoration.
"""

from __future__ import annotations

import json
from pathlib import Path
import wave

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
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
from tests.test_custodied_thing_encounter import (
    KEY,
    _custody_for,
    _partition_authority,
)
from tests.test_lived_vocal_teaching_episode import _external_mount
from tests.test_w1_audiovisual_physical_evidence import (
    EVIDENCE_KEY,
    WORLD_KEY,
    _authority,
    _execution,
    _world,
)


_RECIPROCAL_KEY = b"label-free-multisensory-word-reciprocal-key"
_RECORDING = Path(
    "dsf_ai_service/curriculum/assets/speech_commands/"
    "go/022cd682_nohash_0.wav"
)


def _pcm() -> bytes:
    with wave.open(str(_RECORDING), "rb") as source:
        assert (
            source.getnchannels(),
            source.getsampwidth(),
            source.getframerate(),
        ) == (1, 2, 16_000)
        return source.readframes(source.getnframes())


def _owner(partitions) -> CausalThingMosaicOwner:
    return CausalThingMosaicOwner(
        authority_key=KEY,
        profile=CausalThingMosaicProfile.create(
            profile_id="label-free-multisensory-word-mosaic-v1",
            max_mosaics=4,
            max_partitions_per_mosaic=8,
            max_roots_per_partition=256,
            max_routes=4_096,
            max_state_bytes=128 * 1024 * 1024,
        ),
        partition_authority=partitions,
    )


def _reciprocal(owner) -> CausalThingReciprocalMosaicOwner:
    return CausalThingReciprocalMosaicOwner(
        authority_key=_RECIPROCAL_KEY,
        thing_owner=owner,
        max_classes=4,
        max_roots_per_class=4_096,
        max_cue_roots=1_024,
    )


def _partition_from_mount(
    partitions,
    mount,
    execution,
    *,
    prior=None,
):
    custody, _retained, capability = _custody_for(
        mount,
        execution,
        physical_key=EVIDENCE_KEY,
        world_key=WORLD_KEY,
    )
    return partitions.partition_from_custody(
        custody_authority=custody,
        capability=capability,
        prior=prior,
    )


def _assert_complete_fields(roots) -> None:
    for root in roots:
        evidence = json.loads(root.full_evidence_json)
        for field_tuple in evidence["field_tuples"]:
            assert tuple(
                field_name
                for field_name, _field_value in field_tuple["fields"]
            ) == DSF_FIELD_ORDER


def test_real_sight_and_sound_form_one_cold_reciprocal_mosaic() -> None:
    world = _world()
    physical = _authority(world)
    partitions = _partition_authority(
        world,
        sensory_key=EVIDENCE_KEY,
    )
    things = _owner(partitions)

    pick_execution = _execution(world)
    pick_mount = physical.mount_action_outcome(pick_execution)
    first = _partition_from_mount(
        partitions,
        pick_mount,
        pick_execution,
    )
    genesis = things.admit(first)

    vocal_execution, vocal_mount = _external_mount(
        world,
        physical,
        _pcm(),
    )
    second = _partition_from_mount(
        partitions,
        vocal_mount,
        vocal_execution,
        prior=first,
    )
    learned = things.admit(second)

    senses = {
        root.sense
        for partition in learned.partitions
        for root in partition.full_field_roots
    }
    assert learned.thing_id == genesis.thing_id
    assert {"sight", "sound"}.issubset(senses)
    assert len(senses) >= 2
    assert second.prior_partition_receipt_sha256 == (
        first.authority_receipt_sha256
    )
    assert second.world_revision == first.world_revision + 1
    assert second.entity_continuity_hmac_sha256 == (
        first.entity_continuity_hmac_sha256
    )
    _assert_complete_fields(
        tuple(
            root
            for partition in learned.partitions
            for root in partition.full_field_roots
        )
    )

    encoded = things.snapshot_encoded()
    for forbidden in (
        b'"label"',
        b'"meaning"',
        b'"transcript"',
        b"022cd682",
    ):
        assert forbidden not in encoded

    restored = restore_causal_thing_mosaic_owner(
        authority_key=KEY,
        encoded=encoded,
        partition_authority=partitions,
    )
    reciprocal = _reciprocal(restored)

    replay_execution, replay_mount = _external_mount(
        world,
        physical,
        _pcm(),
    )
    from_sound = reciprocal.evoke(
        replay_mount.causal_settlement,
        cue_senses=("sound",),
    )
    from_sight = reciprocal.evoke(
        pick_mount.causal_settlement,
        cue_senses=("sight",),
    )

    assert from_sound.state == from_sight.state == "unique"
    assert from_sound.thing_ids == from_sight.thing_ids == (
        learned.thing_id,
    )
    assert from_sound.candidate == from_sight.candidate
    assert {
        root.sense for root in from_sound.evoked_full_field_roots
    }.issuperset({"sight", "sound"})
    assert {
        root.sense for root in from_sight.evoked_full_field_roots
    }.issuperset({"sight", "sound"})
    assert replay_execution.after.revision == (
        vocal_execution.after.revision + 1
    )
