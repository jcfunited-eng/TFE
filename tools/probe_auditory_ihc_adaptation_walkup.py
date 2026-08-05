"""Isolated deterministic inner-hair-cell adaptation walk-up.

The canonical fourth-order ERB gammatone recurrence is preserved.  This probe
observes the real basilar-membrane displacement at every native sample,
half-wave rectifies it into an inner-hair-cell receptor potential, and retains
parameter-free causal onset and recovery release.  No fitted time constant,
threshold, compression exponent, peak selection, score, interpolation, ML,
or transcript identity enters the physical transform.

Every canonical channel contributes the same complete IHC field.  Each field
then passes through unchanged exact L0--L4 before source-disjoint grounded
THING basins are audited.  No production code is modified.
"""

from __future__ import annotations

import argparse
import hashlib
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
from tools.probe_auditory_cross_band_relation_walkup import (
    _grow,
    _settle,
    _strictly_dominant,
    _trajectory_root,
)
from tools.probe_auditory_full_field_separability_census import (
    ARCHIVE_SHA256,
    _pcm_from_wav,
    _select_corpus,
)
from tools.probe_auditory_receptor_topology_census import (
    HOP_DURATION,
    _coefficients,
)
from tools.probe_contextual_thing_mosaic_settling import (
    REFERENCE_COUNT,
    TEST_COMMANDS,
    _tone_item,
    _tone_pcm,
)


SCHEMA = "guala.audit.auditory_ihc_adaptation_walkup.v1"
IHC_FIELDS = (
    "receptor_potential_mean",
    "receptor_potential_rms",
    "onset_release_mean",
    "recovery_release_mean",
    "release_balance",
)
CHANNEL_COUNT = provider.COCHLEAR_CHANNEL_COUNT
IHC_PORT_COUNT = CHANNEL_COUNT * len(IHC_FIELDS)

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
class IHCFieldCapture:
    centres_hz: tuple[float, ...]
    widths_hz: tuple[float, ...]
    receptor_potential_mean: np.ndarray
    receptor_potential_rms: np.ndarray
    onset_release_mean: np.ndarray
    recovery_release_mean: np.ndarray
    release_balance: np.ndarray
    transduction_seconds: float
    audio_seconds: Fraction

    @property
    def observation_count(self) -> int:
        return int(self.receptor_potential_mean.shape[0])


def _ihc_transduce(signal: np.ndarray) -> IHCFieldCapture:
    values = np.asarray(signal, dtype=np.float64)
    if (
        values.ndim != 1
        or len(values) < provider.OBSERVATION_HOP_SAMPLES
        or len(values) % provider.OBSERVATION_HOP_SAMPLES
        or not np.all(np.isfinite(values))
        or np.any(values < -1.0)
        or np.any(values > 1.0)
    ):
        raise ValueError("IHC probe input left canonical PCM custody")
    centres, widths, poles, injection = _coefficients(CHANNEL_COUNT)
    state = np.zeros(
        (provider.COCHLEAR_ORDER, CHANNEL_COUNT),
        dtype=np.complex128,
    )
    prior_potential = np.zeros(CHANNEL_COUNT, dtype=np.float64)
    potential_sum = np.zeros(CHANNEL_COUNT, dtype=np.float64)
    potential_energy = np.zeros(CHANNEL_COUNT, dtype=np.float64)
    onset_sum = np.zeros(CHANNEL_COUNT, dtype=np.float64)
    recovery_sum = np.zeros(CHANNEL_COUNT, dtype=np.float64)
    observation_count = len(values) // provider.OBSERVATION_HOP_SAMPLES
    potential_mean = np.empty(
        (observation_count, CHANNEL_COUNT), dtype=np.float64
    )
    potential_rms = np.empty_like(potential_mean)
    onset_mean = np.empty_like(potential_mean)
    recovery_mean = np.empty_like(potential_mean)
    release_balance = np.empty_like(potential_mean)
    observation_index = 0
    started = time.perf_counter()
    for source_index, sample in enumerate(values):
        stage_input = np.full(
            CHANNEL_COUNT, float(sample), dtype=np.complex128
        )
        for order_index in range(provider.COCHLEAR_ORDER):
            state[order_index] = (
                poles * state[order_index] + injection * stage_input
            )
            stage_input = state[order_index]
        potential = np.maximum(state[-1].real, 0.0)
        delta = potential - prior_potential
        onset = np.maximum(delta, 0.0)
        recovery = np.maximum(-delta, 0.0)
        prior_potential = potential.copy()
        potential_sum += potential
        potential_energy += potential * potential
        onset_sum += onset
        recovery_sum += recovery
        if (source_index + 1) % provider.OBSERVATION_HOP_SAMPLES == 0:
            hop = provider.OBSERVATION_HOP_SAMPLES
            observed_mean = potential_sum / hop
            observed_rms = np.sqrt(potential_energy / hop)
            observed_onset = onset_sum / hop
            observed_recovery = recovery_sum / hop
            total_release = observed_onset + observed_recovery
            observed_balance = np.divide(
                observed_onset - observed_recovery,
                total_release,
                out=np.zeros_like(total_release),
                where=total_release != 0.0,
            )
            for observed in (
                observed_mean,
                observed_rms,
                observed_onset,
                observed_recovery,
            ):
                if np.any(observed < 0.0) or np.any(observed > 1.0 + 1e-12):
                    raise RuntimeError("IHC field exceeded analytic bound")
            if np.any(np.abs(observed_balance) > 1.0):
                raise RuntimeError("IHC release balance exceeded unit bound")
            potential_mean[observation_index] = np.minimum(
                observed_mean, 1.0
            )
            potential_rms[observation_index] = np.minimum(
                observed_rms, 1.0
            )
            onset_mean[observation_index] = np.minimum(
                observed_onset, 1.0
            )
            recovery_mean[observation_index] = np.minimum(
                observed_recovery, 1.0
            )
            release_balance[observation_index] = observed_balance
            observation_index += 1
            potential_sum.fill(0.0)
            potential_energy.fill(0.0)
            onset_sum.fill(0.0)
            recovery_sum.fill(0.0)
    return IHCFieldCapture(
        centres_hz=tuple(float(value) for value in centres),
        widths_hz=tuple(float(value) for value in widths),
        receptor_potential_mean=potential_mean,
        receptor_potential_rms=potential_rms,
        onset_release_mean=onset_mean,
        recovery_release_mean=recovery_mean,
        release_balance=release_balance,
        transduction_seconds=time.perf_counter() - started,
        audio_seconds=Fraction(
            len(values), provider.REQUIRED_SAMPLE_RATE_HZ
        ),
    )


