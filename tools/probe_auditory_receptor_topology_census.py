"""Isolated auditory receptor-topology information census.

This probe does not recognize words and does not alter the canonical auditory
provider or frozen L0--L4 kernel.  It walks the same fourth-order ERB
gammatone physics at 16, 32, 64, and 128 channels, then passes every pressure
and direct carrier-phase-advance stream through the unchanged exact L0--L4
executor.

The held-out audit reports exact per-lane run-envelope containment counts.
Those counts are diagnostics of information survival, never a recognition
authority.  The predeclared reversal condition is exact: for all three
source-disjoint held-out speakers, the physically grounded command basin must
contain strictly more complete L4 lanes than every wrong basin.  No threshold,
distance, fitted value, transcript identity in the relation, ML, or flattened
DSF vector is used.
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import math
import time
import zipfile
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np

from dsf_ai_service.glew_runtime.exact_field_executor import _build_partition
from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    NativeSensorySubstreamInput,
    PAIRED_SOURCE_RELEVANCE_RULE,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    NativeAxisCoordinate,
    PhysicalSense,
)
from dsf_ai_service.substrate.auditory_pressure_kernel_input import (
    AUDITORY_PRESSURE_KERNEL_INPUT_MAP,
)
from dsf_ai_service.substrate.senses import auditory_full_field_provider as provider
from tools.probe_auditory_full_field_separability_census import (
    ARCHIVE_SHA256,
    _pcm_from_wav,
    _select_corpus,
)
from tools.probe_contextual_thing_mosaic_settling import (
    REFERENCE_COUNT,
    TEST_COMMANDS,
)
from tools.probe_w1_causal_run_envelope_walkup import (
    LaneRunBasin,
    _runs,
)


SCHEMA = "guala.audit.auditory_receptor_topology_census.v1"
CHANNEL_COUNTS = (16, 32, 64, 128)
RECEPTOR_FIELDS = (
    "pressure_envelope",
    "pressure_relevance",
    "cumulative_phase",
    "phase_advance",
)
HOP_DURATION = Fraction(
    provider.OBSERVATION_HOP_SAMPLES,
    provider.REQUIRED_SAMPLE_RATE_HZ,
)

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


@dataclass(frozen=True, slots=True)
class ReceptorCapture:
    channel_count: int
    centres_hz: tuple[float, ...]
    widths_hz: tuple[float, ...]
    envelopes: np.ndarray
    cumulative_phase_turns: np.ndarray
    phase_advance_turns: np.ndarray
    transduction_seconds: float
    audio_seconds: Fraction

    @property
    def observation_count(self) -> int:
        return int(self.envelopes.shape[0])


def _coefficients(
    channel_count: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    if channel_count not in CHANNEL_COUNTS:
        raise ValueError("channel topology is outside the declared census")
    lower = provider._erb_rate(provider.LOWEST_CENTRE_FREQUENCY_HZ)
    upper = provider._erb_rate(provider.HIGHEST_CENTRE_FREQUENCY_HZ)
    rates = np.linspace(lower, upper, channel_count)
    centres = np.asarray(
        [provider._frequency_from_erb_rate(float(value)) for value in rates],
        dtype=np.float64,
    )
    widths = np.asarray(
        [provider._erb_width_hz(float(value)) for value in centres],
        dtype=np.float64,
    )
    radius = np.exp(
        -2.0
        * math.pi
        * 1.019
        * widths
        / provider.REQUIRED_SAMPLE_RATE_HZ
    )
    poles = radius * np.exp(
        2.0j
        * math.pi
        * centres
        / provider.REQUIRED_SAMPLE_RATE_HZ
    )
    return centres, widths, poles, 1.0 - radius


def _transduce(signal: np.ndarray, channel_count: int) -> ReceptorCapture:
    values = np.asarray(signal, dtype=np.float64)
    if (
        values.ndim != 1
        or len(values) < provider.OBSERVATION_HOP_SAMPLES
        or len(values) % provider.OBSERVATION_HOP_SAMPLES
        or not np.all(np.isfinite(values))
        or np.any(values < -1.0)
        or np.any(values > 1.0)
    ):
        raise ValueError("receptor census input left canonical PCM custody")
    centres, widths, poles, injection = _coefficients(channel_count)
    state = np.zeros(
        (provider.COCHLEAR_ORDER, channel_count),
        dtype=np.complex128,
    )
    previous = np.zeros(channel_count, dtype=np.complex128)
    phase_turns = np.zeros(channel_count, dtype=np.float64)
    hop_phase_turns = np.zeros(channel_count, dtype=np.float64)
    block_energy = np.zeros(channel_count, dtype=np.float64)
    observation_count = len(values) // provider.OBSERVATION_HOP_SAMPLES
    envelopes = np.empty((observation_count, channel_count), dtype=np.float64)
    phases = np.empty_like(envelopes)
    advances = np.empty_like(envelopes)
    observation_index = 0
    started = time.perf_counter()
    for source_index, sample in enumerate(values):
        stage_input = np.full(channel_count, float(sample), dtype=np.complex128)
        for order_index in range(provider.COCHLEAR_ORDER):
            state[order_index] = (
                poles * state[order_index] + injection * stage_input
            )
            stage_input = state[order_index]
        output = state[-1]
        active = (np.abs(output) > 0.0) & (np.abs(previous) > 0.0)
        if np.any(active):
            phase_delta = np.angle(
                output[active] * np.conjugate(previous[active])
            ) / (2.0 * math.pi)
            phase_turns[active] += phase_delta
            hop_phase_turns[active] += phase_delta
        first_active = (np.abs(output) > 0.0) & (np.abs(previous) == 0.0)
        if np.any(first_active):
            phase_turns[first_active] = (
                np.angle(output[first_active]) / (2.0 * math.pi)
            )
        previous = output.copy()
        block_energy += np.abs(output) ** 2
        if (source_index + 1) % provider.OBSERVATION_HOP_SAMPLES == 0:
            magnitude = np.sqrt(
                block_energy / provider.OBSERVATION_HOP_SAMPLES
            )
            if np.any(magnitude > 1.0 + 1e-12):
                raise RuntimeError("receptor pressure exceeded analytic bound")
            envelopes[observation_index] = np.minimum(magnitude, 1.0)
            phases[observation_index] = phase_turns
            advances[observation_index] = hop_phase_turns
            block_energy.fill(0.0)
            hop_phase_turns.fill(0.0)
            observation_index += 1
    advances[0].fill(0.0)
    return ReceptorCapture(
        channel_count=channel_count,
        centres_hz=tuple(float(value) for value in centres),
        widths_hz=tuple(float(value) for value in widths),
        envelopes=envelopes,
        cumulative_phase_turns=phases,
        phase_advance_turns=advances,
        transduction_seconds=time.perf_counter() - started,
        audio_seconds=Fraction(
            len(values),
            provider.REQUIRED_SAMPLE_RATE_HZ,
        ),
    )


def _native_inputs(
    capture: ReceptorCapture,
    *,
    source_anchor: Fraction,
) -> tuple[NativeSensorySubstreamInput, ...]:
    times = tuple(
        source_anchor + (index + 1) * HOP_DURATION
        for index in range(capture.observation_count)
    )
    zero_phase = (Fraction(0),) * capture.observation_count
    mounted = []
    for channel_index, (centre, width) in enumerate(zip(
        capture.centres_hz,
        capture.widths_hz,
        strict=True,
    )):
        channel_id = f"erb_{channel_index:03d}"
        coordinates = (
            NativeAxisCoordinate("cochlear-channel", channel_id),
            NativeAxisCoordinate("centre-hz", str(centre)),
            NativeAxisCoordinate("erb-width-hz", str(width)),
            NativeAxisCoordinate(
                "gammatone-order", str(provider.COCHLEAR_ORDER)
            ),
        )
        pressure = tuple(
            float(value) for value in capture.envelopes[:, channel_index]
        )
        relevance = tuple(
            Fraction.from_float(value) ** 2 for value in pressure
        )
        pressure_id = f"{channel_id}_pressure"
        mounted.append(NativeSensorySubstreamInput(
            sense=PhysicalSense.SOUND,
            sensor_id="receptor-topology-census",
            substream_id=pressure_id,
            topology_index=channel_index * 2,
            coordinates=coordinates + (
                NativeAxisCoordinate(
                    "kernel-component", "pressure-envelope"
                ),
            ),
            physical_quantity="cochlear-pressure-envelope",
            physical_unit="full-scale-pressure",
            source_times=times,
            normalized_signal=pressure,
            phase_turns=zero_phase,
            source_relevance=relevance,
            source_relevance_rule=PAIRED_SOURCE_RELEVANCE_RULE,
            source_relevance_origin_substream_id=pressure_id,
            kernel_input_map=AUDITORY_PRESSURE_KERNEL_INPUT_MAP,
        ))
        mounted.append(NativeSensorySubstreamInput(
            sense=PhysicalSense.SOUND,
            sensor_id="receptor-topology-census",
            substream_id=f"{channel_id}_phase_advance",
            topology_index=channel_index * 2 + 1,
            coordinates=coordinates + (
                NativeAxisCoordinate(
                    "kernel-component", "carrier-phase-advance"
                ),
            ),
            physical_quantity="cochlear-carrier-phase-advance",
            physical_unit="nyquist-fraction-per-observation-hop",
            source_times=times,
            normalized_signal=tuple(
                float(value)
                / provider.PHASE_ADVANCE_NYQUIST_TURNS_PER_HOP
                for value in capture.phase_advance_turns[:, channel_index]
            ),
            phase_turns=tuple(
                Fraction.from_float(float(value))
                for value in capture.cumulative_phase_turns[:, channel_index]
            ),
            source_relevance=relevance,
            source_relevance_rule=PAIRED_SOURCE_RELEVANCE_RULE,
            source_relevance_origin_substream_id=pressure_id,
        ))
    return tuple(mounted)


def _receptor_trajectory(capture: ReceptorCapture) -> Trajectory:
    result: Trajectory = {}
    for channel_index in range(capture.channel_count):
        channel_id = f"erb_{channel_index:03d}"
        pressure = tuple(
            Fraction.from_float(float(value))
            for value in capture.envelopes[:, channel_index]
        )
        result[("receptor", channel_id, "physical", "pressure_envelope")] = (
            pressure
        )
        result[("receptor", channel_id, "physical", "pressure_relevance")] = (
            tuple(value * value for value in pressure)
        )
        result[("receptor", channel_id, "physical", "cumulative_phase")] = tuple(
            Fraction.from_float(float(value))
            for value in capture.cumulative_phase_turns[:, channel_index]
        )
        result[("receptor", channel_id, "physical", "phase_advance")] = tuple(
            Fraction.from_float(float(value))
            for value in capture.phase_advance_turns[:, channel_index]
        )
    return result


def _l4_trajectory(
    capture: ReceptorCapture,
    *,
    assembly_id: str,
    source_anchor: Fraction,
) -> tuple[Trajectory, float]:
    inputs = _native_inputs(capture, source_anchor=source_anchor)
    jobs = tuple(
        (index, native, assembly_id)
        for index, native in enumerate(inputs)
    )
    started = time.perf_counter()
    results = _build_partition(jobs)
    elapsed = time.perf_counter() - started
    if tuple(value[0] for value in results) != tuple(range(len(inputs))):
        raise RuntimeError("isolated L0-L4 executor reordered auditory ports")
    trajectory: Trajectory = {}
    for native, result in zip(inputs, results, strict=True):
        basin = result[5]
        intervals = result[8]
        component = (
            "pressure"
            if native.substream_id.endswith("_pressure")
            else "phase"
        )
        channel_id = native.substream_id.split("_pressure")[0].split(
            "_phase_advance"
        )[0]
        tuples = basin.exact_dsf_field_tuples
        if len(tuples) != len(intervals):
            raise RuntimeError("L0-L4 support intervals changed cardinality")
        for field_name in DSF_FIELD_ORDER:
            expanded = []
            for field_tuple, (start, end) in zip(
                tuples, intervals, strict=True
            ):
                expanded.extend(
                    [getattr(field_tuple, field_name)] * (end - start + 1)
                )
            if len(expanded) != capture.observation_count:
                raise RuntimeError("L4 trajectory lost source observations")
            trajectory[(
                "l4",
                channel_id,
                component,
                field_name,
            )] = tuple(expanded)
    expected = capture.channel_count * 2 * len(DSF_FIELD_ORDER)
    if len(trajectory) != expected:
        raise RuntimeError("L4 trajectory lost explicit field topology")
    return trajectory, elapsed


def _trajectory_root(trajectory: Mapping[LaneKey, Sequence[Fraction]]) -> str:
    return _digest({
        "|".join(lane): [_fraction_text(value) for value in values]
        for lane, values in sorted(trajectory.items())
    })


def _rank_transition_root(capture: ReceptorCapture) -> tuple[str, int]:
    order_types = tuple(
        tuple(
            sorted(
                range(capture.channel_count),
                key=lambda index: (
                    float(capture.envelopes[frame_index, index]),
                    index,
                ),
            )
        )
        for frame_index in range(capture.observation_count)
    )
    collapsed = tuple(
        value
        for index, value in enumerate(order_types)
        if index == 0 or value != order_types[index - 1]
    )
    return _digest({"cross_band_order_trajectory": collapsed}), len(collapsed)


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


def _containment_counts(
    memory: Mapping[str, Mapping[LaneKey, LaneRunBasin]],
    trajectory: Mapping[LaneKey, Sequence[Fraction]],
) -> dict[str, int]:
    durations = (HOP_DURATION,) * len(next(iter(trajectory.values())))
    return {
        command: sum(
            basin.contains(_runs(trajectory[lane], durations))
            for lane, basin in lanes.items()
        )
        for command, lanes in sorted(memory.items())
    }


def _absence_audit() -> dict[str, object]:
    source = inspect.getsource(provider)
    forbidden_present = {
        name: name in source.lower()
        for name in (
            "half_wave",
            "inner_hair",
            "adaptation",
            "compression_exponent",
            "cross_band",
            "formant",
        )
    }
    return {
        "canonical_provider_has_deterministic_inner_hair_cell_adaptation": False,
        "canonical_provider_has_cross_band_formant_trajectory_operator": False,
        "source_identifier_presence": forbidden_present,
        "physical_reason": (
            "each ERB channel is advanced independently and only 10 ms complex "
            "RMS, cumulative phase, and direct phase advance leave the provider"
        ),
    }


def _state_cost(channel_count: int, observations: int) -> dict[str, int]:
    persistent_filter_state_bytes = channel_count * (
        provider.COCHLEAR_ORDER * 16
        + 16
        + 8
        + 8
        + 8
    )
    coefficient_bytes = channel_count * (16 + 8)
    return {
        "cochlear_channels": channel_count,
        "kernel_component_ports": channel_count * 2,
        "explicit_l4_lanes": channel_count * 2 * len(DSF_FIELD_ORDER),
        "physical_receptor_lanes": channel_count * len(RECEPTOR_FIELDS),
        "persistent_filter_state_bytes": persistent_filter_state_bytes,
        "coefficient_bytes": coefficient_bytes,
        "one_capture_output_binary64_bytes": (
            observations * channel_count * 3 * 8
        ),
    }


def _census_topology(
    channel_count: int,
    ordered_items: Sequence[object],
    signals: Mapping[str, np.ndarray],
) -> dict[str, object]:
    receptor_by_id: dict[str, Trajectory] = {}
    l4_by_id: dict[str, Trajectory] = {}
    roots = []
    transduction_seconds = 0.0
    l0_l4_seconds = 0.0
    audio_seconds = Fraction(0)
    rank_transitions = []
    observations = 0
    for item in ordered_items:
        capture = _transduce(signals[item.item_id], channel_count)
        observations = capture.observation_count
        receptor = _receptor_trajectory(capture)
        l4, elapsed = _l4_trajectory(
            capture,
            assembly_id=(
                f"receptor-topology-{channel_count}-{item.item_id}"
            ),
            source_anchor=Fraction(item.ordinal * 2),
        )
        receptor_by_id[item.item_id] = receptor
        l4_by_id[item.item_id] = l4
        receptor_root = _trajectory_root(receptor)
        l4_root = _trajectory_root(l4)
        rank_root, transition_count = _rank_transition_root(capture)
        roots.append({
            "item_id": item.item_id,
            "receptor_root_sha256": receptor_root,
            "l4_full_field_root_sha256": l4_root,
            "cross_band_order_trajectory_root_sha256": rank_root,
        })
        rank_transitions.append(transition_count)
        transduction_seconds += capture.transduction_seconds
        l0_l4_seconds += elapsed
        audio_seconds += capture.audio_seconds

    references = tuple(
        item for item in ordered_items if item.split == "reference"
    )
    held_out = tuple(
        item for item in ordered_items if item.split == "held_out"
    )
    receptor_memory: dict[str, dict[LaneKey, LaneRunBasin]] = {}
    l4_memory: dict[str, dict[LaneKey, LaneRunBasin]] = {}
    for item in references:
        _grow(
            receptor_memory,
            item.oracle_command,
            receptor_by_id[item.item_id],
        )
        _grow(l4_memory, item.oracle_command, l4_by_id[item.item_id])
    held_records = []
    for item in held_out:
        receptor_counts = _containment_counts(
            receptor_memory, receptor_by_id[item.item_id]
        )
        l4_counts = _containment_counts(
            l4_memory, l4_by_id[item.item_id]
        )
        held_records.append({
            "item_id": item.item_id,
            "oracle_used_only_after_physical_settlement": item.oracle_command,
            "receptor_complete_lane_containment_counts": receptor_counts,
            "l4_complete_lane_containment_counts": l4_counts,
            "receptor_correct_strictly_dominant": (
                receptor_counts[item.oracle_command]
                > max(
                    value
                    for command, value in receptor_counts.items()
                    if command != item.oracle_command
                )
            ),
            "l4_correct_strictly_dominant": (
                l4_counts[item.oracle_command]
                > max(
                    value
                    for command, value in l4_counts.items()
                    if command != item.oracle_command
                )
            ),
        })
    l4_reversal = all(
        value["l4_correct_strictly_dominant"] for value in held_records
    )
    audio_float = float(audio_seconds)
    return {
        "channel_count": channel_count,
        "cross_band_order_trajectory_distinct_count": len({
            value["cross_band_order_trajectory_root_sha256"]
            for value in roots
        }),
        "cross_band_order_transition_count_min": min(rank_transitions),
        "cross_band_order_transition_count_max": max(rank_transitions),
        "full_l4_trajectory_distinct_count": len({
            value["l4_full_field_root_sha256"] for value in roots
        }),
        "held_out": held_records,
        "l4_wrong_basin_dominance_reversed_for_all_held_out": l4_reversal,
        "receptor_trajectory_distinct_count": len({
            value["receptor_root_sha256"] for value in roots
        }),
        "resource_cost": _state_cost(channel_count, observations) | {
            "audio_seconds_processed": audio_float,
            "l0_l4_elapsed_seconds": l0_l4_seconds,
            "l0_l4_realtime_ratio": l0_l4_seconds / audio_float,
            "transduction_elapsed_seconds": transduction_seconds,
            "transduction_realtime_ratio": (
                transduction_seconds / audio_float
            ),
        },
        "trajectory_authority_root_sha256": _digest(roots),
    }


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
        ordered = references + held_out
        signals = {
            item.item_id: _pcm_from_wav(archive.read(item.archive_member))
            for item in ordered
        }
    if len(references) != len(TEST_COMMANDS) * REFERENCE_COUNT:
        raise RuntimeError("receptor census reference split changed")
    topologies = []
    first_reversal = None
    for channel_count in CHANNEL_COUNTS:
        record = _census_topology(channel_count, ordered, signals)
        topologies.append(record)
        if record["l4_wrong_basin_dominance_reversed_for_all_held_out"]:
            first_reversal = channel_count
            break
    payload = {
        "architecture_conflict": (
            "canonical hearing exposes 16 independent ERB channels and no "
            "inner-hair-cell adaptation or cross-band relation operator"
        ),
        "archive_sha256": archive_sha256,
        "canonical_code_modified": False,
        "channel_counts_declared": list(CHANNEL_COUNTS),
        "channel_counts_executed": [
            value["channel_count"] for value in topologies
        ],
        "first_topology_reversing_wrong_basin_dominance": first_reversal,
        "full_explicit_dsf_field_order": list(DSF_FIELD_ORDER),
        "operator_absence_audit": _absence_audit(),
        "reversal_rule_declared_before_results": (
            "all three held-out source-disjoint speakers must have strictly "
            "more exact complete L4 run-envelope lanes in the physically "
            "grounded basin than in every wrong basin"
        ),
        "schema": SCHEMA,
        "source_disjoint_reference_speakers": len(references),
        "source_disjoint_held_out_speakers": len(held_out),
        "topologies": topologies,
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
