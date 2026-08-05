"""Hash-locked physical walk-up for witnessed auditory temporal union v2."""

from __future__ import annotations

import hashlib
import io
import json
import struct
import sys
import wave
import zipfile
from pathlib import Path

from dsf_ai_service.substrate.causal_thing_mosaic import (
    CausalThingMosaicOwner,
    CausalThingMosaicProfile,
)
from dsf_ai_service.substrate.custodied_thing_encounter import (
    CustodiedW1ContactThingEncounterAuthority,
    THING_MOSAIC_CONSUMER_ID,
)
from dsf_ai_service.substrate.embodiment_world import (
    MoveCommand,
    PickCommand,
    PlaceCommand,
    PoseMM,
    PositionMM,
)
from dsf_ai_service.substrate.w1_physical_receptors import (
    EmbodimentSensoryOutcomeAuthority,
)
from tests.test_lived_vocal_teaching_episode import _external_mount
from tests.test_w1_audiovisual_physical_evidence import (
    EVIDENCE_KEY,
    _authority as _physical_authority,
)
from tools.isolated_auditory_monotonic_union_law_v2 import (
    MonotonicThingUnion,
    build_union,
    settle_union_query,
)
from tools.isolated_auditory_physical_episode import (
    Episode,
    episode_from_settlement,
)
from tools.probe_auditory_thing_local_familiarity import (
    AUTHORITY_KEY,
    OBJECT_IDS,
    _custody,
    _execute,
    _world,
)
from tools.probe_contextual_thing_mosaic_settling import _tone_pcm
from tools.probe_vtvr_causal_thing_familiarity import (
    ARCHIVE_PATH,
    ARCHIVE_SHA256,
    SpeechItem,
    _archive_sha256,
)


