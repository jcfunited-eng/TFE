"""Exposure-growth audit for the byte-frozen local interval-neuron law."""

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
from tools.probe_auditory_thing_local_familiarity import (
    AUTHORITY_KEY,
    OBJECT_IDS,
    _custody,
    _execute,
    _world,
)
from tools.probe_auditory_thing_local_interval_mosaic import (
    CellBasin,
    CellKey,
    Episode,
    _basins,
    _episode,
    _recurrent,
    _settle,
)
from tools.probe_contextual_thing_mosaic_settling import _tone_pcm
from tools.probe_vtvr_causal_thing_familiarity import (
    ARCHIVE_PATH,
    ARCHIVE_SHA256,
    SpeechItem,
    _archive_sha256,
)


SCHEMA = "guala.audit.auditory_thing_interval_exposure_growth.v1"
FROZEN_LAW_PATH = Path(
    "tools/probe_auditory_thing_local_interval_mosaic.py"
)
FROZEN_LAW_SHA256 = (
    "1e4c1d118975e46cbf7fe9f1a7036e6e95112eb08289cb509ed726eda7e45362"
)
WORDS = ("no", "right", "up")
RUNGS = (5, 10, 20, 40, 80)
HELD_OUT_PER_THING = 20
TRAINING_PER_THING = RUNGS[-1]


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


def _fraction_text(value) -> str:
    return f"{value.numerator}/{value.denominator}"


