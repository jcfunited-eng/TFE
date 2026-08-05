"""Falsify candidate exact co-resonance relations before production wiring.

This probe mounts real W1 binaural speech, advances the authentic Loom
auditory bridge, and derives exact local transition relations only from the
bridge's parallel rational winding authority.  Corpus command names are
withheld from every sensory computation and are used only to group already
settled causal demonstrations and score held-out results.

The candidates are not production identity.  A candidate must separate
held-out speakers and reject an unrelated tone before its relation can be
considered for a bounded causal THING coupling owner.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.loom_model.brain import LoomBrain
from dsf_ai_service.substrate.canonical_l6 import (
    canonical_l6_direction,
)
from dsf_ai_service.substrate.w1_loom_auditory_bridge import (
    W1LoomAuditoryBridge,
    W1LoomAuditoryDynamicsOccurrence,
)
from tools.probe_auditory_full_field_separability_census import (
    ARCHIVE_SHA256,
    CorpusItem,
    _select_corpus,
)
from tools.probe_contextual_thing_mosaic_settling import (
    REFERENCE_COUNT,
    TEST_COMMANDS,
    _mount_episodes,
    _tone_item,
    _tone_pcm,
)
from tools.probe_existing_auditory_neuron_temporal_go_no_go import (
    _read_pcm,
)


SCHEMA = "guala.audit.w1_loom_bilateral_coupling_walkup.v1"
AUTHORITY_KEY = b"guala-w1-loom-bilateral-coupling-walkup-20260727"
CANDIDATES = (
    "lane_transition",
    "homologous_bilateral_coupling",
    "pressure_phase_coupling",
    "adjacent_cochlear_coupling",
    "within_component_field_coupling",
    "all_physical_couplings",
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


def _sign(value: int) -> int:
    return (value > 0) - (value < 0)


def _order(left: int, right: int) -> int:
    return (left > right) - (left < right)


def _transition_cells(
    relation_key: tuple[object, ...],
    sequences: Sequence[tuple[int, ...]],
) -> frozenset[tuple[object, ...]]:
    if not sequences or len({len(value) for value in sequences}) != 1:
        raise ValueError("coupling sequences left their common causal grid")
    events = []
    for index, deltas in enumerate(zip(*sequences, strict=True)):
        if not any(deltas):
            continue
        state = tuple(_sign(value) for value in deltas)
        magnitude_orders = tuple(
            _order(abs(left), abs(right))
            for left, right in zip(deltas, deltas[1:])
        )
        events.append((index, state, magnitude_orders))
    cells = set()
    for left, middle, right in zip(
        events,
        events[1:],
        events[2:],
    ):
        left_gap = middle[0] - left[0]
        right_gap = right[0] - middle[0]
        cells.add((
            *relation_key,
            left[1],
            middle[1],
            right[1],
            left[2],
            middle[2],
            right[2],
            _order(right_gap, left_gap),
        ))
    return frozenset(cells)


def _lane_map(
    occurrence: W1LoomAuditoryDynamicsOccurrence,
) -> dict[tuple[str, str, str, str], tuple[int, ...]]:
    occurrence.verify()
    return {
        value.lane_key: value.exact_winding_deltas
        for value in occurrence.lanes
    }


def _lane_cells(
    lanes: Mapping[
        tuple[str, str, str, str],
        tuple[int, ...],
    ],
) -> frozenset[tuple[object, ...]]:
    return frozenset().union(*(
        _transition_cells(("lane", *lane), (sequence,))
        for lane, sequence in lanes.items()
    ))


def _homologous_edges(lanes):
    for lane in sorted(lanes):
        route, channel, component, field = lane
        if route != "left":
            continue
        right = ("right", channel, component, field)
        if right in lanes:
            yield ("homologous", channel, component, field), lane, right


def _pressure_phase_edges(lanes):
    for route in ("left", "right"):
        for channel_index in range(16):
            channel = f"erb_{channel_index:02d}"
            for field in DSF_FIELD_ORDER:
                pressure = (route, channel, "pressure", field)
                phase = (route, channel, "phase", field)
                if pressure in lanes and phase in lanes:
                    yield (
                        "pressure_phase",
                        route,
                        channel,
                        field,
                    ), pressure, phase


def _adjacent_edges(lanes):
    for route in ("left", "right", "bilateral"):
        keys = sorted(
            lane for lane in lanes if lane[0] == route
        )
        by_coordinate = {}
        for lane in keys:
            _route, channel, component, field = lane
            by_coordinate[
                (int(channel.split("_")[1]), component, field)
            ] = lane
        for (index, component, field), lane in sorted(
            by_coordinate.items()
        ):
            adjacent = by_coordinate.get(
                (index + 1, component, field)
            )
            if adjacent is not None:
                yield (
                    "adjacent",
                    route,
                    component,
                    field,
                    index,
                ), lane, adjacent


def _within_field_edges(lanes):
    fields = tuple(DSF_FIELD_ORDER)
    for route in ("left", "right"):
        for channel_index in range(16):
            channel = f"erb_{channel_index:02d}"
            for component in ("pressure", "phase"):
                for left_index, left_field in enumerate(fields):
                    for right_field in fields[left_index + 1:]:
                        left = (
                            route,
                            channel,
                            component,
                            left_field,
                        )
                        right = (
                            route,
                            channel,
                            component,
                            right_field,
                        )
                        if left in lanes and right in lanes:
                            yield (
                                "within_field",
                                route,
                                channel,
                                component,
                                left_field,
                                right_field,
                            ), left, right


def _edge_cells(lanes, edges):
    return frozenset().union(*(
        _transition_cells(
            relation,
            (lanes[left], lanes[right]),
        )
        for relation, left, right in edges
    ))


def _candidate_populations(
    occurrence: W1LoomAuditoryDynamicsOccurrence,
) -> dict[str, frozenset[tuple[object, ...]]]:
    lanes = _lane_map(occurrence)
    homologous = _edge_cells(lanes, tuple(_homologous_edges(lanes)))
    pressure_phase = _edge_cells(
        lanes,
        tuple(_pressure_phase_edges(lanes)),
    )
    adjacent = _edge_cells(lanes, tuple(_adjacent_edges(lanes)))
    within = _edge_cells(
        lanes,
        tuple(_within_field_edges(lanes)),
    )
    return {
        "lane_transition": _lane_cells(lanes),
        "homologous_bilateral_coupling": homologous,
        "pressure_phase_coupling": pressure_phase,
        "adjacent_cochlear_coupling": adjacent,
        "within_component_field_coupling": within,
        "all_physical_couplings": (
            homologous | pressure_phase | adjacent | within
        ),
    }


def _recurrent(
    populations: Sequence[frozenset[object]],
) -> frozenset[object]:
    union = frozenset().union(*populations)
    return frozenset(
        value
        for value in union
        if canonical_l6_direction(
            dimensions=len(populations),
            matching_non_null=sum(
                value in population
                for population in populations
            ),
            matching_quiescent=0,
        ).locked
    )


def _fission(
    memories: Mapping[str, frozenset[object]],
) -> dict[str, frozenset[object]]:
    shared = frozenset(
        value
        for value in frozenset().union(*memories.values())
        if sum(value in memory for memory in memories.values()) > 1
    )
    return {
        command: memory - shared
        for command, memory in memories.items()
    }


def _settle(
    memories: Mapping[str, frozenset[object]],
    population: frozenset[object],
) -> dict[str, object]:
    relations = {}
    for command, memory in memories.items():
        if not memory:
            relations[command] = {
                "dimensions": 0,
                "effective_dimensions": 0,
                "knee": 0,
                "locked": False,
                "matching": 0,
            }
            continue
        matching = len(memory.intersection(population))
        direction = canonical_l6_direction(
            dimensions=len(memory),
            matching_non_null=matching,
            matching_quiescent=0,
        )
        relations[command] = {
            "dimensions": direction.dimensions,
            "effective_dimensions": direction.effective_dimensions,
            "knee": direction.knee,
            "locked": direction.locked,
            "matching": matching,
        }
    locked = tuple(
        command
        for command, relation in relations.items()
        if relation["locked"]
    )
    return {
        "locked": list(locked),
        "relations": relations,
        "state": (
            "resolved"
            if len(locked) == 1
            else "unknown"
            if not locked
            else "ambiguous"
        ),
    }


def run(archive_path: Path) -> dict[str, object]:
    archive_bytes = archive_path.read_bytes()
    if hashlib.sha256(archive_bytes).hexdigest() != ARCHIVE_SHA256:
        raise ValueError("speech corpus authority changed")
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
        tone = _tone_item()
        ordered = (*references, *held_out, tone)
        pcm_by_item = {
            item.item_id: _read_pcm(
                archive.read(item.archive_member)
            )
            for item in (*references, *held_out)
        } | {tone.item_id: _tone_pcm()}
    if len(references) != len(TEST_COMMANDS) * REFERENCE_COUNT:
        raise ValueError("walk-up reference split changed")
    episodes = _mount_episodes(ordered, pcm_by_item)
    brain = LoomBrain(seed_size=8, observable="event_count")
    bridge = W1LoomAuditoryBridge(brain)
    populations = {}
    for episode in episodes:
        bridge.settle(
            episode.mount.binaural_receptor_settlement
        )
        dynamics = bridge.latest_dynamics
        if dynamics is None:
            raise RuntimeError(
                "authentic bridge produced no exact dynamics"
            )
        populations[episode.item.item_id] = (
            _candidate_populations(dynamics)
        )
    results = {}
    for candidate in CANDIDATES:
        memories = _fission({
            command: _recurrent(tuple(
                populations[item.item_id][candidate]
                for item in references
                if item.oracle_command == command
            ))
            for command in TEST_COMMANDS
        })
        held_records = []
        for item in held_out:
            settled = _settle(
                memories,
                populations[item.item_id][candidate],
            )
            held_records.append({
                "expected": item.oracle_command,
                "passed": (
                    settled["state"] == "resolved"
                    and settled["locked"] == [
                        item.oracle_command
                    ]
                ),
                "settlement": settled,
            })
        tone_settlement = _settle(
            memories,
            populations[tone.item_id][candidate],
        )
        results[candidate] = {
            "held_out": held_records,
            "held_out_pass_count": sum(
                value["passed"] for value in held_records
            ),
            "memory_dimensions": {
                command: len(memory)
                for command, memory in memories.items()
            },
            "passed": (
                all(value["passed"] for value in held_records)
                and tone_settlement["state"] != "resolved"
            ),
            "tone": tone_settlement,
        }
    payload = {
        "archive_sha256": hashlib.sha256(
            archive_bytes
        ).hexdigest(),
        "candidate_results": results,
        "commands_used_only_after_settlement": list(
            TEST_COMMANDS
        ),
        "full_binaural_field_preserved": True,
        "legacy_wave_summary_used": False,
        "overall_pass": any(
            value["passed"] for value in results.values()
        ),
        "schema": SCHEMA,
        "source_disjoint_speaker_count": (
            len(references) + len(held_out)
        ),
    }
    return payload | {
        "authority_receipt_sha256": hashlib.sha256(
            AUTHORITY_KEY + b"\0" + _canonical(payload)
        ).hexdigest(),
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
    ) + "\n"
    if args.output is not None:
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")


if __name__ == "__main__":
    main()
