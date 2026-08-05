"""Isolated deterministic adjacent-ERB relation-field walk-up.

Every adjacent pair in the canonical sixteen-channel cochlear topology
contributes the same six causal relation streams.  No band, ridge, peak, or
time sample is selected.  Absolute ERB coordinates and relative spacing
remain mounted on every stream.  Exact receptor relations are retained as
Fractions; the unchanged native L0--L4 boundary receives their binary64
physical transport representation just as it does for every other sense.

Command labels are unavailable while relations and L0--L4 fields are formed.
They are consulted only after source-disjoint physical experiences exist, to
audit grounded THING basins.  Exact complete-lane containment counts are
diagnostics, not recognition scores.  Canonical L6 is the only lock law.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from fractions import Fraction
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np

from dsf_ai_service.glew_runtime.exact_field_executor import _build_partition
from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    NativeSensorySubstreamInput,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    NativeAxisCoordinate,
    PhysicalSense,
)
from dsf_ai_service.substrate.canonical_l6 import canonical_l6_direction
from dsf_ai_service.substrate.senses import auditory_full_field_provider as provider
from tools.probe_auditory_full_field_separability_census import (
    ARCHIVE_SHA256,
    _pcm_from_wav,
    _select_corpus,
)
from tools.probe_auditory_receptor_topology_census import (
    HOP_DURATION,
    ReceptorCapture,
    _transduce,
)
from tools.probe_contextual_thing_mosaic_settling import (
    REFERENCE_COUNT,
    TEST_COMMANDS,
    _tone_item,
    _tone_pcm,
)
from tools.probe_w1_causal_run_envelope_walkup import (
    LaneRunBasin,
    _runs,
)


SCHEMA = "guala.audit.auditory_cross_band_relation_walkup.v1"
RELATION_NAMES = (
    "envelope_order",
    "envelope_crossing",
    "projective_amplitude_balance",
    "projective_amplitude_motion",
    "carrier_phase_cycle_relation",
    "carrier_phase_advance_relation",
)
CHANNEL_COUNT = provider.COCHLEAR_CHANNEL_COUNT
PAIR_COUNT = CHANNEL_COUNT - 1
RELATION_PORT_COUNT = PAIR_COUNT * len(RELATION_NAMES)

LaneKey = tuple[str, str, str, str]
Trajectory = dict[LaneKey, tuple[Fraction, ...]]


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


def _sign(value: Fraction) -> Fraction:
    return Fraction((value > 0) - (value < 0))


def _wrap_cycle(value: Fraction) -> Fraction:
    return (value + Fraction(1, 2)) % 1 - Fraction(1, 2)


def _relation_trajectory(capture: ReceptorCapture) -> Trajectory:
    if capture.channel_count != CHANNEL_COUNT:
        raise ValueError("cross-band probe requires canonical channel count")
    result: Trajectory = {}
    for left_index in range(PAIR_COUNT):
        right_index = left_index + 1
        pair_id = f"erb_{left_index:02d}_to_erb_{right_index:02d}"
        left_pressure = tuple(
            Fraction.from_float(float(value))
            for value in capture.envelopes[:, left_index]
        )
        right_pressure = tuple(
            Fraction.from_float(float(value))
            for value in capture.envelopes[:, right_index]
        )
        order = tuple(
            _sign(left - right)
            for left, right in zip(
                left_pressure, right_pressure, strict=True
            )
        )
        crossing = (Fraction(0),) + tuple(
            (current - prior) / 2
            for prior, current in zip(order, order[1:])
        )
        balance = tuple(
            (
                Fraction(0)
                if left + right == 0
                else (left - right) / (left + right)
            )
            for left, right in zip(
                left_pressure, right_pressure, strict=True
            )
        )
        projective_motion = (Fraction(0),) + tuple(
            (
                left_now * right_prior
                - right_now * left_prior
            )
            for left_prior, right_prior, left_now, right_now in zip(
                left_pressure[:-1],
                right_pressure[:-1],
                left_pressure[1:],
                right_pressure[1:],
                strict=True,
            )
        )
        left_phase = tuple(
            Fraction.from_float(float(value))
            for value in capture.cumulative_phase_turns[:, left_index]
        )
        right_phase = tuple(
            Fraction.from_float(float(value))
            for value in capture.cumulative_phase_turns[:, right_index]
        )
        phase_cycle = tuple(
            2 * _wrap_cycle(left - right)
            for left, right in zip(left_phase, right_phase, strict=True)
        )
        left_advance = tuple(
            Fraction.from_float(float(value))
            for value in capture.phase_advance_turns[:, left_index]
        )
        right_advance = tuple(
            Fraction.from_float(float(value))
            for value in capture.phase_advance_turns[:, right_index]
        )
        phase_advance = tuple(
            (left - right)
            / (2 * Fraction.from_float(
                provider.PHASE_ADVANCE_NYQUIST_TURNS_PER_HOP
            ))
            for left, right in zip(
                left_advance, right_advance, strict=True
            )
        )
        values_by_relation = {
            "envelope_order": order,
            "envelope_crossing": crossing,
            "projective_amplitude_balance": balance,
            "projective_amplitude_motion": projective_motion,
            "carrier_phase_cycle_relation": phase_cycle,
            "carrier_phase_advance_relation": phase_advance,
        }
        if tuple(values_by_relation) != RELATION_NAMES:
            raise RuntimeError("cross-band relation order changed")
        for relation_name, values in values_by_relation.items():
            if (
                len(values) != capture.observation_count
                or any(not -1 <= value <= 1 for value in values)
            ):
                raise RuntimeError(
                    "cross-band relation left its exact bounded field"
                )
            result[(
                "receptor-relation",
                pair_id,
                "adjacent-erb",
                relation_name,
            )] = values
    if len(result) != RELATION_PORT_COUNT:
        raise RuntimeError("cross-band relation topology is incomplete")
    return result


def _relation_native_inputs(
    capture: ReceptorCapture,
    trajectory: Mapping[LaneKey, Sequence[Fraction]],
    *,
    source_anchor: Fraction,
) -> tuple[NativeSensorySubstreamInput, ...]:
    source_times = tuple(
        source_anchor + (index + 1) * HOP_DURATION
        for index in range(capture.observation_count)
    )
    zero_phase = (Fraction(0),) * capture.observation_count
    mounted = []
    for pair_index in range(PAIR_COUNT):
        right_index = pair_index + 1
        pair_id = f"erb_{pair_index:02d}_to_erb_{right_index:02d}"
        left_centre = Fraction.from_float(
            capture.centres_hz[pair_index]
        )
        right_centre = Fraction.from_float(
            capture.centres_hz[right_index]
        )
        spacing = right_centre - left_centre
        for relation_index, relation_name in enumerate(RELATION_NAMES):
            lane = (
                "receptor-relation",
                pair_id,
                "adjacent-erb",
                relation_name,
            )
            values = tuple(trajectory[lane])
            phase_turns = (
                tuple(
                    Fraction.from_float(float(left))
                    - Fraction.from_float(float(right))
                    for left, right in zip(
                        capture.cumulative_phase_turns[:, pair_index],
                        capture.cumulative_phase_turns[:, right_index],
                        strict=True,
                    )
                )
                if relation_name.startswith("carrier_phase")
                else zero_phase
            )
            mounted.append(NativeSensorySubstreamInput(
                sense=PhysicalSense.SOUND,
                sensor_id="adjacent-erb-relation-field",
                substream_id=f"{pair_id}_{relation_name}",
                topology_index=(
                    pair_index * len(RELATION_NAMES) + relation_index
                ),
                coordinates=(
                    NativeAxisCoordinate("left-channel", f"erb_{pair_index:02d}"),
                    NativeAxisCoordinate("right-channel", f"erb_{right_index:02d}"),
                    NativeAxisCoordinate(
                        "left-centre-hz", _fraction_text(left_centre)
                    ),
                    NativeAxisCoordinate(
                        "right-centre-hz", _fraction_text(right_centre)
                    ),
                    NativeAxisCoordinate(
                        "centre-spacing-hz", _fraction_text(spacing)
                    ),
                    NativeAxisCoordinate(
                        "left-erb-width-hz",
                        _fraction_text(Fraction.from_float(
                            capture.widths_hz[pair_index]
                        )),
                    ),
                    NativeAxisCoordinate(
                        "right-erb-width-hz",
                        _fraction_text(Fraction.from_float(
                            capture.widths_hz[right_index]
                        )),
                    ),
                    NativeAxisCoordinate("relation", relation_name),
                ),
                physical_quantity=relation_name,
                physical_unit="exact-adjacent-erb-relation",
                source_times=source_times,
                normalized_signal=tuple(float(value) for value in values),
                phase_turns=phase_turns,
            ))
    if (
        len(mounted) != RELATION_PORT_COUNT
        or tuple(value.topology_index for value in mounted)
        != tuple(range(RELATION_PORT_COUNT))
    ):
        raise RuntimeError("cross-band native relation topology changed")
    return tuple(mounted)


def _l4_relation_trajectory(
    capture: ReceptorCapture,
    receptor: Mapping[LaneKey, Sequence[Fraction]],
    *,
    assembly_id: str,
    source_anchor: Fraction,
) -> tuple[Trajectory, float]:
    inputs = _relation_native_inputs(
        capture,
        receptor,
        source_anchor=source_anchor,
    )
    started = __import__("time").perf_counter()
    results = _build_partition(tuple(
        (index, value, assembly_id)
        for index, value in enumerate(inputs)
    ))
    elapsed = __import__("time").perf_counter() - started
    result: Trajectory = {}
    for native, built in zip(inputs, results, strict=True):
        basin = built[5]
        intervals = built[8]
        pair_id, relation_name = next(
            (
                (
                    f"erb_{pair_index:02d}_to_erb_{pair_index + 1:02d}",
                    candidate,
                )
                for pair_index in range(PAIR_COUNT)
                for candidate in RELATION_NAMES
                if native.substream_id
                == (
                    f"erb_{pair_index:02d}_to_erb_{pair_index + 1:02d}_"
                    f"{candidate}"
                )
            ),
            (None, None),
        )
        if pair_id is None or relation_name is None:
            raise RuntimeError("cross-band L4 port identity changed")
        for field_name in DSF_FIELD_ORDER:
            expanded = []
            for field_tuple, (start, end) in zip(
                basin.exact_dsf_field_tuples,
                intervals,
                strict=True,
            ):
                expanded.extend(
                    [getattr(field_tuple, field_name)] * (end - start + 1)
                )
            if len(expanded) != capture.observation_count:
                raise RuntimeError("cross-band L4 lost causal observations")
            result[(
                "l4-relation",
                pair_id,
                relation_name,
                field_name,
            )] = tuple(expanded)
    expected = RELATION_PORT_COUNT * len(DSF_FIELD_ORDER)
    if len(result) != expected:
        raise RuntimeError("cross-band L4 lost explicit DSF fields")
    return result, elapsed


def _trajectory_root(trajectory: Mapping[LaneKey, Sequence[Fraction]]) -> str:
    return _digest({
        "|".join(lane): [_fraction_text(value) for value in values]
        for lane, values in sorted(trajectory.items())
    })


def _grow(
    memory: dict[str, dict[LaneKey, LaneRunBasin]],
    command: str,
    trajectory: Mapping[LaneKey, Sequence[Fraction]],
) -> None:
    command_memory = memory.setdefault(command, {})
    durations = (HOP_DURATION,) * len(next(iter(trajectory.values())))
    for lane, values in trajectory.items():
        basin = command_memory.setdefault(lane, LaneRunBasin.create())
        basin.grow(_runs(values, durations))


def _settle(
    memory: Mapping[str, Mapping[LaneKey, LaneRunBasin]],
    trajectory: Mapping[LaneKey, Sequence[Fraction]],
) -> dict[str, object]:
    durations = (HOP_DURATION,) * len(next(iter(trajectory.values())))
    relations = {}
    for command, lanes in sorted(memory.items()):
        matching = sum(
            basin.contains(_runs(trajectory[lane], durations))
            for lane, basin in lanes.items()
        )
        direction = canonical_l6_direction(
            dimensions=len(lanes),
            matching_non_null=matching,
            matching_quiescent=0,
        )
        relations[command] = {
            "dimensions": direction.dimensions,
            "effective_dimensions": direction.effective_dimensions,
            "knee": direction.knee,
            "locked": direction.locked,
            "matching_complete_lanes": matching,
        }
    locked = tuple(
        command
        for command, relation in relations.items()
        if relation["locked"]
    )
    return {
        "relations": relations,
        "state": (
            "resolved"
            if len(locked) == 1
            else "unknown"
            if not locked
            else "ambiguous"
        ),
        "thing_commands": list(locked),
    }


def _strictly_dominant(
    settlement: Mapping[str, object],
    expected: str,
) -> bool:
    relations = settlement["relations"]
    correct = relations[expected]["matching_complete_lanes"]
    return correct > max(
        relation["matching_complete_lanes"]
        for command, relation in relations.items()
        if command != expected
    )


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
        ordered = references + held_out + (tone,)
        signals = {
            item.item_id: _pcm_from_wav(archive.read(item.archive_member))
            for item in references + held_out
        }
        signals[tone.item_id] = (
            np.frombuffer(_tone_pcm(), dtype="<i2").astype(np.float64)
            / 32_768.0
        )
    if len(references) != len(TEST_COMMANDS) * REFERENCE_COUNT:
        raise RuntimeError("cross-band reference split changed")

    receptor_by_id: dict[str, Trajectory] = {}
    l4_by_id: dict[str, Trajectory] = {}
    combined_by_id: dict[str, Trajectory] = {}
    roots = []
    transduction_seconds = 0.0
    l0_l4_seconds = 0.0
    for item in ordered:
        capture = _transduce(signals[item.item_id], CHANNEL_COUNT)
        receptor = _relation_trajectory(capture)
        l4, elapsed = _l4_relation_trajectory(
            capture,
            receptor,
            assembly_id=f"cross-band-relation-{item.item_id}",
            source_anchor=Fraction(item.ordinal * 2),
        )
        combined = dict(receptor)
        combined.update(l4)
        receptor_by_id[item.item_id] = receptor
        l4_by_id[item.item_id] = l4
        combined_by_id[item.item_id] = combined
        roots.append({
            "item_id": item.item_id,
            "receptor_relation_root_sha256": _trajectory_root(receptor),
            "l4_relation_root_sha256": _trajectory_root(l4),
            "complete_relation_root_sha256": _trajectory_root(combined),
        })
        transduction_seconds += capture.transduction_seconds
        l0_l4_seconds += elapsed

    memories = {
        "receptor": {},
        "l4": {},
        "complete": {},
    }
    sources = {
        "receptor": receptor_by_id,
        "l4": l4_by_id,
        "complete": combined_by_id,
    }
    for item in references:
        for boundary_name, memory in memories.items():
            _grow(
                memory,
                item.oracle_command,
                sources[boundary_name][item.item_id],
            )
    held_records = []
    for item in held_out:
        settlements = {
            boundary_name: _settle(
                memory,
                sources[boundary_name][item.item_id],
            )
            for boundary_name, memory in memories.items()
        }
        complete = settlements["complete"]
        held_records.append({
            "item_id": item.item_id,
            "oracle_used_only_after_physical_settlement": item.oracle_command,
            "settlements": settlements,
            "complete_correct_strictly_dominant": _strictly_dominant(
                complete, item.oracle_command
            ),
            "complete_uniquely_l6_resolved": (
                complete["state"] == "resolved"
                and complete["thing_commands"] == [item.oracle_command]
            ),
        })
    tone_settlements = {
        boundary_name: _settle(
            memory,
            sources[boundary_name][tone.item_id],
        )
        for boundary_name, memory in memories.items()
    }
    decisive_pass = (
        all(
            value["complete_correct_strictly_dominant"]
            and value["complete_uniquely_l6_resolved"]
            for value in held_records
        )
        and tone_settlements["complete"]["state"] == "unknown"
    )
    audio_seconds = sum(
        len(value) / provider.REQUIRED_SAMPLE_RATE_HZ
        for value in signals.values()
    )
    payload = {
        "adjacent_pair_count": PAIR_COUNT,
        "archive_sha256": archive_sha256,
        "canonical_code_modified": False,
        "complete_relation_lane_count": (
            RELATION_PORT_COUNT * (1 + len(DSF_FIELD_ORDER))
        ),
        "decision_rule_declared_before_results": (
            "each held-out grounded command must have strictly more exact "
            "complete relation lanes than every competitor and be the only "
            "canonical-L6 lock; the unrelated tone must have no L6 lock"
        ),
        "decisive_pass": decisive_pass,
        "full_explicit_dsf_field_order": list(DSF_FIELD_ORDER),
        "held_out": held_records,
        "l4_relation_lane_count": (
            RELATION_PORT_COUNT * len(DSF_FIELD_ORDER)
        ),
        "no_formant_ridge_was_selected": True,
        "receptor_relation_lane_count": RELATION_PORT_COUNT,
        "relation_names": list(RELATION_NAMES),
        "resource_cost": {
            "audio_seconds_processed": audio_seconds,
            "fixed_relation_ports": RELATION_PORT_COUNT,
            "l0_l4_elapsed_seconds": l0_l4_seconds,
            "l0_l4_realtime_ratio": l0_l4_seconds / audio_seconds,
            "transduction_elapsed_seconds": transduction_seconds,
            "transduction_realtime_ratio": (
                transduction_seconds / audio_seconds
            ),
        },
        "schema": SCHEMA,
        "source_disjoint_held_out_speakers": len(held_out),
        "source_disjoint_reference_speakers": len(references),
        "tone": tone_settlements,
        "trajectory_authority_root_sha256": _digest(roots),
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
