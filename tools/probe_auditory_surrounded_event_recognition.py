"""Test the live spoken-form owner on physically settled utterance events."""

from __future__ import annotations

import argparse
import io
import json
import wave
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
from dsf_ai_service.substrate.auditory_l5 import AuditoryL5Owner
from dsf_ai_service.substrate.auditory_reciprocity import (
    AuditoryReciprocityKind,
    AuditoryReciprocityOwner,
)
from dsf_ai_service.substrate.auditory_tutor_authority import (
    AuditoryTutorAuthority,
)
from dsf_ai_service.v4.gualaloom_v5_engine import Guala
from tools.probe_auditory_full_field_discrimination import _decode_pcm


def _wav(pcm: bytes) -> bytes:
    payload = io.BytesIO()
    with wave.open(payload, "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(16_000)
        target.writeframes(pcm)
    return payload.getvalue()


def _experience(path: Path, ordinal: int, l5_owner: AuditoryL5Owner):
    source_pcm = _decode_pcm(path)
    _event_wav, event_sample_count, _pcm_bytes, event_field = (
        Guala._auditory_tutor_event(_wav(source_pcm))
    )
    anchor = Fraction(2_000 + ordinal * 100)
    components = auditory_kernel_component_inputs(
        event_field,
        source_anchor=anchor,
    )
    built = build_transaction_owned_six_sense_full_field(
        assembly_id=f"auditory-surrounded-event-{ordinal}",
        source_time_start=anchor,
        source_time_end=anchor + Fraction(event_sample_count, 16_000),
        observed_substreams={PhysicalSense.SOUND: components},
        states={
            sense: (
                SenseBoundaryState.OBSERVED
                if sense is PhysicalSense.SOUND
                else SenseBoundaryState.SENSOR_UNAVAILABLE
            )
            for sense in SENSE_ORDER
        },
    )
    experience = l5_owner.settle(built, event_boundary="utterance")
    if experience is None:
        raise RuntimeError(f"event did not reach auditory L5: {path}")
    return experience, {
        "path": str(path.resolve()),
        "source_sample_count": len(source_pcm) // 2,
        "event_sample_count": event_sample_count,
        "event_frame_count": event_field.frame_count,
        "l5_structural_fingerprint": experience.structural_fingerprint,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("query", type=Path)
    parser.add_argument("tutors", nargs=2, type=Path)
    parser.add_argument("--label", default="hello guala")
    args = parser.parse_args()
    for path in (args.query, *args.tutors):
        if not path.is_file():
            raise SystemExit(f"recording does not exist: {path}")

    exact_owner = start_exact_field_executor()
    exact_owner.assert_healthy()
    l5_owner = AuditoryL5Owner(log_event=lambda *_args, **_kwargs: None)
    try:
        query, query_report = _experience(args.query, 0, l5_owner)
        tutor_values = [
            _experience(path, index + 1, l5_owner)
            for index, path in enumerate(args.tutors)
        ]
    finally:
        stop_exact_field_executor()

    reciprocity = AuditoryReciprocityOwner(
        log_event=lambda *_args, **_kwargs: None,
        tutor_authority=AuditoryTutorAuthority.unrequired(),
    )
    learned = None
    for tutor, _report in tutor_values:
        learned = reciprocity.teach(
            tutor,
            kind=AuditoryReciprocityKind.SPOKEN_FORM,
            tutor_label=args.label,
        )
    recognition, work = reciprocity.recognize_bounded(
        query,
        kind=AuditoryReciprocityKind.SPOKEN_FORM,
        max_work=1_000_000,
    )
    print(json.dumps({
        "schema": "guala.audit.auditory_surrounded_event_recognition.v1",
        "query": query_report,
        "tutors": [report for _value, report in tutor_values],
        "learned_branch_count": len(learned.branches),
        "recognition_state": recognition.state.value,
        "recognized_label": recognition.tutor_label,
        "candidate_labels": list(recognition.candidate_labels),
        "work_cells": work,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
