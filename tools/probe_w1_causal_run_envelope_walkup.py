"""Exact experience-grown causal run-envelope hearing walk-up.

This is an isolated falsification boundary, not production architecture.
Each causally grounded THING grows lane-local monotonic-run envelopes and
transition topology from source-disjoint bilateral full-field occurrences.
Observed extrema are the only boundaries.  No distance, epsilon, score,
nearest exemplar, majority vote, transcript identity, or fixed tempo
tolerance exists.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import zipfile
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Mapping, Sequence

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.canonical_l6 import (
    canonical_l6_direction,
)
from dsf_ai_service.substrate.w1_loom_auditory_bridge import (
    BILATERAL_RELATION_FIELDS,
    PHYSICAL_LANES,
    _durations,
    _expanded_field,
    _physical_values,
)
from tools.probe_auditory_full_field_separability_census import (
    ARCHIVE_SHA256,
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


SCHEMA = "guala.audit.w1_causal_run_envelope_walkup.v1"

LaneKey = tuple[str, str, str, str]
RunKey = tuple[int, int, int]


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


def _sign(value: Fraction) -> int:
    return (value > 0) - (value < 0)


@dataclass(frozen=True, slots=True)
class ExactRun:
    key: RunKey
    duration: Fraction
    start: Fraction
    end: Fraction
    lower: Fraction
    upper: Fraction


@dataclass(slots=True)
class ExactRunEnvelope:
    duration_lower: Fraction
    duration_upper: Fraction
    start_lower: Fraction
    start_upper: Fraction
    end_lower: Fraction
    end_upper: Fraction
    value_lower: Fraction
    value_upper: Fraction

    @classmethod
    def from_run(cls, run: ExactRun) -> "ExactRunEnvelope":
        return cls(
            duration_lower=run.duration,
            duration_upper=run.duration,
            start_lower=run.start,
            start_upper=run.start,
            end_lower=run.end,
            end_upper=run.end,
            value_lower=run.lower,
            value_upper=run.upper,
        )

    def grow(self, run: ExactRun) -> None:
        self.duration_lower = min(self.duration_lower, run.duration)
        self.duration_upper = max(self.duration_upper, run.duration)
        self.start_lower = min(self.start_lower, run.start)
        self.start_upper = max(self.start_upper, run.start)
        self.end_lower = min(self.end_lower, run.end)
        self.end_upper = max(self.end_upper, run.end)
        self.value_lower = min(self.value_lower, run.lower)
        self.value_upper = max(self.value_upper, run.upper)

    def contains(self, run: ExactRun) -> bool:
        return (
            self.duration_lower <= run.duration <= self.duration_upper
            and self.start_lower <= run.start <= self.start_upper
            and self.end_lower <= run.end <= self.end_upper
            and self.value_lower <= run.lower
            and run.upper <= self.value_upper
        )

    def record(self) -> dict[str, str]:
        return {
            "duration_lower": _fraction_text(self.duration_lower),
            "duration_upper": _fraction_text(self.duration_upper),
            "end_lower": _fraction_text(self.end_lower),
            "end_upper": _fraction_text(self.end_upper),
            "start_lower": _fraction_text(self.start_lower),
            "start_upper": _fraction_text(self.start_upper),
            "value_lower": _fraction_text(self.value_lower),
            "value_upper": _fraction_text(self.value_upper),
        }


@dataclass(slots=True)
class LaneRunBasin:
    nodes: dict[RunKey, ExactRunEnvelope]
    edges: set[tuple[RunKey, RunKey]]
    starts: set[RunKey]
    ends: set[RunKey]

    @classmethod
    def create(cls) -> "LaneRunBasin":
        return cls(nodes={}, edges=set(), starts=set(), ends=set())

    def grow(self, runs: Sequence[ExactRun]) -> None:
        if not runs:
            raise ValueError("run basin cannot learn an empty lane")
        self.starts.add(runs[0].key)
        self.ends.add(runs[-1].key)
        for run in runs:
            envelope = self.nodes.get(run.key)
            if envelope is None:
                self.nodes[run.key] = ExactRunEnvelope.from_run(run)
            else:
                envelope.grow(run)
        self.edges.update(
            (left.key, right.key)
            for left, right in zip(runs, runs[1:])
        )

    def contains(self, runs: Sequence[ExactRun]) -> bool:
        if (
            not runs
            or runs[0].key not in self.starts
            or runs[-1].key not in self.ends
            or any(
                run.key not in self.nodes
                or not self.nodes[run.key].contains(run)
                for run in runs
            )
            or any(
                (left.key, right.key) not in self.edges
                for left, right in zip(runs, runs[1:])
            )
        ):
            return False
        return True


def _runs(
    values: Sequence[Fraction],
    durations: Sequence[Fraction],
) -> tuple[ExactRun, ...]:
    if (
        len(values) != len(durations)
        or not values
        or any(value <= 0 for value in durations)
    ):
        raise ValueError("run source lost its exact causal grid")
    if len(values) == 1:
        return (
            ExactRun(
                key=(2, 0, 2),
                duration=durations[0],
                start=values[0],
                end=values[0],
                lower=values[0],
                upper=values[0],
            ),
        )
    directions = tuple(
        _sign(right - left)
        for left, right in zip(values, values[1:])
    )
    spans = []
    start = 0
    for index in range(1, len(directions)):
        if directions[index] != directions[start]:
            spans.append((start, index, directions[start]))
            start = index
    spans.append((start, len(directions), directions[start]))
    result = []
    for ordinal, (start_index, end_index, direction) in enumerate(spans):
        sample_start = start_index
        sample_end = end_index
        samples = tuple(values[sample_start:sample_end + 1])
        prior_direction = spans[ordinal - 1][2] if ordinal else 2
        next_direction = (
            spans[ordinal + 1][2]
            if ordinal + 1 < len(spans)
            else 2
        )
        result.append(ExactRun(
            key=(prior_direction, direction, next_direction),
            duration=sum(
                durations[sample_start:sample_end + 1],
                Fraction(0),
            ),
            start=samples[0],
            end=samples[-1],
            lower=min(samples),
            upper=max(samples),
        ))
    return tuple(result)


def _trajectory(settlement) -> dict[
    LaneKey,
    tuple[tuple[Fraction, ...], tuple[Fraction, ...]],
]:
    settlement.verify()
    result = {}
    for ear in settlement.ears:
        for channel in ear.event.channels:
            durations = _durations(channel)
            for component, fields in (
                ("phase", channel.phase_fields),
                ("pressure", channel.pressure_fields),
            ):
                for field_name in DSF_FIELD_ORDER:
                    result[(
                        ear.ear_id,
                        channel.channel_id,
                        component,
                        field_name,
                    )] = (
                        _expanded_field(
                            channel,
                            component=component,
                            field_name=field_name,
                        ),
                        durations,
                    )
            for component, field_names in PHYSICAL_LANES.items():
                for field_name in field_names:
                    result[(
                        ear.ear_id,
                        channel.channel_id,
                        component,
                        field_name,
                    )] = (
                        _physical_values(channel, field_name),
                        durations,
                    )
    left, right = settlement.ears
    for left_channel, right_channel in zip(
        left.event.channels,
        right.event.channels,
        strict=True,
    ):
        durations = _durations(left_channel)
        relations = {
            "pressure_difference": tuple(
                left_frame.pressure_amplitude
                - right_frame.pressure_amplitude
                for left_frame, right_frame in zip(
                    left_channel.frames,
                    right_channel.frames,
                    strict=True,
                )
            ),
            "relevance_difference": tuple(
                left_frame.relevance - right_frame.relevance
                for left_frame, right_frame in zip(
                    left_channel.frames,
                    right_channel.frames,
                    strict=True,
                )
            ),
            "cumulative_phase_difference": tuple(
                left_frame.cumulative_phase_turns
                - right_frame.cumulative_phase_turns
                for left_frame, right_frame in zip(
                    left_channel.frames,
                    right_channel.frames,
                    strict=True,
                )
            ),
            "phase_advance_difference": tuple(
                left_frame.phase_advance_turns
                - right_frame.phase_advance_turns
                for left_frame, right_frame in zip(
                    left_channel.frames,
                    right_channel.frames,
                    strict=True,
                )
            ),
            "source_time_difference": tuple(
                left_frame.source_time - right_frame.source_time
                for left_frame, right_frame in zip(
                    left_channel.frames,
                    right_channel.frames,
                    strict=True,
                )
            ),
        }
        if tuple(relations) != BILATERAL_RELATION_FIELDS:
            raise ValueError("bilateral run relation order changed")
        for relation_name, values in relations.items():
            result[(
                "bilateral",
                left_channel.channel_id,
                "interaural",
                relation_name,
            )] = (values, durations)
    if len(result) != 656:
        raise ValueError("run envelope lost full receptor topology")
    return result


def _grow(
    memories: dict[str, dict[LaneKey, LaneRunBasin]],
    thing_id: str,
    trajectory,
) -> None:
    memory = memories.setdefault(thing_id, {})
    for lane, (values, durations) in trajectory.items():
        basin = memory.setdefault(lane, LaneRunBasin.create())
        basin.grow(_runs(values, durations))


def _settle(memories, trajectory) -> dict[str, object]:
    relations = {}
    for thing_id, memory in sorted(memories.items()):
        matching = sum(
            memory[lane].contains(_runs(values, durations))
            for lane, (values, durations) in trajectory.items()
        )
        direction = canonical_l6_direction(
            dimensions=len(memory),
            matching_non_null=matching,
            matching_quiescent=0,
        )
        relations[thing_id] = {
            "dimensions": direction.dimensions,
            "effective_dimensions": direction.effective_dimensions,
            "knee": direction.knee,
            "locked": direction.locked,
            "matching_non_null": direction.matching_non_null,
        }
    locked = tuple(
        thing_id
        for thing_id, relation in relations.items()
        if relation["locked"]
    )
    return {
        "relations": relations,
        "state": (
            "resolved"
            if len(locked) == 1
            else "ambiguous"
            if locked
            else "unknown"
        ),
        "thing_ids": list(locked),
    }


def _thing_id(target_ordinal: int) -> str:
    return _digest({
        "physical_action_target_ordinal": target_ordinal,
        "schema": "guala.audit.run_envelope_grounding.v1",
    })


def run(archive_path: Path) -> dict[str, object]:
    archive_bytes = archive_path.read_bytes()
    archive_sha256 = hashlib.sha256(archive_bytes).hexdigest()
    if archive_sha256 != ARCHIVE_SHA256:
        raise ValueError("speech corpus authority changed")
    with zipfile.ZipFile(archive_path) as archive:
        corpus = _select_corpus(archive)
        references = tuple(
            item
            for command in TEST_COMMANDS
            for item in corpus
            if item.oracle_command == command and item.split == "reference"
        )
        held_out = tuple(
            next(
                item
                for item in corpus
                if item.oracle_command == command
                and item.split == "held_out"
            )
            for command in TEST_COMMANDS
        )
        tone = _tone_item()
        ordered = (*references, *held_out, tone)
        pcm_by_item = {
            item.item_id: _read_pcm(archive.read(item.archive_member))
            for item in (*references, *held_out)
        } | {tone.item_id: _tone_pcm()}
    if len(references) != len(TEST_COMMANDS) * REFERENCE_COUNT:
        raise ValueError("run-envelope reference split changed")
    episodes = _mount_episodes(ordered, pcm_by_item)
    by_id = {value.item.item_id: value for value in episodes}
    trajectories = {
        value.item.item_id: _trajectory(
            value.mount.binaural_receptor_settlement
        )
        for value in episodes
    }
    memories: dict[str, dict[LaneKey, LaneRunBasin]] = {}
    learning = []
    for item in references:
        episode = by_id[item.item_id]
        thing_id = _thing_id(episode.target_ordinal)
        _grow(memories, thing_id, trajectories[item.item_id])
        learning.append({
            "grounding_authority_receipt_sha256": (
                episode.context_signature_sha256
            ),
            "item_id": item.item_id,
            "thing_id": thing_id,
        })
    held_records = []
    for item in held_out:
        episode = by_id[item.item_id]
        expected = _thing_id(episode.target_ordinal)
        settlement = _settle(memories, trajectories[item.item_id])
        held_records.append({
            "expected_thing_id": expected,
            "item_id": item.item_id,
            "passed": (
                settlement["state"] == "resolved"
                and settlement["thing_ids"] == [expected]
            ),
            "settlement": settlement,
        })
    tone_settlement = _settle(memories, trajectories[tone.item_id])
    memory_payload = {
        thing_id: {
            "|".join(lane): {
                "edges": [
                    [list(left), list(right)]
                    for left, right in sorted(basin.edges)
                ],
                "ends": [list(value) for value in sorted(basin.ends)],
                "nodes": {
                    ",".join(map(str, key)): envelope.record()
                    for key, envelope in sorted(basin.nodes.items())
                },
                "starts": [list(value) for value in sorted(basin.starts)],
            }
            for lane, basin in sorted(memory.items())
        }
        for thing_id, memory in sorted(memories.items())
    }
    payload = {
        "archive_sha256": archive_sha256,
        "commands_used_only_after_physical_settlement": list(TEST_COMMANDS),
        "dynamic_mosaic_growth": (
            "each grounded occurrence expands exact extrema, duration, "
            "and transition envelopes; no stored exemplar is queried"
        ),
        "full_binaural_field_lane_count": 656,
        "held_out": held_records,
        "held_out_pass_count": sum(
            value["passed"] for value in held_records
        ),
        "learning": learning,
        "memory_authority_receipt_sha256": _digest(memory_payload),
        "overall_pass": (
            all(value["passed"] for value in held_records)
            and tone_settlement["state"] != "resolved"
        ),
        "schema": SCHEMA,
        "source_disjoint_speaker_count": (
            len(references) + len(held_out)
        ),
        "tempo_law": (
            "run duration intervals are exact extrema learned from causal "
            "occurrences; no fixed timing tolerance"
        ),
        "tone": tone_settlement,
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
    ) + "\n"
    if args.output is not None:
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")


if __name__ == "__main__":
    main()