SCHEMA = "guala.audit.auditory_monotonic_union_walkup.v2"
PLAN_PATH = Path(
    "tests/fixtures/auditory_monotonic_union_walkup_plan_v2.json"
)
PLAN_SHA256 = (
    "879aa64384118e5d332b3808e289ee2471344bf0ff6373ab7cc0e29b5c9e6320"
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


def _load_frozen_plan() -> dict[str, object]:
    raw = PLAN_PATH.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PLAN_SHA256:
        raise RuntimeError("monotonic union walk-up plan changed after freeze")
    plan = json.loads(raw)
    if plan["physical_capture_count"] != 183:
        raise RuntimeError("frozen plan does not require 183 captures")
    if plan["physical_control_captures"] != {
        "unknown_stop_speech": 1,
        "generated_tone": 1,
        "equal_gain_overlap": 1,
    }:
        raise RuntimeError("frozen control capture plan changed")
    for path_key, digest_key in (
        ("physical_episode_adapter_path", "physical_episode_adapter_sha256"),
        ("law_path", "law_sha256"),
    ):
        source = Path(str(plan[path_key]))
        source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
        if source_sha != plan[digest_key]:
            raise RuntimeError(f"{source} changed after plan freeze")
    return plan


def _select(
    archive: zipfile.ZipFile,
    *,
    word: str,
    count: int,
    skipped_speakers: int,
    used: set[str],
) -> tuple[SpeechItem, ...]:
    prefix = f"mini_speech_commands/{word}/"
    by_speaker: dict[str, list[str]] = {}
    for member in sorted(archive.namelist()):
        if not member.startswith(prefix) or not member.endswith(".wav"):
            continue
        filename = member.rsplit("/", 1)[-1]
        if "_nohash_" in filename:
            by_speaker.setdefault(
                filename.split("_nohash_", 1)[0],
                [],
            ).append(member)
    result = []
    eligible_ordinal = 0
    for speaker in sorted(by_speaker):
        valid = None
        for member in by_speaker[speaker]:
            wav_data = archive.read(member)
            with wave.open(io.BytesIO(wav_data), "rb") as source:
                if (
                    source.getnchannels() != 1
                    or source.getsampwidth() != 2
                    or source.getframerate() != 16_000
                    or source.getnframes() != 16_000
                    or source.getcomptype() != "NONE"
                ):
                    continue
                valid = (
                    member,
                    wav_data,
                    source.readframes(source.getnframes()),
                )
                break
        if valid is None:
            continue
        if eligible_ordinal < skipped_speakers:
            eligible_ordinal += 1
            continue
        eligible_ordinal += 1
        if speaker in used:
            continue
        member, wav_data, pcm = valid
        result.append(
            SpeechItem(
                oracle_word=word,
                speaker_id=speaker,
                archive_member=member,
                pcm_s16le=pcm,
                wav_sha256=hashlib.sha256(wav_data).hexdigest(),
            )
        )
        used.add(speaker)
        if len(result) == count:
            return tuple(result)
    raise RuntimeError(f"fresh monotonic union corpus lacks {word}")


def _equal_mix(left: bytes, right: bytes) -> bytes:
    return b"".join(
        struct.pack("<h", (a[0] + b[0]) // 2)
        for a, b in zip(
            struct.iter_unpack("<h", left),
            struct.iter_unpack("<h", right),
            strict=True,
        )
    )


def _monotonic(
    prior: MonotonicThingUnion,
    current: MonotonicThingUnion,
) -> bool:
    prior_cells = prior.cell_map()
    current_cells = current.cell_map()
    return (
        set(prior_cells).issubset(current_cells)
        and prior.temporal_edges.issubset(current.temporal_edges)
        and all(
            all(
                current_cells[key].lower[index]
                <= basin.lower[index]
                <= basin.upper[index]
                <= current_cells[key].upper[index]
                for index in range(len(basin.lower))
            )
            for key, basin in prior_cells.items()
        )
        and set(prior.field_witness_receipt_sha256s).issubset(
            current.field_witness_receipt_sha256s
        )
        and set(prior.temporal_witness_receipt_sha256s).issubset(
            current.temporal_witness_receipt_sha256s
        )
    )


def _physical_topology_holds(episode: Episode) -> bool:
    witnessed = {
        (left.key, right.key)
        for left in episode.drives
        for right in episode.drives
        if (
            left.key.ear_id == right.key.ear_id
            and left.key.cochlear_index == right.key.cochlear_index
            and left.key.component_kind == right.key.component_kind
            and left.source_index_end == right.source_index_start
            and left.source_time_end == right.source_time_start
            and left.end_occurrence_receipt_sha256
            == right.start_occurrence_receipt_sha256
        )
    }
    return all(
        (edge.left, edge.right) in witnessed
        for edge in episode.temporal_edges
    )


def run_probe() -> dict[str, object]:
    plan = _load_frozen_plan()
    if _archive_sha256(ARCHIVE_PATH) != ARCHIVE_SHA256:
        raise RuntimeError("speech archive authority changed")
    words = tuple(str(value) for value in plan["words"])
    skip_speakers = int(plan["skip_valid_speakers_per_word"])
    training_per_thing = int(plan["training_speakers_per_thing"])
    held_out_per_thing = int(plan["held_out_speakers_per_thing"])
    planned_captures = int(plan["physical_capture_count"])
    if words != ("down", "go", "left"):
        raise RuntimeError("frozen word plan changed")
    object_ids = OBJECT_IDS[: len(words)]
    if len(object_ids) != len(words):
        raise RuntimeError("physical world lacks planned THING objects")

    used: set[str] = set()
    with zipfile.ZipFile(ARCHIVE_PATH) as archive:
        corpus = {
            word: _select(
                archive,
                word=word,
                count=training_per_thing + held_out_per_thing,
                skipped_speakers=skip_speakers,
                used=used,
            )
            for word in words
        }
        unknown_item = _select(
            archive,
            word="stop",
            count=1,
            skipped_speakers=skip_speakers,
            used=used,
        )[0]

    world = _world()
    physical = _physical_authority(world)
    sensory = EmbodimentSensoryOutcomeAuthority(
        authority_key=EVIDENCE_KEY
    )
    partitions = CustodiedW1ContactThingEncounterAuthority(
        authority_key=AUTHORITY_KEY + b":monotonic-union-v2",
        world_authority=world,
        sensory_authority=sensory,
        max_roots_per_partition=256,
    )
    things = CausalThingMosaicOwner(
        authority_key=AUTHORITY_KEY + b":monotonic-union-v2",
        profile=CausalThingMosaicProfile.create(
            profile_id="auditory-monotonic-union-things-v2",
            max_mosaics=len(words),
            max_partitions_per_mosaic=training_per_thing + 1,
            max_roots_per_partition=256,
            max_routes=131_072,
            max_state_bytes=1024 * 1024 * 1024,
        ),
        partition_authority=partitions,
    )
    training: dict[str, list[Episode]] = {word: [] for word in words}
    held_out: dict[str, list[Episode]] = {word: [] for word in words}
    thing_ids = {}
    action_ordinal = 40_000
    custody_ordinal = 40_000
    completed = 0

    for ordinal, (word, object_id) in enumerate(
        zip(words, object_ids, strict=True),
        start=1,
    ):
        approach_x = ordinal * 1_000
        if ordinal > 1:
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
        custody_ordinal += 1
        custody = _custody(
            source_mount=physical.mount_action_outcome(picked),
            execution=picked,
            ordinal=custody_ordinal,
        )
        prior = partitions.partition_from_custody(
            custody_authority=custody,
            capability=custody.issue_child(THING_MOSAIC_CONSUMER_ID),
        )
        mosaic = things.admit(prior)
        for item in corpus[word][:training_per_thing]:
            execution, mount = _external_mount(
                world,
                physical,
                item.pcm_s16le,
            )
            completed += 1
            custody_ordinal += 1
            custody = _custody(
                source_mount=mount,
                execution=execution,
                ordinal=custody_ordinal,
            )
            prior = partitions.partition_from_custody(
                custody_authority=custody,
                capability=custody.issue_child(
                    THING_MOSAIC_CONSUMER_ID
                ),
                prior=prior,
            )
            mosaic = things.admit(prior)
            settlement = mount.binaural_receptor_settlement
            if (
                settlement.upstream_causal_settlement_receipt_sha256
                != prior.settlement_receipt_sha256
            ):
                raise ValueError("monotonic union left THING custody")
            training[word].append(episode_from_settlement(settlement))
            if completed % 10 == 0:
                print(
                    f"physical training captures: {completed}/120",
                    file=sys.stderr,
                    flush=True,
                )
        thing_ids[word] = mosaic.thing_id
        if ordinal < len(words):
            action_ordinal += 1
            _execute(
                world,
                PlaceCommand(
                    object_id,
                    PositionMM(approach_x - 500, 1_000, 0),
                ),
                causal_ordinal=action_ordinal,
            )

    for word in words:
        for item in corpus[word][training_per_thing:]:
            _execution, mount = _external_mount(
                world,
                physical,
                item.pcm_s16le,
            )
            completed += 1
            held_out[word].append(
                episode_from_settlement(
                    mount.binaural_receptor_settlement
                )
            )
            if completed % 10 == 0:
                print(
                    f"physical total captures: {completed}/{planned_captures}",
                    file=sys.stderr,
                    flush=True,
                )

    _execution, mount = _external_mount(
        world,
        physical,
        unknown_item.pcm_s16le,
    )
    completed += 1
    unknown = episode_from_settlement(
        mount.binaural_receptor_settlement
    )

    tone_pcm = _tone_pcm()
    _execution, mount = _external_mount(world, physical, tone_pcm)
    completed += 1
    tone = episode_from_settlement(mount.binaural_receptor_settlement)

    overlap_pcm = _equal_mix(
        corpus[words[0]][training_per_thing].pcm_s16le,
        corpus[words[1]][training_per_thing].pcm_s16le,
    )
    _execution, mount = _external_mount(world, physical, overlap_pcm)
    completed += 1
    overlap = episode_from_settlement(
        mount.binaural_receptor_settlement
    )

    if completed != planned_captures:
        raise RuntimeError(
            f"physical capture count {completed} != plan {planned_captures}"
        )
    all_episodes = tuple(
        episode
        for word in words
        for episode in (*training[word], *held_out[word])
    ) + (unknown, tone, overlap)
    if not all(_physical_topology_holds(value) for value in all_episodes):
        raise RuntimeError("physical temporal topology audit failed")
    print(
        f"physical capture and topology gates: {completed}/{planned_captures}",
        file=sys.stderr,
        flush=True,
    )

    memories = tuple(
        build_union(
            thing_id=thing_ids[word],
            episodes=tuple(training[word]),
        )
        for word in words
    )
    monotonic_checks = []
    for word in words:
        earlier = build_union(
            thing_id=thing_ids[word],
            episodes=tuple(training[word][:20]),
        )
        current = next(
            value for value in memories
            if value.thing_id == thing_ids[word]
        )
        monotonic_checks.append(
            {
                "passed": _monotonic(earlier, current),
                "thing_id": thing_ids[word],
            }
        )

    evaluations = []
    correct = 0
    for word in words:
        for ordinal, query in enumerate(held_out[word]):
            result = settle_union_query(
                query=query,
                memories=memories,
            )
            released = (
                result["locked_thing_ids"][0]
                if result["state"] == "resolved"
                else None
            )
            passed = released == thing_ids[word]
            correct += int(passed)
            evaluations.append(
                {
                    "expected_thing_id": thing_ids[word],
                    "held_out_ordinal": ordinal,
                    "locked_thing_ids": result["locked_thing_ids"],
                    "oracle_word": word,
                    "passed": passed,
                    "relations": result["relations"],
                    "state": result["state"],
                }
            )
    controls = {}
    for name, query, expected_state in (
        ("unknown_speech", unknown, "unknown"),
        ("physical_tone", tone, "unknown"),
        ("equal_gain_overlap", overlap, "ambiguous"),
    ):
        result = settle_union_query(query=query, memories=memories)
        controls[name] = {
            "expected_state": expected_state,
            "locked_thing_ids": result["locked_thing_ids"],
            "passed": result["state"] == expected_state,
            "relations": result["relations"],
            "state": result["state"],
        }
    full_gate = (
        correct == len(words) * held_out_per_thing
        and all(value["passed"] for value in controls.values())
        and all(value["passed"] for value in monotonic_checks)
    )
    payload = {
        "archive_sha256": ARCHIVE_SHA256,
        "claim_allowed": full_gate,
        "control_results": controls,
        "correct": correct,
        "fixed_held_out_per_thing": held_out_per_thing,
        "frozen_law_sha256": plan["law_sha256"],
        "frozen_physical_episode_adapter_sha256": (
            plan["physical_episode_adapter_sha256"]
        ),
        "frozen_plan_sha256": PLAN_SHA256,
        "full_gate_passed": full_gate,
        "held_out_count": len(words) * held_out_per_thing,
        "held_out_evaluations": evaluations,
        "learning_boundary_received_words_or_speakers": False,
        "memory_encoded_bytes": sum(
            len(value.encoded()) for value in memories
        ),
        "memory_records": [
            {
                "cell_count": len(memory.cells),
                "encoded_bytes": len(memory.encoded()),
                "episode_count": len(memory.episode_receipt_sha256s),
                "field_witness_count": len(
                    memory.field_witness_receipt_sha256s
                ),
                "temporal_edge_count": len(memory.temporal_edges),
                "temporal_witness_count": len(
                    memory.temporal_witness_receipt_sha256s
                ),
                "thing_id": memory.thing_id,
            }
            for memory in memories
        ],
        "monotonic_growth_checks": monotonic_checks,
        "physical_capture_count": completed,
        "physical_topology_gate_passed": True,
        "raw_pcm_retained_by_memory_bytes": 0,
        "schema": SCHEMA,
        "source_disjoint_speaker_count": len(used),
        "training_speakers_per_thing": training_per_thing,
        "user_authorized_learned_interval_physics": True,
    }
    return payload | {
        "authority_receipt_sha256": _digest(payload),
    }


if __name__ == "__main__":
    print(json.dumps(run_probe(), indent=2, sort_keys=True))