def _ihc_trajectory(capture: IHCFieldCapture) -> Trajectory:
    arrays = {
        field_name: getattr(capture, field_name)
        for field_name in IHC_FIELDS
    }
    result: Trajectory = {}
    for channel_index in range(CHANNEL_COUNT):
        channel_id = f"erb_{channel_index:02d}"
        for field_name, values in arrays.items():
            result[(
                "ihc-receptor",
                channel_id,
                "inner-hair-cell",
                field_name,
            )] = tuple(
                Fraction.from_float(float(value))
                for value in values[:, channel_index]
            )
    if len(result) != IHC_PORT_COUNT:
        raise RuntimeError("IHC trajectory lost full channel topology")
    return result


def _ihc_native_inputs(
    capture: IHCFieldCapture,
    trajectory: Mapping[LaneKey, Sequence[Fraction]],
    *,
    source_anchor: Fraction,
) -> tuple[NativeSensorySubstreamInput, ...]:
    source_times = tuple(
        source_anchor + (index + 1) * HOP_DURATION
        for index in range(capture.observation_count)
    )
    phase_turns = (Fraction(0),) * capture.observation_count
    mounted = []
    for channel_index in range(CHANNEL_COUNT):
        channel_id = f"erb_{channel_index:02d}"
        relevance = tuple(
            value * value
            for value in trajectory[(
                "ihc-receptor",
                channel_id,
                "inner-hair-cell",
                "receptor_potential_rms",
            )]
        )
        relevance_origin = f"{channel_id}_receptor_potential_rms"
        for field_index, field_name in enumerate(IHC_FIELDS):
            lane = (
                "ihc-receptor",
                channel_id,
                "inner-hair-cell",
                field_name,
            )
            positive = field_name != "release_balance"
            mounted.append(NativeSensorySubstreamInput(
                sense=PhysicalSense.SOUND,
                sensor_id="deterministic-inner-hair-cell-field",
                substream_id=f"{channel_id}_{field_name}",
                topology_index=(
                    channel_index * len(IHC_FIELDS) + field_index
                ),
                coordinates=(
                    NativeAxisCoordinate("cochlear-channel", channel_id),
                    NativeAxisCoordinate(
                        "centre-hz",
                        _fraction_text(Fraction.from_float(
                            capture.centres_hz[channel_index]
                        )),
                    ),
                    NativeAxisCoordinate(
                        "erb-width-hz",
                        _fraction_text(Fraction.from_float(
                            capture.widths_hz[channel_index]
                        )),
                    ),
                    NativeAxisCoordinate(
                        "gammatone-order", str(provider.COCHLEAR_ORDER)
                    ),
                    NativeAxisCoordinate("ihc-field", field_name),
                    NativeAxisCoordinate(
                        "adaptation-law",
                        "parameter-free-causal-onset-recovery",
                    ),
                ),
                physical_quantity=field_name,
                physical_unit="normalized-ihc-receptor-state",
                source_times=source_times,
                normalized_signal=tuple(
                    float(value) for value in trajectory[lane]
                ),
                phase_turns=phase_turns,
                source_relevance=relevance,
                source_relevance_rule=PAIRED_SOURCE_RELEVANCE_RULE,
                source_relevance_origin_substream_id=relevance_origin,
                kernel_input_map=(
                    AUDITORY_PRESSURE_KERNEL_INPUT_MAP
                    if positive
                    else NativeSensorySubstreamInput.__dataclass_fields__[
                        "kernel_input_map"
                    ].default
                ),
            ))
    if (
        len(mounted) != IHC_PORT_COUNT
        or tuple(value.topology_index for value in mounted)
        != tuple(range(IHC_PORT_COUNT))
    ):
        raise RuntimeError("IHC native topology changed")
    return tuple(mounted)


