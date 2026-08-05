"""Falsify Krimelack kind recall inside fixed continuous PCM units.

Two surrounded tutor events form one label-independent physical kind.  Each
query event is then placed at several offsets inside a two-second ambient
transport unit and transduced as that complete unit.  This determines whether
whole-unit recall is a valid live terminal architecture before any engine
cutover is attempted.
"""

from __future__ import annotations

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
from dsf_ai_service.substrate.auditory_krimelack_memory import (
    AuditoryKrimelackMemoryOwner,
)
from dsf_ai_service.substrate.auditory_l5 import AuditoryL5Owner
from dsf_ai_service.substrate.auditory_tutor_authority import (
    AuditoryTutorAuthority,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    REQUIRED_SAMPLE_RATE_HZ,
    transduce_auditory_full_field,
)
from dsf_ai_service.v4.gualaloom_v5_engine import Guala
from tools.probe_auditory_full_field_discrimination import _decode_pcm
from tools.probe_auditory_surrounded_event_recognition import (
    _experience,
    _wav,
)


TRANSPORT_SAMPLES = REQUIRED_SAMPLE_RATE_HZ * 2
OFFSETS = (0, 4_000, 8_000, 12_000)
RECORDINGS = (
    Path("/workspaces/Tao_Financial_Engine/harness/Hello Guala.mp3"),
    Path("/workspaces/Tao_Financial_Engine/harness/hello guala 1.mp3"),
    Path("/workspaces/Tao_Financial_Engine/harness/hello guala 2.mp3"),
)


def _event_pcm(path: Path) -> bytes:
    event_wav, sample_count, _pcm_bytes, _field = (
        Guala._auditory_tutor_event(_wav(_decode_pcm(path)))
    )
    with wave.open(io.BytesIO(event_wav), "rb") as source:
        pcm = source.readframes(sample_count)
    if len(pcm) != sample_count * 2:
        raise RuntimeError("surrounded auditory event PCM changed")
    return pcm


def _continuous_experience(
    pcm: bytes,
    *,
    offset: int,
    ordinal: int,
    owner: AuditoryL5Owner,
):
    event = np.frombuffer(pcm, dtype="<i2")
    if offset + len(event) > TRANSPORT_SAMPLES:
        raise ValueError("query event does not fit the transport unit")
    signal = np.zeros(TRANSPORT_SAMPLES, dtype=np.int16)
    signal[offset:offset + len(event)] = event
    capture = transduce_auditory_full_field(
        signal.astype(np.float64) / 32_768.0,
        sample_rate_hz=REQUIRED_SAMPLE_RATE_HZ,
    )
    anchor = Fraction(10_000 + ordinal * 10)
    built = build_transaction_owned_six_sense_full_field(
        assembly_id=f"krimelack-continuous-{ordinal}-{offset}",
        source_time_start=anchor,
        source_time_end=anchor + Fraction(
            TRANSPORT_SAMPLES,
            REQUIRED_SAMPLE_RATE_HZ,
        ),
        observed_substreams={
            PhysicalSense.SOUND: auditory_kernel_component_inputs(
                capture,
                source_anchor=anchor,
            ),
        },
        states={
            sense: (
                SenseBoundaryState.OBSERVED
                if sense is PhysicalSense.SOUND
                else SenseBoundaryState.SENSOR_UNAVAILABLE
            )
            for sense in SENSE_ORDER
        },
    )
    experience = owner.settle(built, event_boundary="ambient")
    if experience is None:
        raise RuntimeError("continuous auditory query did not reach L5")
    return experience


def main() -> None:
    executor = start_exact_field_executor()
    executor.assert_healthy()
    l5_owner = AuditoryL5Owner(log_event=lambda *_args, **_kwargs: None)
    try:
        tutors = tuple(
            _experience(path, ordinal, l5_owner)[0]
            for ordinal, path in enumerate(RECORDINGS[:2])
        )
        event_pcm = tuple(_event_pcm(path) for path in RECORDINGS)
        memory = AuditoryKrimelackMemoryOwner(
            log_event=lambda *_args, **_kwargs: None,
            tutor_authority=AuditoryTutorAuthority.unrequired(),
        )
        for tutor in tutors:
            memory.teach(tutor, tutor_label="hello guala")
        results = []
        ordinal = 100
        for path, pcm in zip(RECORDINGS, event_pcm, strict=True):
            for offset in OFFSETS:
                query = _continuous_experience(
                    pcm,
                    offset=offset,
                    ordinal=ordinal,
                    owner=l5_owner,
                )
                ordinal += 1
                recognition = memory.recognize(query)
                results.append({
                    "event_samples": len(pcm) // 2,
                    "offset_samples": offset,
                    "query": str(path.resolve()),
                    "state": recognition.state.value,
                    "tutor_label": recognition.tutor_label,
                    "work_cells": recognition.work_cells,
                })
    finally:
        stop_exact_field_executor()
    print(json.dumps({
        "results": results,
        "schema": (
            "guala.audit.auditory_krimelack_continuous_chunk.v1"
        ),
        "transport_samples": TRANSPORT_SAMPLES,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
