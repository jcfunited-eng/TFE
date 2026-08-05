"""Real source-disjoint reciprocal THING variant-learning probe.

Three different physical objects are encountered in one W1 world.  Two
source-disjoint recorded speakers are experienced while each object is held,
then a third held-out speaker is challenged before and after one authenticated
causal encounter with that same object.

The reciprocal class uses no sound comparison.  Before causal admission an
unexperienced auditory root must remain unresolved.  After admission the same
root must evoke the complete multisensory THING mosaic, including alternative
experienced sound roots and non-auditory roots.  Different held entities must
remain different classes.  An unrelated tone is never admitted and must
remain unresolved.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

from dsf_ai_service.substrate.causal_thing_mosaic import (
    CausalThingMosaicOwner,
    CausalThingMosaicProfile,
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
from dsf_ai_service.substrate.settled_experience_custody import (
    SettledExperienceCustodyAuthority,
    SettledExperienceCustodyProfile,
)
from dsf_ai_service.substrate.w1_physical_receptors import (
    EmbodimentSensoryOutcomeAuthority,
)
from tools.probe_auditory_full_field_separability_census import (
    ARCHIVE_SHA256,
    _select_corpus,
)
from tools.probe_contextual_thing_mosaic_settling import (
    TEST_COMMANDS,
    _tone_pcm,
)
from tools.probe_existing_auditory_neuron_temporal_go_no_go import (
    _read_pcm,
)
from tests.test_lived_vocal_teaching_episode import _external_mount
from tests.test_w1_audiovisual_physical_evidence import (
    EVIDENCE_KEY,
    WORLD_KEY,
    _authority as _physical_authority,
    _world,
)


SCHEMA = "guala.audit.causal_thing_reciprocal_variant_learning.v1"
KEY = b"guala-causal-thing-reciprocal-variant-probe-20260727"
OBJECT_BY_COMMAND = {
    "down": "teaching-object",
    "go": "thing-go",
    "left": "thing-left",
}
PLACE_BY_COMMAND = {
    "down": PositionMM(1_000, 1_800, 0),
    "go": PositionMM(4_800, 1_000, 0),
}
MOVE_AFTER_COMMAND = {
    "down": PoseMM(PositionMM(4_000, 1_000, 0), 0),
    "go": PoseMM(PositionMM(4_500, 3_500, 0), 0),
}


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


def _execute(world, command, ordinal: int):
    before = world.observation_snapshot()
    result = world.execute_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(command),
        causal_intent_receipt_sha256=_digest({
            "ordinal": ordinal,
            "schema": "guala.audit.reciprocal_variant_action.v1",
        }),
        expected_revision=before.revision,
    )
    if result.disposition != "applied":
        raise RuntimeError(
            f"reciprocal variant action failed: {result.reason}"
        )
    return result


def _custody(mount, execution, ordinal: int):
    authority = SettledExperienceCustodyAuthority(
        authority_key=KEY + str(ordinal).encode("ascii"),
        w1_physical_authority_key=EVIDENCE_KEY,
        world_authority_key=WORLD_KEY,
        profile=SettledExperienceCustodyProfile.create(
            profile_id=f"reciprocal-variant-custody-{ordinal}",
            max_children=2,
            max_snapshot_bytes=128 * 1024 * 1024,
        ),
    )
    value = authority.admit(mount, execution)
    child = authority.issue_child(THING_MOSAIC_CONSUMER_ID)
    return authority, value, child


def run(archive_path: Path) -> dict[str, object]:
    archive_bytes = archive_path.read_bytes()
    archive_sha256 = hashlib.sha256(archive_bytes).hexdigest()
    if archive_sha256 != ARCHIVE_SHA256:
        raise ValueError("speech corpus authority changed")
    with zipfile.ZipFile(archive_path) as archive:
        corpus = _select_corpus(archive)
        references = {
            command: tuple(
                item
                for item in corpus
                if item.oracle_command == command
                and item.split == "reference"
            )[:2]
            for command in TEST_COMMANDS
        }
        held_out = {
            command: next(
                item
                for item in corpus
                if item.oracle_command == command
                and item.split == "held_out"
            )
            for command in TEST_COMMANDS
        }
        selected = tuple(
            item
            for command in TEST_COMMANDS
            for item in references[command] + (held_out[command],)
        )
        pcm_by_id = {
            item.item_id: _read_pcm(archive.read(item.archive_member))
            for item in selected
        }
    if (
        any(len(references[command]) != 2 for command in TEST_COMMANDS)
        or len({
            item.speaker_id
            for item in selected
        }) != len(selected)
    ):
        raise RuntimeError("reciprocal variant speakers are not disjoint")

    world = _world(additional_objects=(
        EmbodiedObject(
            "thing-go",
            radius_mm=90,
            mass_grams=300,
            position=PositionMM(4_500, 1_000, 0),
            reflectance_ppm=(
                100_000, 700_000, 100_000,
                100_000, 100_000, 100_000,
            ),
        ),
        EmbodiedObject(
            "thing-left",
            radius_mm=110,
            mass_grams=700,
            position=PositionMM(4_500, 4_000, 0),
            reflectance_ppm=(
                100_000, 100_000, 700_000,
                100_000, 100_000, 100_000,
            ),
        ),
    ))
    physical = _physical_authority(world)
    sensory = EmbodimentSensoryOutcomeAuthority(
        authority_key=EVIDENCE_KEY
    )
    partitions = CustodiedW1ContactThingEncounterAuthority(
        authority_key=KEY,
        world_authority=world,
        sensory_authority=sensory,
        max_roots_per_partition=256,
    )
    things = CausalThingMosaicOwner(
        authority_key=KEY,
        profile=CausalThingMosaicProfile.create(
            profile_id="reciprocal-variant-things",
            max_mosaics=3,
            max_partitions_per_mosaic=4,
            max_roots_per_partition=256,
            max_routes=16_384,
            max_state_bytes=512 * 1024 * 1024,
        ),
        partition_authority=partitions,
    )
    reciprocal = CausalThingReciprocalMosaicOwner(
        authority_key=KEY,
        thing_owner=things,
        max_classes=3,
        max_roots_per_class=2_048,
        max_cue_roots=128,
    )

    ordinal = 0
    thing_ids = {}
    records = []
    heldout_records = []
    for command in TEST_COMMANDS:
        ordinal += 1
        picked = _execute(
            world,
            PickCommand(OBJECT_BY_COMMAND[command]),
            ordinal,
        )
        pick_mount = physical.mount_action_outcome(picked)
        pick_custody, _pick_value, pick_child = _custody(
            pick_mount, picked, ordinal
        )
        prior = partitions.partition_from_custody(
            custody_authority=pick_custody,
            capability=pick_child,
        )
        mosaic = things.admit(prior)
        thing_ids[command] = mosaic.thing_id
        records.append({
            "command_used_only_to_select_physical_test_object": command,
            "encounter_kind": "contact-genesis",
            "partition_receipt_sha256": prior.authority_receipt_sha256,
            "thing_id": mosaic.thing_id,
        })

        for item in references[command]:
            ordinal += 1
            execution, mount = _external_mount(
                world,
                physical,
                pcm_by_id[item.item_id],
            )
            custody, _value, child = _custody(
                mount, execution, ordinal
            )
            partition = partitions.partition_from_custody(
                custody_authority=custody,
                capability=child,
                prior=prior,
            )
            mosaic = things.admit(partition)
            if mosaic.thing_id != thing_ids[command]:
                raise RuntimeError("same held THING split across speakers")
            prior = partition
            records.append({
                "encounter_kind": "grounded-reference-speaker",
                "item_id": item.item_id,
                "partition_receipt_sha256": (
                    partition.authority_receipt_sha256
                ),
                "speaker_id": item.speaker_id,
                "thing_id": mosaic.thing_id,
            })

        item = held_out[command]
        ordinal += 1
        execution, mount = _external_mount(
            world,
            physical,
            pcm_by_id[item.item_id],
        )
        before = reciprocal.evoke(
            mount.causal_settlement,
            cue_senses=("sound",),
        )
        custody, _value, child = _custody(mount, execution, ordinal)
        partition = partitions.partition_from_custody(
            custody_authority=custody,
            capability=child,
            prior=prior,
        )
        mosaic = things.admit(partition)
        after = reciprocal.evoke(
            mount.causal_settlement,
            cue_senses=("sound",),
        )
        heldout_records.append({
            "after_grounded_exposure_state": after.state,
            "after_grounded_exposure_thing_ids": list(after.thing_ids),
            "before_grounded_exposure_state": before.state,
            "before_grounded_exposure_thing_ids": list(before.thing_ids),
            "evoked_senses_after_exposure": sorted({
                root.sense for root in after.evoked_full_field_roots
            }),
            "expected_thing_id": thing_ids[command],
            "item_id": item.item_id,
            "passed": (
                before.state == "unresolved"
                and after.state == "unique"
                and after.thing_ids == (thing_ids[command],)
                and {
                    "body", "sight", "sound", "touch"
                }.issubset({
                    root.sense
                    for root in after.evoked_full_field_roots
                })
            ),
            "speaker_id": item.speaker_id,
        })

        if command in PLACE_BY_COMMAND:
            ordinal += 1
            _execute(
                world,
                PlaceCommand(
                    OBJECT_BY_COMMAND[command],
                    PLACE_BY_COMMAND[command],
                ),
                ordinal,
            )
            ordinal += 1
            _execute(
                world,
                MoveCommand(MOVE_AFTER_COMMAND[command]),
                ordinal,
            )

    ordinal += 1
    _tone_execution, tone_mount = _external_mount(
        world,
        physical,
        _tone_pcm(),
    )
    tone = reciprocal.evoke(
        tone_mount.causal_settlement,
        cue_senses=("sound",),
    )
    classes = reciprocal.classes()
    thing_ids_distinct = len(set(thing_ids.values())) == len(TEST_COMMANDS)
    class_records = [
        {
            "partition_count": len(value.partition_receipt_sha256s),
            "roots_by_sense": {
                sense: len(roots)
                for sense, roots in value.roots_by_sense
            },
            "thing_id": value.thing_id,
            "variant_class_receipt_sha256": (
                value.authority_receipt_sha256
            ),
        }
        for value in classes
    ]
    payload = {
        "archive_sha256": archive_sha256,
        "canonical_code_modified": False,
        "class_records": class_records,
        "different_physical_things_remained_separate": (
            thing_ids_distinct and len(classes) == len(TEST_COMMANDS)
        ),
        "encounter_records": records,
        "heldout": heldout_records,
        "heldout_pass_count": sum(
            value["passed"] for value in heldout_records
        ),
        "learning_law": (
            "sensory variants become equivalent only by authenticated "
            "membership in one physically continuous THING mosaic; an "
            "unexperienced variant is never guessed"
        ),
        "live_wiring_performed": False,
        "overall_pass": (
            thing_ids_distinct
            and len(classes) == len(TEST_COMMANDS)
            and all(value["passed"] for value in heldout_records)
            and tone.state == "unresolved"
        ),
        "reciprocal_status": reciprocal.status(),
        "schema": SCHEMA,
        "source_disjoint_recorded_speaker_count": len(selected),
        "tone": {
            "state": tone.state,
            "thing_ids": list(tone.thing_ids),
        },
        "unseen_variant_recognition_claimed": False,
    }
    return payload | {"authority_receipt_sha256": _digest(payload)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run(args.archive)
    encoded = json.dumps(
        report,
        allow_nan=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
    if args.output is not None:
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")


if __name__ == "__main__":
    main()