def _l4_ihc_trajectory(
    capture: IHCFieldCapture,
    receptor: Mapping[LaneKey, Sequence[Fraction]],
    *,
    assembly_id: str,
    source_anchor: Fraction,
) -> tuple[Trajectory, float]:
    inputs = _ihc_native_inputs(
        capture,
        receptor,
        source_anchor=source_anchor,
    )
    started = time.perf_counter()
    built = _build_partition(tuple(
        (index, value, assembly_id)
        for index, value in enumerate(inputs)
    ))
    elapsed = time.perf_counter() - started
    result: Trajectory = {}
    for native, port in zip(inputs, built, strict=True):
        identity = next(
            (
                (f"erb_{channel_index:02d}", field_name)
                for channel_index in range(CHANNEL_COUNT)
                for field_name in IHC_FIELDS
                if native.substream_id
                == f"erb_{channel_index:02d}_{field_name}"
            ),
            None,
        )
        if identity is None:
            raise RuntimeError("IHC L4 port identity changed")
        channel_id, ihc_field = identity
        basin = port[5]
        intervals = port[8]
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
                raise RuntimeError("IHC L4 lost causal observations")
            result[(
                "l4-ihc",
                channel_id,
                ihc_field,
                field_name,
            )] = tuple(expanded)
    expected = IHC_PORT_COUNT * len(DSF_FIELD_ORDER)
    if len(result) != expected:
        raise RuntimeError("IHC L4 lost explicit DSF field topology")
    return result, elapsed


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
        raise RuntimeError("IHC reference split changed")

    receptor_by_id: dict[str, Trajectory] = {}
    l4_by_id: dict[str, Trajectory] = {}
    complete_by_id: dict[str, Trajectory] = {}
    roots = []
    transduction_seconds = 0.0
    l0_l4_seconds = 0.0
    for item in ordered:
        capture = _ihc_transduce(signals[item.item_id])
        receptor = _ihc_trajectory(capture)
        l4, elapsed = _l4_ihc_trajectory(
            capture,
            receptor,
            assembly_id=f"ihc-adaptation-{item.item_id}",
            source_anchor=Fraction(item.ordinal * 2),
        )
        complete = dict(receptor)
        complete.update(l4)
        receptor_by_id[item.item_id] = receptor
        l4_by_id[item.item_id] = l4
        complete_by_id[item.item_id] = complete
        roots.append({
            "item_id": item.item_id,
            "ihc_receptor_root_sha256": _trajectory_root(receptor),
            "ihc_l4_root_sha256": _trajectory_root(l4),
            "complete_ihc_root_sha256": _trajectory_root(complete),
        })
        transduction_seconds += capture.transduction_seconds
        l0_l4_seconds += elapsed

    memories = {"receptor": {}, "l4": {}, "complete": {}}
    sources = {
        "receptor": receptor_by_id,
        "l4": l4_by_id,
        "complete": complete_by_id,
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
        "adaptation_law": (
            "half-wave real basilar displacement; exact positive sample "
            "increment is onset release; exact negative sample increment is "
            "recovery release; no fitted decay or threshold"
        ),
        "archive_sha256": archive_sha256,
        "canonical_code_modified": False,
        "complete_ihc_lane_count": (
            IHC_PORT_COUNT * (1 + len(DSF_FIELD_ORDER))
        ),
        "decision_rule_declared_before_results": (
            "each held-out grounded command must have strictly more exact "
            "complete IHC lanes than every competitor and be the only "
            "canonical-L6 lock; the unrelated tone must have no L6 lock"
        ),
        "decisive_pass": decisive_pass,
        "full_explicit_dsf_field_order": list(DSF_FIELD_ORDER),
        "held_out": held_records,
        "ihc_fields": list(IHC_FIELDS),
        "l4_ihc_lane_count": IHC_PORT_COUNT * len(DSF_FIELD_ORDER),
        "receptor_ihc_lane_count": IHC_PORT_COUNT,
        "resource_cost": {
            "audio_seconds_processed": audio_seconds,
            "fixed_ihc_ports": IHC_PORT_COUNT,
            "incremental_stream_state_bytes": CHANNEL_COUNT * 8,
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
