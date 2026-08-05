"""Trace real recordings through Guala's canonical auditory full field.

This conformance probe performs no speech transcription and assigns no word
meaning from acoustics.  It proves whether different source recordings remain
different through PCM, cochlear transduction, the complete thirty-two-port
unchanged L0--L4 field, and auditory L5.  When two tutor recordings and a
query recording are supplied, it also measures the existing learned
cross-instance spoken-form relation without altering the sensory evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

import numpy as np

from dsf_ai_service.glew_runtime.exact_field_executor import (
    start_exact_field_executor,
    stop_exact_field_executor,
)
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
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
from dsf_ai_service.substrate.auditory_l5 import (
    AuditoryL5Experience,
    AuditoryL5Owner,
)
from dsf_ai_service.substrate.auditory_reciprocity import (
    AuditoryReciprocityKind,
    AuditoryReciprocityOwner,
)
from dsf_ai_service.substrate.auditory_tutor_authority import (
    AuditoryTutorAuthority,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    REQUIRED_SAMPLE_RATE_HZ,
    transduce_auditory_full_field,
)


@dataclass(frozen=True, slots=True)
class TracedRecording:
    report: dict[str, object]
    experience: AuditoryL5Experience


def _canonical_digest(value: object) -> str:
    encoded = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _decode_pcm(path: Path) -> bytes:
    completed = subprocess.run(
        (
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(path),
            "-ac",
            "1",
            "-ar",
            str(REQUIRED_SAMPLE_RATE_HZ),
            "-f",
            "s16le",
            "-",
        ),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    pcm = completed.stdout
    if not pcm or len(pcm) % 2:
        raise RuntimeError(f"decoded PCM is invalid: {path}")
    return pcm


def _cochlear_payload(capture) -> dict[str, object]:
    return {
        "input_sample_count": capture.input_sample_count,
        "observation_hop_samples": capture.observation_hop_samples,
        "source_sample_rate_hz": capture.source_sample_rate_hz,
        "channels": [
            {
                "name": channel.definition.name,
                "offsets_ns": list(channel.causal_offsets_ns),
                "pressure": [
                    value.hex()
                    for value in channel.pressure_envelope_full_scale
                ],
                "phase_advance": [
                    value.hex()
                    for value in channel.carrier_phase_advance_turns
                ],
                "phase_advance_nyquist": [
                    value.hex()
                    for value in channel.carrier_phase_advance_nyquist_fraction
                ],
            }
            for channel in capture.channels
        ],
    }


def _mounted_payload(components) -> list[dict[str, object]]:
    return [
        {
            "substream_id": component.substream_id,
            "topology_index": component.topology_index,
            "normalized_signal": [
                float(value).hex() for value in component.normalized_signal
            ],
            "phase_turns": [
                f"{value.numerator}/{value.denominator}"
                for value in component.phase_turns
            ],
        }
        for component in components
    ]


def _l4_payload(experience) -> list[dict[str, object]]:
    values: list[dict[str, object]] = []
    for channel in experience.channels:
        for component in (channel.pressure, channel.carrier_phase_advance):
            values.append({
                "substream_id": component.substream_id,
                "topology_index": component.topology_index,
                "tuples": [
                    {
                        "tuple_index": item.tuple_index,
                        "fields": [
                            [
                                name,
                                f"{field.numerator}/{field.denominator}",
                            ]
                            for name, field in item.fields
                        ],
                    }
                    for item in component.l4_field_tuples
                ],
            })
    return values


def _trace(
    path: Path,
    ordinal: int,
    l5_owner: AuditoryL5Owner,
) -> TracedRecording:
    source_bytes = path.read_bytes()
    pcm = _decode_pcm(path)
    samples_i16 = np.frombuffer(pcm, dtype="<i2")
    samples = samples_i16.astype(np.float64) / 32768.0
    capture = transduce_auditory_full_field(
        samples,
        sample_rate_hz=REQUIRED_SAMPLE_RATE_HZ,
    )
    anchor = Fraction(1_000 + ordinal * 100)
    components = auditory_kernel_component_inputs(
        capture,
        source_anchor=anchor,
    )
    source_end = anchor + Fraction(
        len(samples_i16),
        REQUIRED_SAMPLE_RATE_HZ,
    )
    states = {
        sense: (
            SenseBoundaryState.OBSERVED
            if sense is PhysicalSense.SOUND
            else SenseBoundaryState.SENSOR_UNAVAILABLE
        )
        for sense in SENSE_ORDER
    }
    built = build_transaction_owned_six_sense_full_field(
        assembly_id=f"auditory-discrimination-{ordinal}",
        source_time_start=anchor,
        source_time_end=source_end,
        observed_substreams={PhysicalSense.SOUND: components},
        states=states,
    )
    experience = l5_owner.settle(
        built,
        event_boundary="utterance",
    )
    if experience is None:
        raise RuntimeError(f"auditory L5 rejected observed sound: {path}")
    experience.verify()

    cochlear_payload = _cochlear_payload(capture)
    mounted_payload = _mounted_payload(components)
    l4_payload = _l4_payload(experience)
    return TracedRecording(
        report={
            "path": str(path),
            "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
            "pcm_sha256": hashlib.sha256(pcm).hexdigest(),
            "sample_count": len(samples_i16),
            "pcm_min": int(samples_i16.min()),
            "pcm_max": int(samples_i16.max()),
            "pcm_nonzero": int(np.count_nonzero(samples_i16)),
            "cochlear_sha256": _canonical_digest(cochlear_payload),
            "cochlear_frame_count": capture.frame_count,
            "mounted_sha256": _canonical_digest(mounted_payload),
            "l4_sha256": _canonical_digest(l4_payload),
            "l4_tuple_count": sum(
                len(component["tuples"]) for component in l4_payload
            ),
            "l5_structural_fingerprint": (
                experience.structural_fingerprint
            ),
            "component_l4_sha256": {
                component["substream_id"]: _canonical_digest(
                    component["tuples"]
                )
                for component in l4_payload
            },
        },
        experience=experience,
    )


def _first_equal_boundary(
    left: dict[str, object],
    right: dict[str, object],
) -> str | None:
    for boundary in (
        "source_sha256",
        "pcm_sha256",
        "cochlear_sha256",
        "mounted_sha256",
        "l4_sha256",
        "l5_structural_fingerprint",
    ):
        if left[boundary] == right[boundary]:
            return boundary
    return None


def _recognition_probe(
    traces: list[TracedRecording],
    tutor_indices: tuple[int, int] | None,
    query_index: int | None,
    tutor_label: str,
) -> dict[str, object] | None:
    if tutor_indices is None or query_index is None:
        return None
    reciprocity = AuditoryReciprocityOwner(
        log_event=lambda *_args, **_kwargs: None,
        tutor_authority=AuditoryTutorAuthority.unrequired(),
    )
    learned = None
    for index in tutor_indices:
        learned = reciprocity.teach(
            traces[index].experience,
            kind=AuditoryReciprocityKind.SPOKEN_FORM,
            tutor_label=tutor_label,
        )
    if learned is None:
        raise RuntimeError("auditory recognition probe taught no branch")
    recognition, work = reciprocity.recognize_bounded(
        traces[query_index].experience,
        kind=AuditoryReciprocityKind.SPOKEN_FORM,
        max_work=1_000_000,
    )
    return {
        "tutor_indices": list(tutor_indices),
        "query_index": query_index,
        "tutor_label": tutor_label,
        "learned_branch_count": len(learned.branches),
        "reinforcement_count": learned.reinforcement_count,
        "recognition_state": recognition.state.value,
        "recognized_label": recognition.tutor_label,
        "candidate_labels": list(recognition.candidate_labels),
        "work_cells": work,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("recordings", nargs="+", type=Path)
    parser.add_argument("--tutor-indices", nargs=2, type=int)
    parser.add_argument("--query-index", type=int)
    parser.add_argument("--tutor-label", default="hello guala")
    args = parser.parse_args()
    if len(args.recordings) < 2:
        raise SystemExit("at least two recordings are required")
    for path in args.recordings:
        if not path.is_file():
            raise SystemExit(f"recording does not exist: {path}")
    tutor_indices = (
        tuple(args.tutor_indices)
        if args.tutor_indices is not None
        else None
    )
    selected = (
        (*tutor_indices, args.query_index)
        if tutor_indices is not None and args.query_index is not None
        else ()
    )
    if any(
        index < 0 or index >= len(args.recordings)
        for index in selected
    ):
        raise SystemExit("recognition probe index is outside the recordings")

    exact_owner = start_exact_field_executor()
    exact_owner.assert_healthy()
    l5_owner = AuditoryL5Owner(
        log_event=lambda *_args, **_kwargs: None,
    )
    try:
        traces = [
            _trace(path.resolve(), ordinal, l5_owner)
            for ordinal, path in enumerate(args.recordings)
        ]
    finally:
        stop_exact_field_executor()

    comparisons = []
    for left_index, left in enumerate(traces):
        for right in traces[left_index + 1:]:
            left_report = left.report
            right_report = right.report
            comparisons.append({
                "left": left_report["path"],
                "right": right_report["path"],
                "first_equal_boundary": _first_equal_boundary(
                    left_report, right_report
                ),
                "pcm_equal": (
                    left_report["pcm_sha256"]
                    == right_report["pcm_sha256"]
                ),
                "cochlear_equal": (
                    left_report["cochlear_sha256"]
                    == right_report["cochlear_sha256"]
                ),
                "l4_equal": (
                    left_report["l4_sha256"]
                    == right_report["l4_sha256"]
                ),
                "l5_equal": (
                    left_report["l5_structural_fingerprint"]
                    == right_report["l5_structural_fingerprint"]
                ),
            })
    print(json.dumps(
        {
            "schema": "guala.audit.auditory_full_field_discrimination.v2",
            "recordings": [trace.report for trace in traces],
            "comparisons": comparisons,
            "learned_cross_instance": _recognition_probe(
                traces,
                tutor_indices,
                args.query_index,
                args.tutor_label,
            ),
        },
        indent=2,
        sort_keys=True,
    ))


if __name__ == "__main__":
    main()