def _select(
    archive: zipfile.ZipFile,
    *,
    word: str,
    count: int,
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
    for speaker in sorted(by_speaker):
        if speaker in used:
            continue
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
                pcm = source.readframes(source.getnframes())
            result.append(SpeechItem(
                oracle_word=word,
                speaker_id=speaker,
                archive_member=member,
                pcm_s16le=pcm,
                wav_sha256=hashlib.sha256(wav_data).hexdigest(),
            ))
            used.add(speaker)
            break
        if len(result) == count:
            return tuple(result)
    raise RuntimeError(f"insufficient growth corpus for {word}")


def _equal_mix(left: bytes, right: bytes) -> bytes:
    left_values = struct.iter_unpack("<h", left)
    right_values = struct.iter_unpack("<h", right)
    return b"".join(
        struct.pack("<h", (a[0] + b[0]) // 2)
        for a, b in zip(left_values, right_values, strict=True)
    )


def _cell_record(value: CellKey) -> list[object]:
    return value.record()


def _memory_bytes(
    memories: dict[
        str,
        tuple[
            dict[CellKey, CellBasin],
            frozenset[tuple[CellKey, CellKey]],
        ],
    ],
) -> int:
    payload = [
        {
            "cells": [
                {
                    "key": _cell_record(key),
                    "lower": [
                        _fraction_text(item) for item in basin.lower
                    ],
                    "upper": [
                        _fraction_text(item) for item in basin.upper
                    ],
                }
                for key, basin in sorted(cells.items())
            ],
            "edges": [
                [_cell_record(left), _cell_record(right)]
                for left, right in sorted(edges)
            ],
            "thing_id": thing_id,
        }
        for thing_id, (cells, edges) in sorted(memories.items())
    ]
    return len(_canonical(payload))


def _memories(
    *,
    count: int,
    training: dict[str, list[Episode]],
    thing_ids: dict[str, str],
):
    recurrent_cells = {
        thing_ids[word]: _recurrent(
            tuple(training[word][:count]),
            attribute="cells",
        )
        for word in WORDS
    }
    recurrent_edges = {
        thing_ids[word]: _recurrent(
            tuple(training[word][:count]),
            attribute="edges",
        )
        for word in WORDS
    }
    shared_cells = frozenset(
        cell
        for values in recurrent_cells.values()
        for cell in values
        if sum(cell in other for other in recurrent_cells.values()) > 1
    )
    shared_edges = frozenset(
        edge
        for values in recurrent_edges.values()
        for edge in values
        if sum(edge in other for other in recurrent_edges.values()) > 1
    )
    result = {}
    for word in WORDS:
        thing_id = thing_ids[word]
        cells = recurrent_cells[thing_id].difference(shared_cells)
        edges = frozenset(
            edge
            for edge in recurrent_edges[thing_id].difference(shared_edges)
            if edge[0] in cells and edge[1] in cells
        )
        result[thing_id] = (
            _basins(tuple(training[word][:count]), cells),
            edges,
        )
    return result, shared_cells, shared_edges


def run_probe() -> dict[str, object]:
    if _archive_sha256(ARCHIVE_PATH) != ARCHIVE_SHA256:
        raise RuntimeError("speech archive authority changed")
    law_sha = hashlib.sha256(FROZEN_LAW_PATH.read_bytes()).hexdigest()
    if law_sha != FROZEN_LAW_SHA256:
        raise RuntimeError("frozen interval-neuron law changed")
    used: set[str] = set()
    with zipfile.ZipFile(ARCHIVE_PATH) as archive:
        selected = {
            word: _select(
                archive,
                word=word,
                count=TRAINING_PER_THING + HELD_OUT_PER_THING,
                used=used,
            )
            for word in WORDS
        }
        unknown_item = _select(
            archive,
            word="down",
            count=1,
            used=used,
        )[0]

    world = _world()
    physical = _physical_authority(world)
    sensory = EmbodimentSensoryOutcomeAuthority(
        authority_key=EVIDENCE_KEY
    )
    partitions = CustodiedW1ContactThingEncounterAuthority(
        authority_key=AUTHORITY_KEY + b":interval-growth",
        world_authority=world,
        sensory_authority=sensory,
        max_roots_per_partition=256,
    )
    things = CausalThingMosaicOwner(
        authority_key=AUTHORITY_KEY + b":interval-growth",
        profile=CausalThingMosaicProfile.create(
            profile_id="auditory-interval-growth-things-v1",
            max_mosaics=3,
            max_partitions_per_mosaic=TRAINING_PER_THING + 1,
            max_roots_per_partition=256,
            max_routes=262_144,
            max_state_bytes=1024 * 1024 * 1024,
        ),
        partition_authority=partitions,
    )
    training: dict[str, list[Episode]] = {word: [] for word in WORDS}
    held_out: dict[str, list[Episode]] = {word: [] for word in WORDS}
    thing_ids = {}
    action_ordinal = 30_000
    custody_ordinal = 30_000
    completed_captures = 0
    for ordinal, (word, object_id) in enumerate(
        zip(WORDS, OBJECT_IDS, strict=True),
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
        for item in selected[word][:TRAINING_PER_THING]:
            execution, mount = _external_mount(
                world,
                physical,
                item.pcm_s16le,
            )
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
                raise ValueError("growth episode left THING custody")
            training[word].append(_episode(settlement))
            completed_captures += 1
            if completed_captures % 10 == 0:
                print(
                    f"physical training captures: {completed_captures}/240",
                    file=sys.stderr,
                    flush=True,
                )
        thing_ids[word] = mosaic.thing_id
        if ordinal < 3:
            action_ordinal += 1
            _execute(
                world,
                PlaceCommand(
                    object_id,
                    PositionMM(approach_x - 500, 1_000, 0),
                ),
                causal_ordinal=action_ordinal,
            )

    for word in WORDS:
        for item in selected[word][TRAINING_PER_THING:]:
            _execution, mount = _external_mount(
                world,
                physical,
                item.pcm_s16le,
            )
            held_out[word].append(
                _episode(mount.binaural_receptor_settlement)
            )
            completed_captures += 1
            if completed_captures % 10 == 0:
                print(
                    f"physical total captures: {completed_captures}/303",
                    file=sys.stderr,
                    flush=True,
                )
    _execution, mount = _external_mount(
        world,
        physical,
        unknown_item.pcm_s16le,
    )
    unknown = _episode(mount.binaural_receptor_settlement)
    _execution, mount = _external_mount(world, physical, _tone_pcm())
    noise = _episode(mount.binaural_receptor_settlement)
    overlap_pcm = _equal_mix(
        selected[WORDS[0]][TRAINING_PER_THING].pcm_s16le,
        selected[WORDS[1]][TRAINING_PER_THING].pcm_s16le,
    )
    _execution, mount = _external_mount(world, physical, overlap_pcm)
    overlap = _episode(mount.binaural_receptor_settlement)

    rung_reports = []
    for count in RUNGS:
        memories, shared_cells, shared_edges = _memories(
            count=count,
            training=training,
            thing_ids=thing_ids,
        )
        evaluations = []
        correct = 0
        for word in WORDS:
            for ordinal, query in enumerate(held_out[word]):
                state, locked, relations = _settle(query, memories)
                released = locked[0] if state == "resolved" else None
                passed = released == thing_ids[word]
                correct += int(passed)
                evaluations.append({
                    "expected_thing_id": thing_ids[word],
                    "held_out_ordinal": ordinal,
                    "locked_thing_ids": list(locked),
                    "oracle_word": word,
                    "passed": passed,
                    "relations": relations,
                    "state": state,
                })
        controls = {}
        for name, query, expected_state in (
            ("unknown_speech", unknown, "unknown"),
            ("physical_tone", noise, "unknown"),
            ("equal_gain_overlap", overlap, "ambiguous"),
        ):
            state, locked, relations = _settle(query, memories)
            controls[name] = {
                "expected_state": expected_state,
                "locked_thing_ids": list(locked),
                "passed": state == expected_state,
                "relations": relations,
                "state": state,
            }
        full_gate = (
            correct == len(WORDS) * HELD_OUT_PER_THING
            and all(value["passed"] for value in controls.values())
        )
        rung_reports.append({
            "control_results": controls,
            "correct": correct,
            "full_gate_passed": full_gate,
            "held_out_count": len(WORDS) * HELD_OUT_PER_THING,
            "held_out_evaluations": evaluations,
            "memory_encoded_bytes": _memory_bytes(memories),
            "memory_records": [
                {
                    "cell_count": len(cells),
                    "edge_count": len(edges),
                    "thing_id": thing_id,
                }
                for thing_id, (cells, edges) in sorted(memories.items())
            ],
            "shared_quiescent_cell_count": len(shared_cells),
            "shared_quiescent_edge_count": len(shared_edges),
            "training_speakers_per_thing": count,
        })
        if full_gate:
            break

    payload = {
        "archive_sha256": ARCHIVE_SHA256,
        "fixed_held_out_per_thing": HELD_OUT_PER_THING,
        "frozen_law_sha256": law_sha,
        "learning_boundary_received_words_or_speakers": False,
        "physical_settlement_computed_once_per_capture": True,
        "predeclared_rungs": list(RUNGS),
        "raw_pcm_retained_by_memory_bytes": 0,
        "rung_reports": rung_reports,
        "schema": SCHEMA,
        "source_disjoint_speaker_count": len(used),
        "training_capacity_per_thing": TRAINING_PER_THING,
        "user_authorized_learned_interval_physics": True,
    }
    return payload | {
        "authority_receipt_sha256": _digest(payload),
    }


if __name__ == "__main__":
    print(json.dumps(run_probe(), indent=2, sort_keys=True))
