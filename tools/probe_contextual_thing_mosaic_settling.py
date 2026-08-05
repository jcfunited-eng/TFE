"""Real contextual THING-mosaic settling probe.

Speech recordings are mounted only after an embodied actor has picked one
physical object and executed an actual place-changing action.  Repeated
speaker variants share an assembly only through the resulting authenticated
non-auditory full-field context, never through a command label.

The existing bilateral motif bank supplies auditory activations with complete
D/M/R/U/C/P/B occurrence witnesses.  Canonical L6 settles the joint
auditory-plus-context assembly.  Auditory support must be nonempty.  This
probe intentionally challenges the resulting assembly with a different
command and an unrelated tone inside the otherwise expected context, because
context is not allowed to manufacture hearing.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import io
import json
import math
import struct
import wave
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from dsf_ai_service.substrate.auditory_recurrent_motif import (
    AuditoryMotifResourceProfile,
    AuditoryRecurrentMotifOwner,
)
from dsf_ai_service.substrate.canonical_l6 import canonical_l6_direction
from dsf_ai_service.substrate.causal_thing_mosaic import (
    full_field_sensory_roots,
)
from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
    MoveCommand,
    PoseMM,
    PositionMM,
    encode_command,
)
from tools.probe_auditory_full_field_separability_census import (
    ARCHIVE_SHA256,
    COMMANDS,
    CorpusItem,
    _select_corpus,
)
from tools.probe_existing_auditory_neuron_temporal_go_no_go import (
    _read_pcm,
)
from tests.test_w1_audiovisual_physical_evidence import (
    EVIDENCE_KEY,
    _authority,
    _emission,
    _execution,
    _vocal_execution,
    _world,
)


SCHEMA = "guala.audit.contextual_thing_mosaic_settling.v1"
TEST_COMMANDS = COMMANDS[:3]
REFERENCE_COUNT = 5
HELD_OUT_COUNT = 1
ACTION_TARGETS = (
    PositionMM(1_000, 800, 0),
    PositionMM(1_400, 1_000, 0),
    PositionMM(800, 1_000, 0),
)
EXPECTED_CONTEXT_SENSES = frozenset(
    ("body", "sight", "smell", "taste", "touch")
)
KEY = b"guala-contextual-thing-mosaic-settling-20260727"


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


def _motif_owner() -> AuditoryRecurrentMotifOwner:
    return AuditoryRecurrentMotifOwner(
        AuditoryMotifResourceProfile.create(
            profile_id="contextual-thing-bilateral-motif",
            ear_count=2,
            max_motif_neurons=24_192,
            max_pending_experiences=8,
            max_work_cells_per_observation=8_000_000,
            max_exact_fraction_text_bytes=4_096,
            encoded_state_allocation_bytes=256 * 1024 * 1024,
        ),
        ear_ids=("left", "right"),
    )


@dataclass(frozen=True, slots=True)
class LivedContextualEpisode:
    item: CorpusItem
    target_ordinal: int
    action_execution_receipt_sha256: str
    action_before_receipt_sha256: str
    action_after_receipt_sha256: str
    vocal_execution_receipt_sha256: str
    binaural_settlement_receipt_sha256: str
    full_context_route_keys: tuple[tuple[str, str], ...]
    typed_context_cells: tuple[tuple[str, ...], ...]
    context_signature_sha256: str
    mount: object


def _move(world, target: PositionMM, ordinal: int):
    before = world.observation_snapshot()
    result = world.execute_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(
            MoveCommand(PoseMM(target, 0))
        ),
        causal_intent_receipt_sha256=_digest({
            "action_ordinal": ordinal,
            "before_receipt_sha256": (
                before.authority_receipt_sha256
            ),
            "schema": "guala.audit.contextual_action_intent.v1",
        }),
        expected_revision=before.revision,
    )
    if result.disposition != "applied":
        raise ValueError("contextual action was not physically applied")
    return result


def _context_route_keys(settlement) -> tuple[tuple[str, str], ...]:
    roots = tuple(
        root
        for root in full_field_sensory_roots(settlement)
        if root.sense in EXPECTED_CONTEXT_SENSES
    )
    if not roots:
        raise ValueError("contextual episode lacks embodied full fields")
    return tuple(sorted(root.route_key for root in roots))


def _context_cells(
    settlement,
    action,
) -> tuple[tuple[str, ...], ...]:
    roots = tuple(
        root
        for root in full_field_sensory_roots(settlement)
        if root.sense in EXPECTED_CONTEXT_SENSES
    )
    cells = []
    for root in roots:
        evidence = json.loads(root.full_evidence_json)
        for field_tuple in evidence["field_tuples"]:
            for field_name, field_value in field_tuple["fields"]:
                cells.append((
                    "full_field",
                    root.sense,
                    str(root.topology_index),
                    root.physical_value_sha256,
                    str(field_tuple["tuple_index"]),
                    field_name,
                    field_value,
                ))
    before_body = next(
        body
        for body in action.before.bodies
        if body.body_id == action.actor_body_id
    )
    after_body = next(
        body
        for body in action.after.bodies
        if body.body_id == action.actor_body_id
    )
    held_continuity = hmac.new(
        KEY,
        (
            b"guala-contextual-held-entity-v1\0"
            + str(after_body.held_object_id).encode("utf-8")
        ),
        hashlib.sha256,
    ).hexdigest()
    before_position = before_body.pose.position
    after_position = after_body.pose.position
    cells.extend((
        ("held_entity_continuity", held_continuity),
        ("place_x_mm", str(after_position.x)),
        ("place_y_mm", str(after_position.y)),
        ("place_z_mm", str(after_position.z)),
        (
            "body_heading_millidegrees",
            str(after_body.pose.heading_millidegrees),
        ),
        (
            "action_delta_x_mm",
            str(after_position.x - before_position.x),
        ),
        (
            "action_delta_y_mm",
            str(after_position.y - before_position.y),
        ),
        (
            "action_delta_z_mm",
            str(after_position.z - before_position.z),
        ),
        (
            "action_delta_heading_millidegrees",
            str(
                after_body.pose.heading_millidegrees
                - before_body.pose.heading_millidegrees
            ),
        ),
        ("causal_time_relation", "action_before_vocal_observation"),
    ))
    if len(cells) != len(set(cells)):
        raise ValueError("contextual assembly collapsed repeated field cells")
    return tuple(sorted(cells))


def _mount_episodes(
    ordered: Sequence[CorpusItem],
    pcm_by_item: Mapping[str, bytes],
) -> tuple[LivedContextualEpisode, ...]:
    world = _world()
    physical = _authority(world)
    pick = _execution(world)
    if pick.disposition != "applied":
        raise ValueError("contextual object was not physically held")
    results = []
    target_by_command = dict(zip(
        TEST_COMMANDS,
        ACTION_TARGETS,
        strict=True,
    ))
    for sequence, item in enumerate(ordered):
            target = target_by_command[item.oracle_command]
            target_ordinal = ACTION_TARGETS.index(target)
            action = _move(world, target, sequence)
            pcm = pcm_by_item[item.item_id]
            epoch = physical.open_epoch()
            vocal = _vocal_execution(
                world,
                epoch,
                sequence=0,
                source_sample_start=0,
                pcm=pcm,
            )
            emission = _emission(
                physical,
                epoch,
                vocal,
                sequence=0,
                source_sample_start=0,
                pcm=pcm,
            )
            mount = physical.mount(
                epoch_token=epoch,
                sequence=0,
                execution_receipt=vocal,
                acoustic_emission=emission,
            )
            if not physical.close_epoch(epoch):
                raise ValueError(
                    "contextual auditory epoch did not close exactly"
                )
            mount.verify(EVIDENCE_KEY)
            if (
                mount.causal_settlement is None
                or mount.binaural_receptor_settlement is None
            ):
                raise ValueError(
                    "contextual episode lacks settled physical evidence: "
                    f"state={mount.state!r}, reason={mount.reason!r}"
                )
            route_keys = _context_route_keys(
                mount.causal_settlement
            )
            context_cells = _context_cells(
                mount.causal_settlement,
                action,
            )
            results.append(LivedContextualEpisode(
                item=item,
                target_ordinal=target_ordinal,
                action_execution_receipt_sha256=(
                    action.authority_receipt_sha256
                ),
                action_before_receipt_sha256=(
                    action.before.authority_receipt_sha256
                ),
                action_after_receipt_sha256=(
                    action.after.authority_receipt_sha256
                ),
                vocal_execution_receipt_sha256=(
                    vocal.authority_receipt_sha256
                ),
                binaural_settlement_receipt_sha256=(
                    mount.binaural_receptor_settlement
                    .authority_receipt_sha256
                ),
                full_context_route_keys=route_keys,
                typed_context_cells=context_cells,
                context_signature_sha256=_digest({
                    "context_cells": [
                        list(value) for value in context_cells
                    ],
                    "schema": (
                        "guala.audit.embodied_context_signature.v1"
                    ),
                }),
                mount=mount,
            ))
    return tuple(results)


def _locked_recurrence(
    populations: Sequence[frozenset[object]],
) -> frozenset[object]:
    population = frozenset().union(*populations)
    return frozenset(
        value
        for value in population
        if canonical_l6_direction(
            dimensions=len(populations),
            matching_non_null=sum(
                value in observed for observed in populations
            ),
            matching_quiescent=0,
        ).locked
    )


def _fission(
    recurrent: Mapping[str, frozenset[object]],
) -> dict[str, frozenset[object]]:
    shared = frozenset(
        value
        for population in recurrent.values()
        for value in population
        if sum(
            value in other
            for other in recurrent.values()
        ) > 1
    )
    return {
        key: values.difference(shared)
        for key, values in recurrent.items()
    }


def _assembly_relation(
    *,
    required_auditory: frozenset[str],
    required_context: frozenset[tuple[str, ...]],
    observed_auditory: frozenset[str],
    active_context: frozenset[tuple[str, ...]],
) -> dict[str, object]:
    auditory_matching = len(
        required_auditory.intersection(observed_auditory)
    )
    context_matching = len(
        required_context.intersection(active_context)
    )
    dimensions = len(required_auditory) + len(required_context)
    if not dimensions:
        return {
            "auditory_matching": 0,
            "context_matching": 0,
            "dimensions": 0,
            "effective_dimensions": 0,
            "knee": 0,
            "locked": False,
        }
    direction = canonical_l6_direction(
        dimensions=dimensions,
        matching_non_null=auditory_matching + context_matching,
        matching_quiescent=0,
    )
    return {
        "auditory_matching": auditory_matching,
        "context_matching": context_matching,
        "dimensions": dimensions,
        "effective_dimensions": direction.effective_dimensions,
        "knee": direction.knee,
        "locked": (
            direction.locked
            and auditory_matching > 0
            and context_matching > 0
        ),
    }


def _settle(
    auditory_memories: Mapping[str, frozenset[str]],
    context_memories: Mapping[
        str,
        frozenset[tuple[str, ...]],
    ],
    *,
    observed_auditory: frozenset[str],
    active_context: frozenset[tuple[str, ...]],
) -> dict[str, object]:
    relations = {
        command: _assembly_relation(
            required_auditory=auditory_memories[command],
            required_context=context_memories[command],
            observed_auditory=observed_auditory,
            active_context=active_context,
        )
        for command in auditory_memories
    }
    locked = tuple(
        command
        for command, relation in relations.items()
        if relation["locked"]
    )
    return {
        "locked_groundings": list(locked),
        "relations": relations,
        "state": (
            "resolved"
            if len(locked) == 1
            else "unknown"
            if not locked
            else "ambiguous"
        ),
    }


def _tone_pcm() -> bytes:
    samples = tuple(
        int(
            round(
                8_000
                * math.sin(2 * math.pi * 733 * index / 16_000)
            )
        )
        for index in range(16_000)
    )
    return struct.pack(f"<{len(samples)}h", *samples)


def _tone_item() -> CorpusItem:
    pcm = _tone_pcm()
    return CorpusItem(
        item_id=_digest({
            "pcm_sha256": hashlib.sha256(pcm).hexdigest(),
            "schema": "guala.audit.contextual_tone_item.v1",
        }),
        oracle_command=TEST_COMMANDS[0],
        speaker_id="unrelated-tone",
        archive_member="generated-physical-tone",
        pcm_sha256=hashlib.sha256(pcm).hexdigest(),
        split="challenge",
        ordinal=99,
    )


def run(archive_path: Path) -> dict[str, object]:
    archive_sha256 = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    if archive_sha256 != ARCHIVE_SHA256:
        raise ValueError("speech corpus archive authority changed")
    with zipfile.ZipFile(archive_path) as archive:
        corpus = _select_corpus(archive)
        references = tuple(
            item
            for command in TEST_COMMANDS
            for item in corpus
            if (
                item.oracle_command == command
                and item.split == "reference"
            )
        )
        held_out = tuple(
            next(
                item
                for item in corpus
                if (
                    item.oracle_command == command
                    and item.split == "held_out"
                )
            )
            for command in TEST_COMMANDS
        )
        tone_item = _tone_item()
        ordered = (*references, *held_out, tone_item)
        pcm_by_item = {
            item.item_id: _read_pcm(archive.read(item.archive_member))
            for item in (*references, *held_out)
        } | {
            tone_item.item_id: _tone_pcm(),
        }
    if (
        len(references) != len(TEST_COMMANDS) * REFERENCE_COUNT
        or len(held_out) != len(TEST_COMMANDS) * HELD_OUT_COUNT
    ):
        raise ValueError("contextual corpus split changed")
    episodes = _mount_episodes(ordered, pcm_by_item)
    by_id = {
        episode.item.item_id: episode
        for episode in episodes
    }
    owner = _motif_owner()
    for item in references:
        owner.observe_binaural(
            by_id[
                item.item_id
            ].mount.binaural_receptor_settlement
        )
    reference_auditory = {
        command: tuple(
            frozenset(
                owner.fire_binaural(
                    by_id[
                        item.item_id
                    ].mount.binaural_receptor_settlement
                ).firing.firing_motif_neuron_ids
            )
            for item in references
            if item.oracle_command == command
        )
        for command in TEST_COMMANDS
    }
    reference_context = {
        command: tuple(
            frozenset(by_id[item.item_id].typed_context_cells)
            for item in references
            if item.oracle_command == command
        )
        for command in TEST_COMMANDS
    }
    auditory_memories = _fission({
        command: _locked_recurrence(values)
        for command, values in reference_auditory.items()
    })
    context_memories = {
        command: _locked_recurrence(values)
        for command, values in reference_context.items()
    }
    observed_auditory = {
        item.item_id: frozenset(
            owner.fire_binaural(
                by_id[
                    item.item_id
                ].mount.binaural_receptor_settlement
            ).firing.firing_motif_neuron_ids
        )
        for item in (*held_out, tone_item)
    }
    active_context = {
        item.item_id: frozenset(
            by_id[item.item_id].typed_context_cells
        )
        for item in (*held_out, tone_item)
    }
    correct_records = []
    for item in held_out:
        result = _settle(
            auditory_memories,
            context_memories,
            observed_auditory=observed_auditory[item.item_id],
            active_context=active_context[item.item_id],
        )
        correct_records.append({
            "expected_grounding": item.oracle_command,
            "held_out_item_id": item.item_id,
            "passed": (
                result["state"] == "resolved"
                and result["locked_groundings"]
                == [item.oracle_command]
            ),
            "settlement": result,
        })
    no_context_records = []
    for item in held_out:
        result = _settle(
            auditory_memories,
            context_memories,
            observed_auditory=observed_auditory[item.item_id],
            active_context=frozenset(),
        )
        no_context_records.append({
            "held_out_item_id": item.item_id,
            "passed": result["state"] in ("unknown", "ambiguous"),
            "settlement": result,
        })
    down, go, _left = held_out
    conflicting = _settle(
        auditory_memories,
        context_memories,
        observed_auditory=observed_auditory[down.item_id],
        active_context=(
            active_context[down.item_id]
            | active_context[go.item_id]
        ),
    )
    different_command = _settle(
        auditory_memories,
        context_memories,
        observed_auditory=observed_auditory[go.item_id],
        active_context=active_context[down.item_id],
    )
    unrelated = _settle(
        auditory_memories,
        context_memories,
        observed_auditory=observed_auditory[tone_item.item_id],
        active_context=active_context[tone_item.item_id],
    )
    episode_records = [
        {
            "action_after_receipt_sha256": (
                value.action_after_receipt_sha256
            ),
            "action_before_receipt_sha256": (
                value.action_before_receipt_sha256
            ),
            "action_execution_receipt_sha256": (
                value.action_execution_receipt_sha256
            ),
            "binaural_settlement_receipt_sha256": (
                value.binaural_settlement_receipt_sha256
            ),
            "context_route_count": len(value.full_context_route_keys),
            "context_cell_count": len(value.typed_context_cells),
            "context_signature_sha256": (
                value.context_signature_sha256
            ),
            "item_id": value.item.item_id,
            "target_ordinal": value.target_ordinal,
            "vocal_execution_receipt_sha256": (
                value.vocal_execution_receipt_sha256
            ),
        }
        for value in episodes
    ]
    pass_cells = [
        *(value["passed"] for value in correct_records),
        *(value["passed"] for value in no_context_records),
        conflicting["state"] == "ambiguous",
        different_command["state"] != "resolved",
        unrelated["state"] != "resolved",
    ]
    payload = {
        "archive_sha256": archive_sha256,
        "auditory_memory_dimensions_by_grounding": {
            key: len(value)
            for key, value in auditory_memories.items()
        },
        "challenge_records": {
            "conflicting_context": conflicting,
            "different_command_in_expected_context": different_command,
            "unrelated_tone_in_expected_context": unrelated,
        },
        "commands_used_only_for_post_settlement_scoring": list(
            TEST_COMMANDS
        ),
        "context_memory_dimensions_by_grounding": {
            key: len(value)
            for key, value in context_memories.items()
        },
        "correct_context_records": correct_records,
        "episode_records": episode_records,
        "full_binaural_field_witnesses_retained": True,
        "held_out_correct_context_pass_count": sum(
            value["passed"] for value in correct_records
        ),
        "held_out_correct_context_total": len(correct_records),
        "l0_l4_modified": False,
        "motif_owner_status": owner.status(),
        "no_context_records": no_context_records,
        "overall_pass": all(pass_cells),
        "schema": SCHEMA,
        "source_disjoint_speech_speaker_count": (
            len(references) + len(held_out)
        ),
    }
    return payload | {
        "authority_receipt_sha256": _digest(payload),
    }


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
    ).encode("utf-8") + b"\n"
    if args.output is not None:
        args.output.write_bytes(encoded)
    print(encoded.decode("utf-8"))


if __name__ == "__main__":
    main()
