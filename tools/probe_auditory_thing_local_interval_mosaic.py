"""Frozen user-authorized learned-interval auditory sensory-neuron walk-up."""

from __future__ import annotations

import hashlib
import io
import json
import wave
import zipfile
from collections import Counter
from dataclasses import dataclass
from fractions import Fraction

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.canonical_l6 import canonical_l6_direction
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
from dsf_ai_service.substrate.w1_binaural_receptor_settlement import (
    W1BinauralReceptorSettlement,
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
from tools.probe_vtvr_causal_thing_familiarity import (
    ARCHIVE_PATH,
    ARCHIVE_SHA256,
    SpeechItem,
    _archive_sha256,
)


SCHEMA = "guala.audit.auditory_thing_local_interval_mosaic.v1"
WORDS = ("no", "right", "up")
TRAINING_SPEAKERS_PER_THING = 5
HELD_OUT_SPEAKERS_PER_THING = 2


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


def _fraction_text(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def _direction(value: Fraction) -> int:
    return (value > 0) - (value < 0)


@dataclass(frozen=True, order=True, slots=True)
class CellKey:
    ear_id: str
    cochlear_index: int
    component_kind: str
    field_directions: tuple[int, ...]

    def record(self) -> list[object]:
        return [
            self.ear_id,
            self.cochlear_index,
            self.component_kind,
            list(self.field_directions),
        ]


@dataclass(frozen=True, slots=True)
class LocalDrive:
    key: CellKey
    source_index: int
    values: tuple[Fraction, ...]


@dataclass(frozen=True, slots=True)
class Episode:
    settlement_receipt_sha256: str
    drives: tuple[LocalDrive, ...]
    cells: frozenset[CellKey]
    edges: frozenset[tuple[CellKey, CellKey]]
    witness_receipt_sha256s: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CellBasin:
    key: CellKey
    lower: tuple[Fraction, ...]
    upper: tuple[Fraction, ...]

    def contains(self, drive: LocalDrive) -> bool:
        return (
            drive.key == self.key
            and all(
                low <= value <= high
                for low, value, high in zip(
                    self.lower,
                    drive.values,
                    self.upper,
                    strict=True,
                )
            )
        )


def _episode(
    settlement: W1BinauralReceptorSettlement,
) -> Episode:
    settlement.verify()
    drives = []
    witnesses = []
    for ear in settlement.ears:
        for channel in range(16):
            occurrences = tuple(sorted(
                (
                    value
                    for value in ear.experience.occurrences
                    if value.receptor.cochlear_index == channel
                ),
                key=lambda value: (
                    value.source_index,
                    value.receptor.winding_direction,
                ),
            ))
            for prior, current in zip(occurrences, occurrences[1:]):
                duration = current.source_time - prior.source_time
                if duration <= 0:
                    continue
                for kind in ("pressure", "phase"):
                    left = tuple(
                        value
                        for _name, value in (
                            prior.pressure_fields
                            if kind == "pressure"
                            else prior.phase_fields
                        )
                    )
                    right = tuple(
                        value
                        for _name, value in (
                            current.pressure_fields
                            if kind == "pressure"
                            else current.phase_fields
                        )
                    )
                    delta = tuple(
                        after - before
                        for before, after in zip(left, right, strict=True)
                    )
                    key = CellKey(
                        ear_id=ear.ear_id,
                        cochlear_index=channel,
                        component_kind=kind,
                        field_directions=tuple(
                            _direction(value) for value in delta
                        ),
                    )
                    drives.append(LocalDrive(
                        key=key,
                        source_index=current.source_index,
                        values=(*left, *right, duration),
                    ))
                witnesses.extend((
                    current.pressure_field_receipt_sha256,
                    current.phase_field_receipt_sha256,
                ))
    ordered = tuple(sorted(
        drives,
        key=lambda value: (value.source_index, value.key),
    ))
    collapsed = []
    for drive in ordered:
        if not collapsed or collapsed[-1].key != drive.key:
            collapsed.append(drive)
    edges = frozenset(
        (left.key, right.key)
        for left, right in zip(collapsed, collapsed[1:])
        if left.key != right.key
    )
    return Episode(
        settlement_receipt_sha256=(
            settlement.authority_receipt_sha256
        ),
        drives=ordered,
        cells=frozenset(value.key for value in ordered),
        edges=edges,
        witness_receipt_sha256s=tuple(sorted(set(witnesses))),
    )


def _fresh_items(
    archive: zipfile.ZipFile,
    *,
    used_speakers: set[str],
    word: str,
) -> tuple[SpeechItem, ...]:
    prefix = f"mini_speech_commands/{word}/"
    by_speaker: dict[str, list[str]] = {}
    for member in archive.namelist():
        if not member.startswith(prefix) or not member.endswith(".wav"):
            continue
        filename = member.rsplit("/", 1)[-1]
        if "_nohash_" in filename:
            by_speaker.setdefault(
                filename.split("_nohash_", 1)[0],
                [],
            ).append(member)
    result = []
    for speaker in sorted(by_speaker, reverse=True):
        if speaker in used_speakers:
            continue
        for member in sorted(by_speaker[speaker], reverse=True):
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
            used_speakers.add(speaker)
            break
        if len(result) == (
            TRAINING_SPEAKERS_PER_THING
            + HELD_OUT_SPEAKERS_PER_THING
        ):
            return tuple(result)
    raise RuntimeError("fresh interval corpus is insufficient")


def _recurrent(
    episodes: tuple[Episode, ...],
    *,
    attribute: str,
):
    counts = Counter(
        value
        for episode in episodes
        for value in getattr(episode, attribute)
    )
    return frozenset(
        value
        for value, matching in counts.items()
        if canonical_l6_direction(
            dimensions=len(episodes),
            matching_non_null=matching,
            matching_quiescent=0,
        ).locked
    )


def _basins(
    episodes: tuple[Episode, ...],
    recurrent_cells: frozenset[CellKey],
) -> dict[CellKey, CellBasin]:
    result = {}
    for key in recurrent_cells:
        values = tuple(
            drive.values
            for episode in episodes
            for drive in episode.drives
            if drive.key == key
        )
        if not values:
            raise ValueError("recurrent cell lacks physical drives")
        result[key] = CellBasin(
            key=key,
            lower=tuple(min(column) for column in zip(*values)),
            upper=tuple(max(column) for column in zip(*values)),
        )
    return result


def _settle(
    query: Episode,
    memories: dict[
        str,
        tuple[
            dict[CellKey, CellBasin],
            frozenset[tuple[CellKey, CellKey]],
        ],
    ],
):
    records = []
    locked = []
    query_by_key: dict[CellKey, list[LocalDrive]] = {}
    for drive in query.drives:
        query_by_key.setdefault(drive.key, []).append(drive)
    for thing_id in sorted(memories):
        cells, edges = memories[thing_id]
        fired_cells = frozenset(
            key
            for key, basin in cells.items()
            if any(
                basin.contains(value)
                for value in query_by_key.get(key, ())
            )
        )
        fired_edges = frozenset(
            edge
            for edge in edges
            if edge in query.edges
            and edge[0] in fired_cells
            and edge[1] in fired_cells
        )
        dimensions = len(cells) + len(edges)
        matching = len(fired_cells) + len(fired_edges)
        direction = canonical_l6_direction(
            dimensions=dimensions,
            matching_non_null=matching,
            matching_quiescent=0,
        )
        records.append({
            "dimensions": dimensions,
            "effective_dimensions": direction.effective_dimensions,
            "fired_cell_count": len(fired_cells),
            "fired_edge_count": len(fired_edges),
            "knee": direction.knee,
            "locked": bool(dimensions and direction.locked),
            "matching_non_null": matching,
            "thing_id": thing_id,
        })
        if dimensions and direction.locked:
            locked.append(thing_id)
    state = (
        "resolved"
        if len(locked) == 1
        else "ambiguous"
        if locked
        else "unknown"
    )
    return state, tuple(locked), records


def run_probe() -> dict[str, object]:
    if _archive_sha256(ARCHIVE_PATH) != ARCHIVE_SHA256:
        raise RuntimeError("speech archive authority changed")
    used_speakers: set[str] = set()
    with zipfile.ZipFile(ARCHIVE_PATH) as archive:
        corpus = {
            word: _fresh_items(
                archive,
                used_speakers=used_speakers,
                word=word,
            )
            for word in WORDS
        }

    world = _world()
    physical = _physical_authority(world)
    sensory = EmbodimentSensoryOutcomeAuthority(
        authority_key=EVIDENCE_KEY
    )
    partitions = CustodiedW1ContactThingEncounterAuthority(
        authority_key=AUTHORITY_KEY + b":local-interval",
        world_authority=world,
        sensory_authority=sensory,
        max_roots_per_partition=256,
    )
    things = CausalThingMosaicOwner(
        authority_key=AUTHORITY_KEY + b":local-interval",
        profile=CausalThingMosaicProfile.create(
            profile_id="auditory-local-interval-things-v1",
            max_mosaics=3,
            max_partitions_per_mosaic=6,
            max_roots_per_partition=256,
            max_routes=65_536,
            max_state_bytes=512 * 1024 * 1024,
        ),
        partition_authority=partitions,
    )
    training: dict[str, list[Episode]] = {word: [] for word in WORDS}
    mosaics = {}
    action_ordinal = 20_000
    custody_ordinal = 20_000
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
        for item in corpus[word][:TRAINING_SPEAKERS_PER_THING]:
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
                raise ValueError("local interval left THING custody")
            training[word].append(_episode(settlement))
        mosaics[word] = mosaic
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

    recurrent_cells = {
        mosaics[word].thing_id: _recurrent(
            tuple(training[word]),
            attribute="cells",
        )
        for word in WORDS
    }
    recurrent_edges = {
        mosaics[word].thing_id: _recurrent(
            tuple(training[word]),
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
    memories = {}
    for word in WORDS:
        thing_id = mosaics[word].thing_id
        cells = recurrent_cells[thing_id].difference(shared_cells)
        edges = frozenset(
            edge
            for edge in recurrent_edges[thing_id].difference(shared_edges)
            if edge[0] in cells and edge[1] in cells
        )
        memories[thing_id] = (
            _basins(tuple(training[word]), cells),
            edges,
        )

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
            query = _episode(mount.binaural_receptor_settlement)
            state, locked, relations = _settle(query, memories)
            released = locked[0] if state == "resolved" else None
            passed = released == expected
            correct += int(passed)
            held_out.append({
                "archive_member": item.archive_member,
                "expected_thing_id": expected,
                "locked_thing_ids": list(locked),
                "oracle_speaker": item.speaker_id,
                "oracle_word": word,
                "passed": passed,
                "relations": relations,
                "released_thing_id": released,
                "state": state,
            })

    report = {
        "archive_sha256": ARCHIVE_SHA256,
        "authority_receipt_sha256": "",
        "claim_allowed": correct == len(held_out),
        "correct": correct,
        "field_order": list(DSF_FIELD_ORDER),
        "held_out": held_out,
        "held_out_count": len(held_out),
        "learning_boundary_received_words_or_speakers": False,
        "memory_records": [
            {
                "cell_count": len(cells),
                "edge_count": len(edges),
                "thing_id": thing_id,
            }
            for thing_id, (cells, edges) in sorted(memories.items())
        ],
        "raw_pcm_retained_bytes": 0,
        "schema": SCHEMA,
        "shared_quiescent_cell_count": len(shared_cells),
        "shared_quiescent_edge_count": len(shared_edges),
        "source_disjoint_speaker_count": len(used_speakers),
        "training_speakers_per_thing": TRAINING_SPEAKERS_PER_THING,
        "user_authorized_learned_interval_physics": True,
    }
    report["authority_receipt_sha256"] = _digest({
        key: value
        for key, value in report.items()
        if key != "authority_receipt_sha256"
    })
    return report


if __name__ == "__main__":
    print(json.dumps(run_probe(), indent=2, sort_keys=True))
