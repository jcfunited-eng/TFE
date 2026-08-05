"""Authenticated raw-to-L4 auditory information-loss localization.

This audit is deliberately outside production.  It keeps the frozen L0--L4
implementation unchanged, withholds command labels until every pair relation
exists, and reports two exact quotient views at every layer:

* whole trajectories modulo one positive rational scale per numeric partition;
* complete local order alphabets per explicit partition.

The strict joint relation is the conjunction of all explicit partitions.  It
is not a score or weighted reduction.  Every quotient discloses its losses.

The same report separately exercises genuine W1 stereo propagation, exact
overlapping-source separation, brainstem interaural relations, and mirrored
bilateral assemblies.  The controlled chamber deliberately omits pinna,
head-shadow, diffraction, reflections, reverberation, and sensor noise.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import wave
import zipfile
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import numpy as np

from dsf_ai_service.glew_runtime.exact_field_executor import (
    start_exact_field_executor,
    stop_exact_field_executor,
)
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    BuiltSixSenseFullField,
    build_transaction_owned_six_sense_full_field,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.auditory_kernel_mount import (
    auditory_kernel_component_inputs,
)
from dsf_ai_service.substrate.canonical_l6 import canonical_l6_direction
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    REQUIRED_SAMPLE_RATE_HZ,
    AuditoryFullFieldCapture,
    transduce_auditory_full_field,
)
from dsf_ai_service.substrate.w1_binaural_acoustic_physics import (
    binaural_sound_field_inputs,
    pcm16_bytes,
    scaled_pcm16_sample,
    signed_pcm16_samples,
)
from dsf_ai_service.substrate.w1_exact_binaural_source_separation import (
    ExactBinauralSeparationState,
    separate_exact_binaural_sources,
)
from tools.isolated_w1_physical_stereo_path import (
    PhysicalStereoAuditAuthority,
)
from tools.probe_auditory_full_field_separability_census import (
    ARCHIVE_SHA256,
    COMMANDS,
    CorpusItem,
    _select_corpus,
)


REPORT_SCHEMA = "guala.audit.auditory_layer_information_loss.v1"
RELATION_SCHEMA = "guala.audit.auditory_layer_relation.v1"
EXPERIENCE_SCHEMA = "guala.audit.auditory_layer_experience.v1"
AUTHORITY_KEY = b"guala-auditory-layer-information-loss-audit-20260727"
LAYER_ORDER = (
    "raw_pcm",
    "cochlear_receptor",
    "L0_SEV",
    "L1_GateL1State",
    "L2_GateInterpretation",
    "L3_ResonanceResult",
    "L4_DSF",
)
QUOTIENTS = (
    "whole_trajectory_positive_scale_v1",
    "local_structural_alphabet_v1",
)
QUOTIENT_LOSSES = {
    "whole_trajectory_positive_scale_v1": (
        "one common positive magnitude scale per numeric partition",
        "absolute numeric magnitude",
        "cross-partition magnitude relations",
        "time alignment between different-length experiences",
    ),
    "local_structural_alphabet_v1": (
        "absolute numeric magnitude",
        "duration and event multiplicity",
        "global temporal order beyond adjacent triples",
        "cross-partition simultaneity",
        "categorical duration beyond adjacent transitions",
    ),
}


Scalar = Fraction | str
Partitions = dict[str, tuple[Scalar, ...]]


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


def _scalar_record(value: Scalar) -> list[str]:
    if isinstance(value, Fraction):
        return ["fraction", _fraction_text(value)]
    if isinstance(value, str):
        return ["categorical", value]
    raise TypeError("layer audit scalar left exact custody")


def _root(schema: str, values: Iterable[str]) -> str:
    return _digest({
        "schema": schema,
        "sha256s": sorted(set(values)),
    })


def _l6(value) -> dict[str, object]:
    return {
        "dimensions": value.dimensions,
        "effective_dimensions": value.effective_dimensions,
        "knee": value.knee,
        "locked": value.locked,
        "matching_non_null": value.matching_non_null,
        "matching_quiescent": value.matching_quiescent,
    }


def _parse_scalar(value: object) -> Scalar | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, str):
        try:
            return Fraction(value)
        except (ValueError, ZeroDivisionError):
            return value
    return None


def _leaf_paths(
    value: object,
    *,
    prefix: str = "",
) -> Iterable[tuple[str, Scalar]]:
    parsed = _parse_scalar(value)
    if parsed is not None:
        yield prefix, parsed
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            yield from _leaf_paths(
                child,
                prefix=f"{prefix}[{index}]",
            )
        return
    if isinstance(value, dict):
        for name in sorted(value):
            if name in ("start_idx", "end_idx"):
                continue
            yield from _leaf_paths(
                value[name],
                prefix=f"{prefix}.{name}" if prefix else name,
            )


def _trace_partitions(
    built: BuiltSixSenseFullField,
) -> dict[str, Partitions]:
    result = {name: {} for name in LAYER_ORDER[2:]}
    for component_index, support in enumerate(
        built._source_l0_l4_supports
    ):
        trace_digest = support[0]
        trace = json.loads(
            built.receipt_registry.resolve(
                trace_digest, "L0-L4 trace"
            )
        )
        for layer_name in LAYER_ORDER[2:]:
            rows = trace.get(layer_name)
            if not isinstance(rows, list) or not rows:
                raise ValueError(
                    f"{layer_name} trace partition is absent"
                )
            by_path: dict[str, list[Scalar]] = {}
            expected_paths = None
            for row in rows:
                leaves = tuple(_leaf_paths(row))
                paths = tuple(path for path, _value in leaves)
                if expected_paths is None:
                    expected_paths = paths
                elif paths != expected_paths:
                    raise ValueError(
                        f"{layer_name} row shape changed"
                    )
                for path, value in leaves:
                    by_path.setdefault(path, []).append(value)
            for path, values in by_path.items():
                result[layer_name][
                    f"component:{component_index:02d}/{path}"
                ] = tuple(values)
    return result


def _receptor_partitions(
    capture: AuditoryFullFieldCapture,
    *,
    prefix: str = "",
) -> Partitions:
    result: Partitions = {}
    fields = (
        "pressure_envelope_full_scale",
        "carrier_phase_turns",
        "carrier_phase_advance_turns",
        "carrier_phase_advance_nyquist_fraction",
    )
    for channel_index, channel in enumerate(capture.channels):
        for field_name in fields:
            result[
                f"{prefix}channel:{channel_index:02d}/{field_name}"
            ] = tuple(
                Fraction.from_float(float(value))
                for value in getattr(channel, field_name)
            )
    return result


def _states() -> dict[PhysicalSense, SenseBoundaryState]:
    return {
        sense: (
            SenseBoundaryState.OBSERVED
            if sense is PhysicalSense.SOUND
            else SenseBoundaryState.SENSOR_UNAVAILABLE
        )
        for sense in SENSE_ORDER
    }


def _build_mono(
    *,
    item: CorpusItem,
    pcm: bytes,
) -> tuple[dict[str, Partitions], BuiltSixSenseFullField]:
    samples = signed_pcm16_samples(pcm)
    signal = np.asarray(samples, dtype=np.float64) / 32_768.0
    capture = transduce_auditory_full_field(
        signal,
        sample_rate_hz=REQUIRED_SAMPLE_RATE_HZ,
    )
    anchor = Fraction(item.ordinal * 4)
    inputs = auditory_kernel_component_inputs(
        capture,
        source_anchor=anchor,
    )
    built = build_transaction_owned_six_sense_full_field(
        assembly_id=f"layer-loss-mono-{item.item_id}",
        source_time_start=anchor,
        source_time_end=anchor + Fraction(
            len(samples), REQUIRED_SAMPLE_RATE_HZ
        ),
        observed_substreams={PhysicalSense.SOUND: inputs},
        states=_states(),
    )
    built.verify_construction()
    layers: dict[str, Partitions] = {
        "raw_pcm": {
            "mono/pressure": tuple(
                Fraction(value, 32_768) for value in samples
            ),
        },
        "cochlear_receptor": _receptor_partitions(capture),
    }
    layers.update(_trace_partitions(built))
    if tuple(layers) != LAYER_ORDER:
        raise ValueError("raw-to-L4 layer order changed")
    return layers, built


def _build_physical_stereo(
    *,
    item: CorpusItem,
    pcm: bytes,
    authority: PhysicalStereoAuditAuthority,
) -> tuple[dict[str, Partitions], dict[str, object]]:
    source_ordinal = item.ordinal % 2
    capture = authority.render(
        (pcm,),
        source_ordinals=(source_ordinal,),
    )
    brainstem = authority.compare_brainstem(capture)
    anchor = Fraction(item.ordinal * 4 + 2)
    inputs = (
        *binaural_sound_field_inputs(
            ear="left",
            topology_index=0,
            pcm=capture.left_pcm_s16le,
            source_time_start=anchor,
        ),
        *binaural_sound_field_inputs(
            ear="right",
            topology_index=32,
            pcm=capture.right_pcm_s16le,
            source_time_start=anchor,
        ),
    )
    built = build_transaction_owned_six_sense_full_field(
        assembly_id=f"layer-loss-stereo-{item.item_id}",
        source_time_start=anchor,
        source_time_end=anchor + Fraction(
            capture.capture_sample_count,
            REQUIRED_SAMPLE_RATE_HZ,
        ),
        observed_substreams={PhysicalSense.SOUND: inputs},
        states=_states(),
    )
    built.verify_construction()
    traces = _trace_partitions(built)
    brainstem_partitions: Partitions = {}
    brainstem_fields = (
        "path_delay_difference_samples",
        "envelope_level_difference",
        "cumulative_phase_difference_turns",
        "phase_advance_difference_turns",
    )
    for channel_index in range(16):
        channel_frames = tuple(
            frame for frame in brainstem.frames
            if frame.channel_index == channel_index
        )
        for field_name in brainstem_fields:
            brainstem_partitions[
                f"channel:{channel_index:02d}/{field_name}"
            ] = tuple(
                Fraction(getattr(frame, field_name))
                for frame in channel_frames
            )
    sound = next(
        value for value in built.boundary.boundaries
        if value.sense is PhysicalSense.SOUND
    )
    basin_receipts = tuple(
        value.kernel_basin.authority_receipt_sha256
        for value in sound.substreams
    )
    if len(basin_receipts) != 64:
        raise ValueError("physical stereo lost one ear")
    assembly = authority.assemble_bilateral(
        left_ear_port_receipt_sha256s=basin_receipts[:32],
        right_ear_port_receipt_sha256s=basin_receipts[32:],
        brainstem=brainstem,
    )
    return {
        "physical_stereo_brainstem": brainstem_partitions,
        "physical_stereo_L4_DSF": traces["L4_DSF"],
    }, {
        "bilateral_assembly_receipt_sha256": (
            assembly.authority_receipt_sha256
        ),
        "brainstem_receipt_sha256": (
            brainstem.authority_receipt_sha256
        ),
        "capture_receipt_sha256": capture.authority_receipt_sha256,
        "capture_sample_count": capture.capture_sample_count,
        "left_hemisphere_port_count": len(
            assembly.left_hemisphere_port_receipt_sha256s
        ),
        "path": capture.paths[0].payload(),
        "right_hemisphere_port_count": len(
            assembly.right_hemisphere_port_receipt_sha256s
        ),
        "source_ordinal": source_ordinal,
        "unsettled_tail_sample_count": (
            capture.capture_sample_count % 160
        ),
    }


def _trajectory_token(
    partition_id: str,
    values: Sequence[Scalar],
) -> str:
    if not values:
        raise ValueError("empty layer trajectory")
    if all(isinstance(value, Fraction) for value in values):
        exact = tuple(value for value in values if isinstance(value, Fraction))
        pivot = next((value for value in exact if value != 0), None)
        normalized = (
            tuple(Fraction(0) for _value in exact)
            if pivot is None
            else tuple(value / abs(pivot) for value in exact)
        )
        quotient: object = [
            _scalar_record(value) for value in normalized
        ]
    elif all(isinstance(value, str) for value in values):
        quotient = [_scalar_record(value) for value in values]
    else:
        raise ValueError("layer trajectory mixed scalar kinds")
    return _digest({
        "partition_id": partition_id,
        "quotient": quotient,
        "schema": "guala.audit.whole_trajectory_token.v1",
    })


def _direction(left: Fraction, right: Fraction) -> int:
    return (right > left) - (right < left)


def _alphabet_tokens(
    partition_id: str,
    values: Sequence[Scalar],
) -> frozenset[str]:
    if not values:
        raise ValueError("layer trajectory is empty")
    if len(values) == 1:
        return frozenset({
            _digest({
                "partition_id": partition_id,
                "quotient": [
                    "singleton-state",
                    _scalar_record(values[0]),
                ],
                "schema": "guala.audit.local_structural_token.v1",
            })
        })
    quotients: set[object] = set()
    if all(isinstance(value, Fraction) for value in values):
        exact = tuple(value for value in values if isinstance(value, Fraction))
        if len(exact) >= 3:
            quotients.update(
                (
                    "numeric-order",
                    _direction(left, middle),
                    _direction(middle, right),
                )
                for left, middle, right in zip(
                    exact, exact[1:], exact[2:]
                )
            )
        else:
            quotients.add((
                "numeric-order",
                _direction(exact[0], exact[1]),
            ))
    elif all(isinstance(value, str) for value in values):
        quotients.update(
            ("categorical-transition", left, right)
            for left, right in zip(values, values[1:])
        )
    else:
        raise ValueError("layer alphabet mixed scalar kinds")
    return frozenset(
        _digest({
            "partition_id": partition_id,
            "quotient": quotient,
            "schema": "guala.audit.local_structural_token.v1",
        })
        for quotient in quotients
    )


@dataclass(frozen=True, slots=True)
class Signature:
    layer_id: str
    quotient_id: str
    partition_tokens: tuple[tuple[str, frozenset[str]], ...]
    authority_receipt_sha256: str


def _signature(
    layer_id: str,
    quotient_id: str,
    partitions: Mapping[str, Sequence[Scalar]],
) -> Signature:
    if not partitions:
        raise ValueError("layer signature lacks partitions")
    values = []
    for partition_id in sorted(partitions):
        trajectory = partitions[partition_id]
        tokens = (
            frozenset({_trajectory_token(partition_id, trajectory)})
            if quotient_id == QUOTIENTS[0]
            else _alphabet_tokens(partition_id, trajectory)
        )
        values.append((partition_id, tokens))
    payload = {
        "layer_id": layer_id,
        "partition_token_roots": [
            [
                partition_id,
                _root(
                    "guala.audit.layer_partition_tokens.v1",
                    tokens,
                ),
            ]
            for partition_id, tokens in values
        ],
        "quotient_id": quotient_id,
        "schema": "guala.audit.layer_signature.v1",
    }
    return Signature(
        layer_id=layer_id,
        quotient_id=quotient_id,
        partition_tokens=tuple(values),
        authority_receipt_sha256=_digest(payload),
    )


def _relation(left: Signature, right: Signature) -> dict[str, object]:
    if (
        left.layer_id != right.layer_id
        or left.quotient_id != right.quotient_id
    ):
        raise ValueError("layer relation crossed authorities")
    left_map = dict(left.partition_tokens)
    right_map = dict(right.partition_tokens)
    if left_map.keys() != right_map.keys():
        raise ValueError("layer relation topology changed")
    partitions = []
    for partition_id in sorted(left_map):
        left_tokens = left_map[partition_id]
        right_tokens = right_map[partition_id]
        matching = len(left_tokens.intersection(right_tokens))
        left_l6 = canonical_l6_direction(
            dimensions=len(left_tokens),
            matching_non_null=matching,
            matching_quiescent=0,
        )
        right_l6 = canonical_l6_direction(
            dimensions=len(right_tokens),
            matching_non_null=matching,
            matching_quiescent=0,
        )
        partitions.append({
            "intersection_root_sha256": _root(
                "guala.audit.layer_partition_intersection.v1",
                left_tokens.intersection(right_tokens),
            ),
            "left_l6": _l6(left_l6),
            "locked": left_l6.locked and right_l6.locked,
            "partition_id": partition_id,
            "right_l6": _l6(right_l6),
        })
    payload = {
        "joint_relation_locked": all(
            bool(value["locked"]) for value in partitions
        ),
        "layer_id": left.layer_id,
        "left_signature_receipt_sha256": (
            left.authority_receipt_sha256
        ),
        "locked_partition_count": sum(
            bool(value["locked"]) for value in partitions
        ),
        "partition_count": len(partitions),
        "partition_relation_root_sha256": _digest({
            "partitions": partitions,
            "schema": "guala.audit.layer_partition_relations.v1",
        }),
        "quotient_id": left.quotient_id,
        "right_signature_receipt_sha256": (
            right.authority_receipt_sha256
        ),
        "schema": RELATION_SCHEMA,
    }
    return payload | {
        "authority_receipt_sha256": _digest(payload),
    }


def _evaluate(
    *,
    items: Sequence[CorpusItem],
    signatures: Mapping[str, Signature],
) -> dict[str, object]:
    matrix = []
    for left in items:
        row = []
        for right in items:
            row.append(_relation(
                signatures[left.item_id],
                signatures[right.item_id],
            ))
        matrix.append(row)
    within_total = 0
    within_locked = 0
    cross_total = 0
    cross_locked = 0
    held_out_total = 0
    held_out_pass = 0
    for left_index, left in enumerate(items):
        for right_index in range(left_index + 1, len(items)):
            right = items[right_index]
            locked = bool(
                matrix[left_index][right_index][
                    "joint_relation_locked"
                ]
            )
            if left.oracle_command == right.oracle_command:
                within_total += 1
                within_locked += int(locked)
            else:
                cross_total += 1
                cross_locked += int(locked)
    reference_indices = {
        command: tuple(
            index for index, item in enumerate(items)
            if (
                item.oracle_command == command
                and item.split == "reference"
            )
        )
        for command in COMMANDS
    }
    for query_index, query in enumerate(items):
        if query.split != "held_out":
            continue
        held_out_total += 1
        same = reference_indices[query.oracle_command]
        other = tuple(
            index
            for command, indices in reference_indices.items()
            if command != query.oracle_command
            for index in indices
        )
        passed = (
            all(
                matrix[query_index][index][
                    "joint_relation_locked"
                ]
                for index in same
            )
            and not any(
                matrix[query_index][index][
                    "joint_relation_locked"
                ]
                for index in other
            )
        )
        held_out_pass += int(passed)
    return {
        "cross_command_locked_pairs": cross_locked,
        "cross_command_pair_count": cross_total,
        "held_out_pass_count": held_out_pass,
        "held_out_total": held_out_total,
        "matrix": matrix,
        "relation_passed": (
            within_locked == within_total
            and cross_locked == 0
            and held_out_pass == held_out_total
        ),
        "selective_recurrence_present": (
            within_locked > 0 and cross_locked == 0
        ),
        "within_command_locked_pairs": within_locked,
        "within_command_pair_count": within_total,
    }


def _read_pcm(wav_data: bytes) -> bytes:
    with wave.open(io.BytesIO(wav_data), "rb") as source:
        if (
            source.getnchannels() != 1
            or source.getsampwidth() != 2
            or source.getframerate() != REQUIRED_SAMPLE_RATE_HZ
            or source.getcomptype() != "NONE"
        ):
            raise ValueError("corpus PCM custody changed")
        result = source.readframes(source.getnframes())
    return result


def _scaled_source(pcm: bytes) -> bytes:
    return pcm16_bytes(tuple(
        scaled_pcm16_sample(value, Fraction(1, 4))
        for value in signed_pcm16_samples(pcm)
    ))


def _segregation_checks(
    *,
    items: Sequence[CorpusItem],
    pcm_by_item: Mapping[str, bytes],
    authority: PhysicalStereoAuditAuthority,
) -> list[dict[str, object]]:
    checks = []
    first_by_command = {
        command: next(
            item for item in items
            if item.oracle_command == command
        )
        for command in COMMANDS
    }
    for index, command in enumerate(COMMANDS):
        left = first_by_command[command]
        right = first_by_command[
            COMMANDS[(index + 1) % len(COMMANDS)]
        ]
        sources = (
            _scaled_source(pcm_by_item[left.item_id]),
            _scaled_source(pcm_by_item[right.item_id]),
        )
        capture = authority.render(
            sources,
            source_ordinals=(0, 1),
        )
        separated = separate_exact_binaural_sources(
            left_pcm_s16le=capture.left_pcm_s16le,
            right_pcm_s16le=capture.right_pcm_s16le,
            paths=capture.paths,
            source_sample_count=capture.source_sample_count,
        )
        separated.verify()
        exact = (
            separated.state
            is ExactBinauralSeparationState.SEPARATED
            and separated.separated_pcm_s16le == sources
        )
        checks.append({
            "capture_receipt_sha256": (
                capture.authority_receipt_sha256
            ),
            "exact_scaled_emitter_recovery": exact,
            "left_item_id": left.item_id,
            "right_item_id": right.item_id,
            "separation_receipt_sha256": (
                separated.authority_receipt_sha256
            ),
            "source_scale": "1/4",
        })
    return checks


def run_audit(archive_path: Path) -> dict[str, object]:
    if hashlib.sha256(archive_path.read_bytes()).hexdigest() != ARCHIVE_SHA256:
        raise ValueError("speech-command archive authority changed")
    authority = PhysicalStereoAuditAuthority(
        authority_key=AUTHORITY_KEY
    )
    with zipfile.ZipFile(archive_path) as archive:
        items = _select_corpus(archive)
        pcm_by_item = {
            item.item_id: _read_pcm(archive.read(item.archive_member))
            for item in items
        }
    mono_layers: dict[str, dict[str, Partitions]] = {}
    stereo_layers: dict[str, dict[str, Partitions]] = {}
    experience_records = []
    executor = start_exact_field_executor()
    executor.assert_healthy()
    try:
        for item in items:
            layers, _built = _build_mono(
                item=item,
                pcm=pcm_by_item[item.item_id],
            )
            physical_layers, physical_record = _build_physical_stereo(
                item=item,
                pcm=pcm_by_item[item.item_id],
                authority=authority,
            )
            mono_layers[item.item_id] = layers
            stereo_layers[item.item_id] = physical_layers
            experience_payload = {
                "item_id": item.item_id,
                "layer_partition_counts": {
                    layer: len(partitions)
                    for layer, partitions in layers.items()
                },
                "oracle_command": item.oracle_command,
                "physical_stereo": physical_record,
                "schema": EXPERIENCE_SCHEMA,
                "speaker_id": item.speaker_id,
                "split": item.split,
            }
            experience_records.append(
                experience_payload | {
                    "authority_receipt_sha256": _digest(
                        experience_payload
                    )
                }
            )
    finally:
        stop_exact_field_executor()

    all_layer_ids = (
        *LAYER_ORDER,
        "physical_stereo_brainstem",
        "physical_stereo_L4_DSF",
    )
    layer_reports = {}
    for layer_id in all_layer_ids:
        source = (
            mono_layers
            if layer_id in LAYER_ORDER
            else stereo_layers
        )
        quotient_reports = {}
        for quotient_id in QUOTIENTS:
            signatures = {
                item.item_id: _signature(
                    layer_id,
                    quotient_id,
                    source[item.item_id][layer_id],
                )
                for item in items
            }
            quotient_reports[quotient_id] = {
                "evaluation": _evaluate(
                    items=items,
                    signatures=signatures,
                ),
                "quotient_loses": list(
                    QUOTIENT_LOSSES[quotient_id]
                ),
                "signature_receipt_root_sha256": _root(
                    "guala.audit.layer_signature_receipts.v1",
                    (
                        signature.authority_receipt_sha256
                        for signature in signatures.values()
                    ),
                ),
            }
        layer_reports[layer_id] = {
            "full_partition_conjunction": True,
            "quotients": quotient_reports,
        }

    segregation = _segregation_checks(
        items=items,
        pcm_by_item=pcm_by_item,
        authority=authority,
    )
    selective = {
        quotient_id: [
            layer_id for layer_id in LAYER_ORDER
            if layer_reports[layer_id]["quotients"][
                quotient_id
            ]["evaluation"]["selective_recurrence_present"]
        ]
        for quotient_id in QUOTIENTS
    }
    localization = {
        "cochlear_receptor_declared_information_reduction": True,
        "earliest_selective_recurrence_disappearance": {
            quotient_id: (
                None
                if not selective[quotient_id]
                else next(
                    (
                        LAYER_ORDER[index + 1]
                        for index, layer_id in enumerate(
                            LAYER_ORDER[:-1]
                        )
                        if (
                            layer_id in selective[quotient_id]
                            and LAYER_ORDER[index + 1]
                            not in selective[quotient_id]
                        )
                    ),
                    None,
                )
            )
            for quotient_id in QUOTIENTS
        },
        "kernel_change_justified_by_recurrence_audit": False,
        "reason": (
            "No declared exact quotient establishes selective "
            "within-command recurrence at raw PCM, so no later layer can be "
            "identified as the point where established recurrence vanished."
        ),
        "selective_recurrence_layers": selective,
    }
    report = {
        "archive_sha256": ARCHIVE_SHA256,
        "controlled_chamber_missing_physics": [
            "pinna transfer",
            "head shadow",
            "diffraction",
            "reflections",
            "reverberation",
            "sensor noise",
        ],
        "corpus_item_ids": [item.item_id for item in items],
        "experience_records": experience_records,
        "labels_used_by_relations": False,
        "layer_order": list(LAYER_ORDER),
        "layer_reports": layer_reports,
        "localization": localization,
        "l0_l4_modified": False,
        "physical_stereo": {
            "brainstem_topology_receipt_sha256": (
                authority.topology_receipt_sha256
            ),
            "ear_positions_mm": [
                [value.x, value.y, value.z]
                for value in authority.ears
            ],
            "mirrored_bilateral_no_weights": True,
            "source_positions_mm": [
                [value.x, value.y, value.z]
                for value in authority.sources
            ],
            "source_segregation_checks": segregation,
            "source_segregation_passed": all(
                value["exact_scaled_emitter_recovery"]
                for value in segregation
            ),
            "transfer_paths": [
                value.payload() for value in authority.paths
            ],
        },
        "schema": REPORT_SCHEMA,
        "source_disjoint_speaker_count": len({
            item.speaker_id for item in items
        }),
    }
    return report | {
        "authority_receipt_sha256": _digest(report),
    }


def _summary(report: Mapping[str, object]) -> dict[str, object]:
    layers = report["layer_reports"]
    return {
        "authority_receipt_sha256": report[
            "authority_receipt_sha256"
        ],
        "layer_evaluations": {
            layer_id: {
                quotient_id: {
                    key: value
                    for key, value in quotient["evaluation"].items()
                    if key != "matrix"
                }
                for quotient_id, quotient in layer["quotients"].items()
            }
            for layer_id, layer in layers.items()
        },
        "localization": report["localization"],
        "physical_stereo": {
            "source_segregation_passed": report[
                "physical_stereo"
            ]["source_segregation_passed"],
            "transfer_paths": report["physical_stereo"][
                "transfer_paths"
            ],
        },
        "schema": "guala.audit.auditory_layer_information_loss_summary.v1",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    report = run_audit(args.archive)
    if args.output is not None:
        args.output.write_bytes(
            json.dumps(
                report, indent=2, sort_keys=True
            ).encode("utf-8") + b"\n"
        )
    print(json.dumps(
        _summary(report) if args.summary else report,
        indent=2,
        sort_keys=True,
    ))


if __name__ == "__main__":
    main()
