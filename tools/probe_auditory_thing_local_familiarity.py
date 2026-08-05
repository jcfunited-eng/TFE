"""Fixed first walk-up for local auditory-to-THING familiarity.

The canonical familiarity owner receives no corpus word or speaker identity.
This probe uses oracle metadata only to construct the fixed source-disjoint
training/held-out split and to score completed resolutions.

Each THING is physically picked and then remains held through three external
vocal occurrences.  Every vocal occurrence becomes a continuation partition
of that same authenticated causal THING mosaic.  One shared binaural q bank
grows from all nine physical training occurrences.  Only after growth
completes are its local ordered activations bound back to their exact
co-occurring THING partitions.

The six held-out occurrences fire without learning.  Unknown and ambiguous
results release no THING.  This configuration is fixed before oracle
evaluation and is not tuned after results are observed.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from dataclasses import dataclass

from dsf_ai_service.substrate.auditory_recurrent_motif import (
    AuditoryMotifResourceProfile,
    AuditoryRecurrentMotifOwner,
)
from dsf_ai_service.substrate.auditory_thing_familiarity import (
    AuditoryThingFamiliarityOwner,
    AuditoryThingFamiliarityProfile,
)
from dsf_ai_service.substrate.causal_thing_mosaic import (
    CausalThingMosaic,
    CausalThingMosaicOwner,
    CausalThingMosaicProfile,
    ThingEncounterPartition,
)
from dsf_ai_service.substrate.custodied_thing_encounter import (
    CustodiedW1ContactThingEncounterAuthority,
    THING_MOSAIC_CONSUMER_ID,
)
from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
    EmbodiedBody,
    EmbodiedObject,
    EmbodimentPort,
    EmbodimentWorldAuthority,
    MoveCommand,
    PickCommand,
    PlaceCommand,
    PoseMM,
    PositionMM,
    encode_command,
)
from dsf_ai_service.substrate.settled_experience_custody import (
    SettledExperienceCustodyAuthority,
    SettledExperienceCustodyProfile,
)
from dsf_ai_service.substrate.w1_physical_receptors import (
    EmbodimentSensoryOutcomeAuthority,
)
from tests.test_lived_vocal_teaching_episode import _external_mount
from tests.test_w1_audiovisual_physical_evidence import (
    EMITTER_PORT,
    EVIDENCE_KEY,
    WORLD_KEY,
    _authority as _physical_authority,
)
from tools.probe_vtvr_causal_thing_familiarity import (
    ARCHIVE_PATH,
    ARCHIVE_SHA256,
    HELD_OUT_SPEAKERS_PER_THING,
    TRAINING_SPEAKERS_PER_THING,
    WORDS,
    SpeechItem,
    _archive_sha256,
    _items,
)


SCHEMA = "guala.audit.auditory_thing_local_familiarity_walkup.v1"
AUTHORITY_KEY = b"guala-auditory-thing-local-familiarity-20260727"
OBJECT_IDS = tuple(
    f"auditory-familiarity-object-{index}"
    for index in range(1, len(WORDS) + 1)
)


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _world() -> EmbodimentWorldAuthority:
    return EmbodimentWorldAuthority(
        authority_key=WORLD_KEY,
        bodies=(
            EmbodiedBody(
                "external-body",
                PoseMM(PositionMM(3_500, 2_500, 0), 180_000),
                radius_mm=200,
                reach_mm=600,
            ),
            EmbodiedBody(
                "guala-body-1",
                PoseMM(PositionMM(1_000, 1_000, 0), 0),
                radius_mm=250,
                reach_mm=800,
            ),
        ),
        actor_ports=(
            EmbodimentPort(PORT_ID, "guala-body-1"),
            EmbodimentPort(EMITTER_PORT, "external-body"),
        ),
        initial_objects=tuple(
            EmbodiedObject(
                object_id,
                radius_mm=(100, 80, 120)[index],
                mass_grams=(500, 350, 700)[index],
                position=PositionMM(1_500 + 1_000 * index, 1_000, 0),
            )
            for index, object_id in enumerate(OBJECT_IDS)
        ),
    )


def _execute(
    world: EmbodimentWorldAuthority,
    command: object,
    *,
    causal_ordinal: int,
):
    before = world.observation_snapshot()
    result = world.execute_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(command),
        causal_intent_receipt_sha256=hashlib.sha256(
            f"auditory-familiarity-action:{causal_ordinal}".encode(
                "ascii"
            )
        ).hexdigest(),
        expected_revision=before.revision,
    )
    if result.disposition != "applied":
        raise RuntimeError(
            "auditory familiarity physical action was not applied: "
            f"{result.reason}"
        )
    return result


def _custody(
    *,
    source_mount,
    execution,
    ordinal: int,
) -> SettledExperienceCustodyAuthority:
    authority = SettledExperienceCustodyAuthority(
        authority_key=(
            AUTHORITY_KEY
            + b":custody:"
            + str(ordinal).encode("ascii")
        ),
        w1_physical_authority_key=EVIDENCE_KEY,
        world_authority_key=WORLD_KEY,
        profile=SettledExperienceCustodyProfile.create(
            profile_id=f"auditory-familiarity-custody-{ordinal}",
            max_children=2,
            max_snapshot_bytes=128 * 1024 * 1024,
        ),
    )
    authority.admit(source_mount, execution)
    return authority


def _motif_owner() -> AuditoryRecurrentMotifOwner:
    return AuditoryRecurrentMotifOwner(
        AuditoryMotifResourceProfile.create(
            profile_id="auditory-thing-local-familiarity-q",
            ear_count=2,
            max_motif_neurons=24_192,
            max_pending_experiences=32,
            max_work_cells_per_observation=8_000_000,
            max_exact_fraction_text_bytes=4_096,
            encoded_state_allocation_bytes=128 * 1024 * 1024,
        ),
        ear_ids=("left", "right"),
    )


@dataclass(frozen=True, slots=True)
class _TrainingOccurrence:
    oracle_word: str
    item: SpeechItem
    partition: ThingEncounterPartition
    receptor_settlement: object


def run_probe() -> dict[str, object]:
    archive_sha256 = _archive_sha256(ARCHIVE_PATH)
    if archive_sha256 != ARCHIVE_SHA256:
        raise RuntimeError("authenticated speech archive changed")
    with zipfile.ZipFile(ARCHIVE_PATH) as archive:
        corpus = {
            word: _items(
                archive,
                word=word,
                count=(
                    TRAINING_SPEAKERS_PER_THING
                    + HELD_OUT_SPEAKERS_PER_THING
                ),
            )
            for word in WORDS
        }

    world = _world()
    physical = _physical_authority(world)
    sensory = EmbodimentSensoryOutcomeAuthority(
        authority_key=EVIDENCE_KEY
    )
    partitions = CustodiedW1ContactThingEncounterAuthority(
        authority_key=AUTHORITY_KEY,
        world_authority=world,
        sensory_authority=sensory,
        max_roots_per_partition=256,
    )
    things = CausalThingMosaicOwner(
        authority_key=AUTHORITY_KEY,
        profile=CausalThingMosaicProfile.create(
            profile_id="auditory-local-familiarity-things",
            max_mosaics=len(WORDS),
            max_partitions_per_mosaic=(
                TRAINING_SPEAKERS_PER_THING + 1
            ),
            max_roots_per_partition=256,
            max_routes=32_768,
            max_state_bytes=512 * 1024 * 1024,
        ),
        partition_authority=partitions,
    )
    q_owner = _motif_owner()
    training: list[_TrainingOccurrence] = []
    mosaics: dict[str, CausalThingMosaic] = {}
    action_ordinal = 0
    custody_ordinal = 0

    for thing_ordinal, (word, object_id) in enumerate(
        zip(WORDS, OBJECT_IDS, strict=True),
        start=1,
    ):
        approach_x = 1_000 * thing_ordinal
        if thing_ordinal > 1:
            for waypoint in (
                PositionMM(1_000, 2_000, 0),
                PositionMM(approach_x, 2_000, 0),
                PositionMM(approach_x, 1_000, 0),
            ):
                action_ordinal += 1
                _execute(
                    world,
                    MoveCommand(PoseMM(waypoint, 0)),
                    causal_ordinal=action_ordinal,
                )
        action_ordinal += 1
        picked = _execute(
            world,
            PickCommand(object_id),
            causal_ordinal=action_ordinal,
        )
        pick_mount = physical.mount_action_outcome(picked)
        custody_ordinal += 1
        pick_custody = _custody(
            source_mount=pick_mount,
            execution=picked,
            ordinal=custody_ordinal,
        )
        prior = partitions.partition_from_custody(
            custody_authority=pick_custody,
            capability=pick_custody.issue_child(
                THING_MOSAIC_CONSUMER_ID
            ),
        )
        mosaic = things.admit(prior)

        for item in corpus[word][:TRAINING_SPEAKERS_PER_THING]:
            execution, mount = _external_mount(
                world,
                physical,
                item.pcm_s16le,
            )
            q_owner.observe_binaural(
                mount.binaural_receptor_settlement
            )
            custody_ordinal += 1
            vocal_custody = _custody(
                source_mount=mount,
                execution=execution,
                ordinal=custody_ordinal,
            )
            prior = partitions.partition_from_custody(
                custody_authority=vocal_custody,
                capability=vocal_custody.issue_child(
                    THING_MOSAIC_CONSUMER_ID
                ),
                prior=prior,
            )
            mosaic = things.admit(prior)
            training.append(_TrainingOccurrence(
                oracle_word=word,
                item=item,
                partition=prior,
                receptor_settlement=(
                    mount.binaural_receptor_settlement
                ),
            ))
        mosaics[word] = mosaic

        if thing_ordinal < len(WORDS):
            action_ordinal += 1
            _execute(
                world,
                PlaceCommand(
                    object_id,
                    PositionMM(
                        approach_x - 500,
                        1_000,
                        0,
                    ),
                ),
                causal_ordinal=action_ordinal,
            )

    familiarity = AuditoryThingFamiliarityOwner(
        authority_key=AUTHORITY_KEY,
        profile=AuditoryThingFamiliarityProfile.create(
            profile_id="auditory-thing-local-familiarity",
            max_things=len(WORDS),
            max_episodes=(
                len(WORDS) * TRAINING_SPEAKERS_PER_THING
            ),
            max_partitions_per_episode=32_768,
            max_motifs_per_episode=65_536,
            max_occurrence_records=100_000,
            max_state_bytes=512 * 1024 * 1024,
        ),
        thing_owner=things,
    )
    admissions = []
    for occurrence in training:
        firing = q_owner.fire_binaural(
            occurrence.receptor_settlement
        )
        admission = familiarity.admit(
            firing=firing,
            receptor_settlement=occurrence.receptor_settlement,
            mosaic=mosaics[occurrence.oracle_word],
            partition=occurrence.partition,
        )
        admissions.append({
            "archive_member_for_oracle_audit": (
                occurrence.item.archive_member
            ),
            "firing_activation_count": len(firing.activations),
            "fissioned_motif_count": (
                admission.fissioned_motif_count
            ),
            "grown_motif_count": admission.grown_motif_count,
            "oracle_speaker_for_audit": (
                occurrence.item.speaker_id
            ),
            "oracle_word_for_audit": occurrence.oracle_word,
            "state": admission.state.value,
            "thing_id": mosaics[
                occurrence.oracle_word
            ].thing_id,
        })

    held_out = []
    correct = 0
    for word in WORDS:
        expected = mosaics[word].thing_id
        for item in corpus[word][TRAINING_SPEAKERS_PER_THING:]:
            _execution, mount = _external_mount(
                world,
                physical,
                item.pcm_s16le,
            )
            firing = q_owner.fire_binaural(
                mount.binaural_receptor_settlement
            )
            resolution = familiarity.resolve(firing)
            passed = resolution.released_thing_id == expected
            correct += int(passed)
            held_out.append({
                "archive_member": item.archive_member,
                "expected_thing_id": expected,
                "firing_activation_count": len(firing.activations),
                "locked_thing_ids": list(
                    resolution.locked_thing_ids
                ),
                "oracle_speaker": item.speaker_id,
                "oracle_word": word,
                "passed": passed,
                "released_thing_id": (
                    resolution.released_thing_id
                ),
                "resolution_authority_receipt_sha256": (
                    resolution.authority_receipt_sha256
                ),
                "state": resolution.state.value,
            })

    report = {
        "admission_records": admissions,
        "archive_sha256": archive_sha256,
        "claim_allowed": correct == len(held_out),
        "correct": correct,
        "familiarity_status": familiarity.status(),
        "full_field_occurrence_witnesses_retained": True,
        "held_out": held_out,
        "held_out_count": len(held_out),
        "learning_boundary_received_speaker_ids": False,
        "learning_boundary_received_words": False,
        "local_motif_rule": (
            "all run-collapsed local q events and all adjacent ordered "
            "event pairs"
        ),
        "memory_records": [
            {
                "episode_count": memory.version,
                "memory_receipt_sha256": (
                    memory.authority_receipt_sha256
                ),
                "quiescent_motif_count": len(
                    memory.quiescent_motifs
                ),
                "recurrent_motif_count": len(
                    memory.recurrent_motif_supports
                ),
                "required_motif_count": len(
                    memory.required_motifs
                ),
                "thing_id": memory.thing_id,
            }
            for memory in familiarity.memories
        ],
        "motif_owner_status": q_owner.status(),
        "oracle_thing_map": {
            mosaics[word].thing_id: word for word in WORDS
        },
        "recognition_governance": (
            "canonical L6 over exact fissioned local motif populations"
        ),
        "schema": SCHEMA,
        "training_encounter_count": len(training),
        "training_speakers_per_thing": (
            TRAINING_SPEAKERS_PER_THING
        ),
    }
    return report | {
        "authority_receipt_sha256": _digest(report),
    }


if __name__ == "__main__":
    print(json.dumps(run_probe(), indent=2, sort_keys=True))
